"""
╔══════════════════════════════════════════════════════════════════╗
║              BOT MARMITA - NETSUL                                ║
║              Sistema automático de pedidos de almoço             ║
╚══════════════════════════════════════════════════════════════════╝
"""
import asyncio
import datetime
import logging
import unicodedata

import discord
from discord.ext import commands, tasks

from cardapio import limpar_cardapio
from pedido import montar_corpo_pedido, montar_linha_prato as montar_linha_prato_pedido
from settings import (
    BASE_DIR,
    CHAVE_PIX,
    CONFIG_PATH,
    HISTORICO_PATH,
    LOG_PATH,
    NOME_PIX,
    NUMERO_CHEF,
    NUMERO_WPP,
    TOKEN,
    VALOR_MARMITA_PADRAO,
    carregar_config,
    carregar_valor_marmita,
    normalizar_config,
)
from whatsapp import montar_link_cobranca as montar_link_cobranca_whatsapp
from whatsapp import montar_link_whatsapp, validar_numero_whatsapp


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8", mode='a'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def _nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)


VALOR_MARMITA = carregar_valor_marmita(logger=log)


def carregar_constantes_config() -> tuple[dict, dict, set, int, int, int]:
    config = carregar_config(CONFIG_PATH, logger=log)
    config_normalizado = normalizar_config(config, logger=log)
    return (
        config,
        config_normalizado["preferencias_sem"],
        config_normalizado["usuarios_monitoramento"],
        config_normalizado["limite_mensagens"],
        config_normalizado["enquete_duracao_horas"],
        config_normalizado["total_maximo_marmitas"],
    )


CONFIG, PREFERENCIAS_SEM, USUARIOS_SERVIDOR, LIMITE_MENSAGENS, ENQUETE_DURACAO, TOTAL_MAXIMO = carregar_constantes_config()
ENQUETES_PENDENTES = {}
LEMBRETES_ENVIADOS: dict[int, int] = {}
CARDAPIOS_POR_CANAL = {}


def montar_linha_prato(prato: str, qtd: int, votos_por_usuario: dict, tem_macarrao: bool = True) -> str:
    return montar_linha_prato_pedido(prato, qtd, votos_por_usuario, PREFERENCIAS_SEM, tem_macarrao)


def montar_link_cobranca(total_marmitas: int) -> str | None:
    return montar_link_cobranca_whatsapp(
        total_marmitas=total_marmitas,
        numero_chef=NUMERO_CHEF,
        chave_pix=CHAVE_PIX,
        nome_pix=NOME_PIX,
        valor_marmita=VALOR_MARMITA,
        logger=log,
    )


def montar_lista_usuarios(config: dict) -> str:
    config_normalizado = normalizar_config(config)
    usuarios = config_normalizado["usuarios_cadastrados"]

    if not usuarios:
        return "📋 **Usuarios cadastrados:**\nNenhum usuario cadastrado."

    def ordenar(item):
        user_id, dados = item
        return str(dados.get("nome") or "").lower(), int(user_id)

    ativos = sorted(
        [(user_id, dados) for user_id, dados in usuarios.items() if dados.get("monitorar")],
        key=ordenar,
    )
    inativos = sorted(
        [(user_id, dados) for user_id, dados in usuarios.items() if not dados.get("monitorar")],
        key=ordenar,
    )

    def linhas(grupo):
        if not grupo:
            return ["- Nenhum"]
        return [
            f"- <@{user_id}> - {dados.get('nome') or f'Usuario {user_id}'} (`{user_id}`)"
            for user_id, dados in grupo
        ]

    return (
        "📋 **Usuarios cadastrados:**\n\n"
        f"✅ **Ativos ({len(ativos)}):**\n"
        + "\n".join(linhas(ativos))
        + "\n\n"
        f"⏸️ **Nao ativos ({len(inativos)}):**\n"
        + "\n".join(linhas(inativos))
    )


def dividir_mensagem(texto: str, limite: int = 1900) -> list[str]:
    partes = []
    parte_atual = ""
    for linha in texto.splitlines():
        candidata = linha if not parte_atual else parte_atual + "\n" + linha
        if len(candidata) > limite:
            if parte_atual:
                partes.append(parte_atual)
            parte_atual = linha
        else:
            parte_atual = candidata
    if parte_atual:
        partes.append(parte_atual)
    return partes


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        log.info(f"✅ SISTEMA NETSUL ATIVO: {bot.user} | Servidor: {guild.name} | ID: {guild.id}")
    if not reconectar.is_running():
        reconectar.start()
    if not verificar_votacao.is_running():
        verificar_votacao.start()
    log.info(f"📋 {len(ENQUETES_PENDENTES)} enquetes pendentes em monitoramento")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


@tasks.loop(minutes=1)
async def verificar_votacao():
    global LEMBRETES_ENVIADOS
    if not ENQUETES_PENDENTES:
        return

    agora = datetime.datetime.now()
    canais_processados = set()

    for msg_id, dados in list(ENQUETES_PENDENTES.items()):
        canal_id = dados['canal_id']
        if canal_id in canais_processados:
            continue

        canal = bot.get_channel(canal_id)
        if not canal or not isinstance(canal, discord.TextChannel):
            continue

        try:
            tempo_criado = dados['criado_em']
            tempo_decorrido = (agora - tempo_criado).total_seconds()
            votos_usuarios = set()

            for mid, d in list(ENQUETES_PENDENTES.items()):
                if d['canal_id'] == canal_id:
                    try:
                        mensagem = await canal.fetch_message(mid)
                        if mensagem.poll:
                            for answer in mensagem.poll.answers:
                                async for voter in answer.voters():
                                    votos_usuarios.add(voter.id)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                        log.warning(f"Não foi possível ler votos da enquete {mid}: {e}")

            usuarios_nao_votaram = dados['usuarios'] - votos_usuarios
            nivel_atual = LEMBRETES_ENVIADOS.get(canal_id, 0)

            if usuarios_nao_votaram:
                if tempo_decorrido >= 1800 and nivel_atual < 1:
                    mentions = " ".join(f"<@{uid}>" for uid in usuarios_nao_votaram)
                    verbo = "Vote" if len(usuarios_nao_votaram) == 1 else "Votem"
                    await canal.send(
                        f"📢 **Lembrete!** Faltam 30 min para encerrar a votação!\n"
                        f"{mentions}\n"
                        f"⏰ {verbo} agora no cardápio de hoje!"
                    )
                    log.info(f"1o lembrete (30min) enviado para {len(usuarios_nao_votaram)} usuários no canal {canal.name}")
                    LEMBRETES_ENVIADOS[canal_id] = 1

                if tempo_decorrido >= dados['prazo'] and nivel_atual < 2:
                    mentions = " ".join(f"<@{uid}>" for uid in usuarios_nao_votaram)
                    verbo = "Vote" if len(usuarios_nao_votaram) == 1 else "Votem"
                    await canal.send(
                        f"🚨 **ÚLTIMO LEMBRETE!** Ainda faltam votos!\n"
                        f"{mentions}\n"
                        f"⏰ {verbo} agora no cardápio de hoje!"
                    )
                    log.info(f"2o lembrete (final) enviado para {len(usuarios_nao_votaram)} usuários no canal {canal.name}")
                    LEMBRETES_ENVIADOS[canal_id] = 2

            if usuarios_nao_votaram == set() and votos_usuarios:
                await canal.send(
                    f"✅ **Todos votaram!**\n"
                    f"🎉 Já podem usar `!pedido` para fechar o almoço!"
                )
                log.info(f"Todos votaram no canal {canal.name}")
                canais_processados.add(canal_id)
                for mid in list(ENQUETES_PENDENTES.keys()):
                    if ENQUETES_PENDENTES[mid]['canal_id'] == canal_id:
                        del ENQUETES_PENDENTES[mid]
        except Exception as e:
            log.error(f"Erro ao verificar votacao: {e}")


@tasks.loop(minutes=5)
async def reconectar():
    if not bot.is_closed():
        return

    log.info("🔄 Tentando reconectar ao Discord...")
    try:
        for handler in log.handlers:
            handler.flush()
        await bot.connect(reconnect=True)
    except Exception as e:
        log.error(f"Erro na reconexão: {e}")


@bot.event
async def on_disconnect():
    log.warning("⚠️ Bot desconectado do Discord")


@bot.event
async def on_error(event, *args, **kwargs):
    log.error(f"Erro no evento {event}: {args}, {kwargs}")


@bot.command(aliases=['almoço', 'cardapio', 'cardápio'])
async def almoco(ctx, *, mensagem_copiada: str):
    canal_alvo = ctx.channel
    if not isinstance(canal_alvo, discord.TextChannel):
        await ctx.send("❌ Erro: Canal inválido.")
        return

    data_hoje = datetime.datetime.now().date()
    async for msg in canal_alvo.history(limit=5):
        if msg.poll and msg.created_at.date() == data_hoje and msg.author == bot.user:
            await ctx.send("⚠️ Já existe uma enquete de hoje! Use `!fechar` para finalizar.")
            return

    pratos = limpar_cardapio(mensagem_copiada)
    if not pratos:
        await ctx.send("🤔 Não identifiquei pratos principais no cardápio.")
        return

    grupos = [pratos[i:i + 10] for i in range(0, len(pratos), 10)]
    enquetes_criadas = []

    for idx, grupo in enumerate(grupos):
        titulo = f"🍴 Qual o almoço de hoje? (P{idx+1})" if len(grupos) > 1 else "🍴 Qual o almoço de hoje?"
        enquete = discord.Poll(question=titulo, duration=datetime.timedelta(hours=ENQUETE_DURACAO))
        for prato in grupo:
            enquete.add_answer(text=(prato['nome'][:52] + "..") if len(prato['nome']) > 55 else prato['nome'])
        msg = await canal_alvo.send(poll=enquete)
        enquetes_criadas.append(msg)

    macarrao_por_disco = {_nfc(p['nome'].upper()): p['tem_macarrao'] for p in pratos}
    CARDAPIOS_POR_CANAL[canal_alvo.id] = macarrao_por_disco

    for msg in enquetes_criadas:
        ENQUETES_PENDENTES[msg.id] = {
            'canal_id': canal_alvo.id,
            'criado_em': datetime.datetime.now(),
            'prazo': 3600,
            'usuarios': USUARIOS_SERVIDOR.copy(),
            'macarrao_por_disco': macarrao_por_disco,
        }

    LEMBRETES_ENVIADOS.clear()
    log.info(f"Enquete(s) criada(s) por {ctx.author.name} no servidor {ctx.guild.name} com {len(pratos)} prato(s).")
    await ctx.message.add_reaction("✅")


@bot.command(aliases=['fechar', 'finalizar'])
async def pedido(ctx):
    canal_alvo = ctx.channel
    if not isinstance(canal_alvo, discord.TextChannel):
        await ctx.send("❌ Erro: Canal inválido.")
        return

    hoje = datetime.datetime.now().strftime("%d.%m.%Y")
    data_hoje = datetime.datetime.now().date()
    pedidos_dict = {}
    votos_por_usuario = {}
    total_marmitas = 0

    async for message in canal_alvo.history(limit=LIMITE_MENSAGENS):
        if message.poll and message.created_at.date() == data_hoje and message.author == bot.user:
            for answer in message.poll.answers:
                if answer.vote_count > 0:
                    prato_nome = answer.text.upper()
                    pedidos_dict[prato_nome] = pedidos_dict.get(prato_nome, 0) + answer.vote_count
                    total_marmitas += answer.vote_count
                    async for voter in answer.voters():
                        if voter.id in PREFERENCIAS_SEM:
                            votos_por_usuario.setdefault(voter.id, []).append(prato_nome)

    if total_marmitas == 0:
        await ctx.send("⚠️ Nenhuma marmita votada hoje!")
        return

    if total_marmitas > TOTAL_MAXIMO:
        await ctx.send(f"⚠️ Total de marmitas ({total_marmitas}) excede o máximo configurado ({TOTAL_MAXIMO})!")
        return

    macarrao_por_disco = {}
    msg_ids_removidas = []
    for mid, dados in ENQUETES_PENDENTES.items():
        if dados['canal_id'] == canal_alvo.id:
            macarrao_por_disco.update(dados.get('macarrao_por_disco', {}))
            msg_ids_removidas.append(mid)
    macarrao_por_disco.update(CARDAPIOS_POR_CANAL.get(canal_alvo.id, {}))

    for mid in msg_ids_removidas:
        del ENQUETES_PENDENTES[mid]
    CARDAPIOS_POR_CANAL.pop(canal_alvo.id, None)

    # Perguntar sobre Reginaldo
    try:
        await ctx.send("📋 **Reginaldo vai pedir hoje?** (sim/nao)\n⏰ 30s")

        def check_reginaldo(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        resp = await bot.wait_for('message', timeout=30, check=check_reginaldo)

        if resp.content.lower() in ('sim', 's'):
            await ctx.send("Qual prato? (ex: Filé de frango acebolado)")
            resp_prato = await bot.wait_for('message', timeout=30, check=check_reginaldo)

            texto = _nfc(resp_prato.content.upper().strip())
            prato_encontrado = None

            for key in macarrao_por_disco:
                if texto in key or key in texto:
                    prato_encontrado = key
                    break

            if prato_encontrado:
                pedidos_dict[prato_encontrado] = pedidos_dict.get(prato_encontrado, 0) + 1
                total_marmitas += 1
                await ctx.send(f"✅ Marmita do Reginaldo adicionada! Total: **{total_marmitas:02d}**")
                log.info(f"Marmita extra do Reginaldo adicionada: {prato_encontrado}")
            else:
                await ctx.send(f"❌ Prato `{resp_prato.content}` não encontrado no cardápio de hoje.")
        else:
            await ctx.send("✅ OK, seguindo sem Reginaldo.")

    except TimeoutError:
        await ctx.send("⏰ Tempo esgotado! Seguindo sem Reginaldo.")

    lista_formatada = []
    for nome, qtd in pedidos_dict.items():
        nome_upper = nome.upper()
        tem_macarrao = macarrao_por_disco.get(_nfc(nome_upper), True)
        lista_formatada.append(montar_linha_prato(nome, qtd, votos_por_usuario, tem_macarrao))

    corpo_pedido = montar_corpo_pedido(hoje, lista_formatada, total_marmitas)

    try:
        with open(HISTORICO_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] REGISTRO:\n{corpo_pedido}\n")
            f.write("="*50 + "\n")
    except Exception as e:
        log.error(f"Erro ao salvar arquivo: {e}")
        await ctx.send("⚠️ Erro ao salvar histórico, mas continuando...")

    link_whatsapp = montar_link_whatsapp(NUMERO_WPP, corpo_pedido)
    if not link_whatsapp:
        await ctx.send("⚠️ Número WhatsApp não configurado ou inválido no .env")
        return

    link_cobranca = montar_link_cobranca(total_marmitas)
    log.info(f"Pedido de {total_marmitas} marmita(s) registrado por {ctx.author.name} no servidor {ctx.guild.name}.")

    if link_cobranca:
        await ctx.send(f"📊 **Pedido Consolidado!** Total: **{total_marmitas:02d}** marmitas.\n"
                       f"👉 [ENVIAR PEDIDO]({link_whatsapp})\n"
                       f"💰 [ENVIAR COBRANÇA]({link_cobranca})")
    else:
        await ctx.send(f"📊 **Pedido Consolidado!** Total: **{total_marmitas:02d}** marmitas.\n"
                       f"👉 [CLIQUE PARA ENVIAR NO WHATSAPP]({link_whatsapp})")


@bot.command(aliases=['ajuda', 'comandos', 'cmds'])
async def help_bot(ctx):
    embed = discord.Embed(
        title="🍴 Bot Marmita - Comandos",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="!almoco / !cardapio",
        value="Cria enquete com os pratos do cardápio",
        inline=False,
    )
    embed.add_field(
        name="!pedido / !fechar",
        value="Fecha a votação e gera pedido para WhatsApp",
        inline=False,
    )
    embed.add_field(
        name="!pref",
        value="Lista restrições alimentares ativas",
        inline=False,
    )
    embed.add_field(
        name="!usuarios",
        value="Lista usuarios cadastrados ativos e nao ativos",
        inline=False,
    )
    embed.add_field(
        name="!status",
        value="Mostra status do bot",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(aliases=['pref', 'preferencias'])
async def ver_preferencias(ctx):
    if not PREFERENCIAS_SEM:
        await ctx.send("📋 Nenhuma restrição configurada.")
        return

    lista = [f"<@{uid}> → SEM {rest}" for uid, rest in PREFERENCIAS_SEM.items()]
    await ctx.send("📋 **Restrições ativas:**\n" + "\n".join(lista))


@bot.command(name='usuarios')
async def listar_usuarios(ctx):
    config_atual = carregar_config(CONFIG_PATH, logger=log)
    mensagem = montar_lista_usuarios(config_atual)
    for parte in dividir_mensagem(mensagem):
        await ctx.send(parte)


@bot.command(aliases=['status'])
async def status_bot(ctx):
    embed = discord.Embed(title="🤖 Status do Bot", color=discord.Color.green())
    embed.add_field(name="Usuário", value=str(bot.user), inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Restrições", value=len(PREFERENCIAS_SEM), inline=True)
    embed.add_field(name="Limite Mensagens", value=LIMITE_MENSAGENS, inline=True)
    embed.add_field(name="WhatsApp", value="✅ Configurado" if validar_numero_whatsapp(NUMERO_WPP) else "❌ Inválido", inline=True)
    embed.add_field(name="Enquetes Pendentes", value=len(ENQUETES_PENDENTES), inline=True)
    await ctx.send(embed=embed)


@bot.command(aliases=['reload', 'recarregar'])
async def recarregar_config(ctx):
    global CONFIG, PREFERENCIAS_SEM, USUARIOS_SERVIDOR, LIMITE_MENSAGENS, ENQUETE_DURACAO, TOTAL_MAXIMO
    CONFIG, PREFERENCIAS_SEM, USUARIOS_SERVIDOR, LIMITE_MENSAGENS, ENQUETE_DURACAO, TOTAL_MAXIMO = carregar_constantes_config()
    await ctx.send("✅ Configurações recarregadas!")


if __name__ == "__main__":
    if not TOKEN:
        log.error("❌ DISCORD_TOKEN não encontrado no arquivo .env")
        exit(1)

    numero_validado = validar_numero_whatsapp(NUMERO_WPP)
    if not numero_validado:
        log.warning("⚠️ NUMERO_MARMITA não configurado ou inválido no .env")

    log.info(f"📋 {len(USUARIOS_SERVIDOR)} usuários monitorados para lembretes")
    bot.run(TOKEN, reconnect=True)
