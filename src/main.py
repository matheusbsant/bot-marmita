"""
╔══════════════════════════════════════════════════════════════════╗
║              BOT MARMITA - NETSUL                                ║
║              Sistema automático de pedidos de almoço             ║
╚══════════════════════════════════════════════════════════════════╝

ETAPAS DO CÓDIGO:
1. IMPORTAÇÕES - Bibliotecas necessárias
2. CONFIGURAÇÕES - Variáveis de ambiente e logging
3. CONSTANTES - Listas de palavras a ignorar
4. FUNÇÕES - Lógica do bot
5. BOT - Configuração e eventos
6. COMANDOS - Comandos do Discord
7. INICIALIZAÇÃO - Execução do bot
"""

# ═══════════════════════════════════════════════════════════════════
# 1. IMPORTAÇÕES
# ═══════════════════════════════════════════════════════════════════
import discord
from discord.ext import commands, tasks
import json, os, re, datetime, urllib.parse, logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


# ═══════════════════════════════════════════════════════════════════
# 2. CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════════
load_dotenv()

TOKEN      = os.getenv('DISCORD_TOKEN')
NUMERO_WPP = os.getenv('NUMERO_MARMITA')

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.json"
HISTORICO_PATH = BASE_DIR / "historico_pedidos.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 3. CONSTANTES (do config.json)
# ═══════════════════════════════════════════════════════════════════
def carregar_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.warning(f"config.json não encontrado ou inválido: {e}")
        return {}

CONFIG = carregar_config()
PREFERENCIAS_SEM = {int(k): v for k, v in CONFIG.get("preferencias_sem", {}).items()}
USUARIOS_SERVIDOR = {int(id) for id in CONFIG.get("usuarios_monitoramento", [])}
LIMITE_MENSAGENS = CONFIG.get("limite_mensagens", 100)
ENQUETE_DURACAO = CONFIG.get("enquete_duracao_horas", 4)
TOTAL_MAXIMO = CONFIG.get("total_maximo_marmitas", 200)

ENQUETES_PENDENTES = {}


# ═══════════════════════════════════════════════════════════════════
# 4. FUNÇÕES
# ═══════════════════════════════════════════════════════════════════
def validar_numero_whatsapp(numero: Optional[str]) -> Optional[str]:
    if not numero:
        return None
    numero_limpo = re.sub(r'\D', '', numero)
    if len(numero_limpo) >= 10:
        return numero_limpo
    return None


def limpar_cardapio(texto: str) -> list[str]:
    pratos_unicos = []
    
    texto_negrito = re.findall(r'\*([^*]+)\*', texto)
    
    for negrito in texto_negrito:
        negrito = negrito.strip()
        if len(negrito) > 5 and negrito.lower() not in [p.lower() for p in pratos_unicos]:
            pratos_unicos.append(negrito)
    
    return pratos_unicos


def montar_linha_prato(prato: str, qtd: int, votos_por_usuario: dict) -> str:
    usuarios_com_restricao = []
    
    for user_id, restricao in PREFERENCIAS_SEM.items():
        if prato in votos_por_usuario.get(user_id, []):
            usuarios_com_restricao.append(restricao)

    qtd_sem = len(usuarios_com_restricao)

    if qtd_sem == 0:
        return f"{qtd:02d} {prato}"

    obs_texto = " / ".join(set(usuarios_com_restricao))

    if qtd_sem == qtd:
        return f"{qtd:02d} {prato} (SEM {obs_texto})"
    else:
        return f"{qtd:02d} {prato} ({qtd_sem:02d} SEM {obs_texto})"


# ═══════════════════════════════════════════════════════════════════
# 5. BOT
# ═══════════════════════════════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)


# ═══════════════════════════════════════════════════════════════════
# 6. EVENTOS
# ═══════════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    for guild in bot.guilds:
        log.info(f"✅ SISTEMA NETSUL ATIVO: {bot.user} | Servidor: {guild.name} | ID: {guild.id}")
    if not reconectar.is_running():
        reconectar.start()
    if not verificar_votacao.is_running():
        verificar_votacao.start()
    log.info(f"📋 {len(ENQUETES_PENDENTES)} enquetes pendentes em monitoramento")


@tasks.loop(minutes=1)
async def verificar_votacao():
    if not ENQUETES_PENDENTES:
        return
    
    agora = datetime.datetime.now()
    
    canais_processados = set()
    lembretes_enviados = set()
    
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
                    except:
                        pass
            
            usuarios_nao_votaram = dados['usuarios'] - votos_usuarios
            
            if tempo_decorrido >= dados['prazo'] and usuarios_nao_votaram and canal_id not in lembretes_enviados:
                mentions = " ".join(f"<@{uid}>" for uid in usuarios_nao_votaram)
                verbo = "Vote" if len(usuarios_nao_votaram) == 1 else "Votem"
                await canal.send(
                    f"📢 **Lembrete!** Ainda faltam votos!\n"
                    f"{mentions}\n"
                    f"⏰ {verbo} agora no cardápio de hoje!"
                )
                log.info(f"Lembrete enviado para {len(usuarios_nao_votaram)} usuários no canal {canal.name}")
                lembretes_enviados.add(canal_id)
            
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


# ═══════════════════════════════════════════════════════════════════
# 7. COMANDOS
# ═══════════════════════════════════════════════════════════════════
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
            enquete.add_answer(text=(prato[:52] + "..") if len(prato) > 55 else prato)
        msg = await canal_alvo.send(poll=enquete)
        enquetes_criadas.append(msg)
    
    for msg in enquetes_criadas:
        ENQUETES_PENDENTES[msg.id] = {
            'canal_id': canal_alvo.id,
            'criado_em': datetime.datetime.now(),
            'prazo': 3600,
            'usuarios': USUARIOS_SERVIDOR.copy()
        }
    
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

    msg_ids_removidas = [mid for mid, dados in ENQUETES_PENDENTES.items() if dados['canal_id'] == canal_alvo.id]
    for mid in msg_ids_removidas:
        del ENQUETES_PENDENTES[mid]
    
    lista_formatada = [montar_linha_prato(nome, qtd, votos_por_usuario) for nome, qtd in pedidos_dict.items()]
    
    corpo_pedido = (
        "---------------------------------------------------\n"
        f"Almoço {hoje} -> Pedidos da NETSUL\n"
        "---------------------------------------------------\n\n"
        "*--------MARMITAS TAMANHO M---------*\n\n"
        + "\n".join(lista_formatada) +
        "\n\n---------------------------------------------------\n"
        f"Entregar na *NETSUL* -> Total de *{total_marmitas:02d} Marmitas*\n"
        "RUA DR. CICERO ROSA 589, BAIRRO SAUDE\n"
        "---------------------------------------------------"
    )

    try:
        with open(HISTORICO_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] REGISTRO:\n{corpo_pedido}\n")
            f.write("="*50 + "\n")
    except Exception as e:
        log.error(f"Erro ao salvar arquivo: {e}")
        await ctx.send("⚠️ Erro ao salvar histórico, mas continuando...")

    numero_validado = validar_numero_whatsapp(NUMERO_WPP)
    if not numero_validado:
        await ctx.send("⚠️ Número WhatsApp não configurado ou inválido no .env")
        return

    texto_url = urllib.parse.quote(corpo_pedido)
    link_whatsapp = f"https://wa.me/{numero_validado}?text={texto_url}"

    log.info(f"Pedido de {total_marmitas} marmita(s) registrado por {ctx.author.name} no servidor {ctx.guild.name}.")
    await ctx.send(f"📊 **Pedido Consolidado!** Total: **{total_marmitas:02d}** marmitas.\n"
                   f"👉 [CLIQUE PARA ENVIAR NO WHATSAPP]({link_whatsapp})")


@bot.command(aliases=['ajuda', 'comandos', 'cmds'])
async def help_bot(ctx):
    embed = discord.Embed(
        title="🍴 Bot Marmita - Comandos",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="!almoco / !cardapio",
        value="Cria enquete com os pratos do cardápio",
        inline=False
    )
    embed.add_field(
        name="!pedido / !fechar",
        value="Fecha a votação e gera pedido para WhatsApp",
        inline=False
    )
    embed.add_field(
        name="!pref",
        value="Lista restrições alimentares ativas",
        inline=False
    )
    embed.add_field(
        name="!status",
        value="Mostra status do bot",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(aliases=['pref', 'preferencias'])
async def ver_preferencias(ctx):
    if not PREFERENCIAS_SEM:
        await ctx.send("📋 Nenhuma restrição configurada.")
        return
    
    lista = [f"<@{uid}> → SEM {rest}" for uid, rest in PREFERENCIAS_SEM.items()]
    await ctx.send("📋 **Restrições ativas:**\n" + "\n".join(lista))


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
    
    nova_config = carregar_config()
    nova_preferencias = {int(k): v for k, v in nova_config.get("preferencias_sem", {}).items()}
    
    CONFIG = nova_config
    PREFERENCIAS_SEM = nova_preferencias
    USUARIOS_SERVIDOR = {int(id) for id in nova_config.get("usuarios_monitoramento", [])}
    LIMITE_MENSAGENS = nova_config.get("limite_mensagens", 100)
    ENQUETE_DURACAO = nova_config.get("enquete_duracao_horas", 4)
    TOTAL_MAXIMO = nova_config.get("total_maximo_marmitas", 200)
    
    await ctx.send("✅ Configurações recarregadas!")


# ═══════════════════════════════════════════════════════════════════
# 8. INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not TOKEN:
        log.error("❌ DISCORD_TOKEN não encontrado no arquivo .env")
        exit(1)
    
    numero_validado = validar_numero_whatsapp(NUMERO_WPP)
    if not numero_validado:
        log.warning("⚠️ NUMERO_MARMITA não configurado ou inválido no .env")
    
    log.info(f"📋 {len(USUARIOS_SERVIDOR)} usuários monitorados para lembretes")
    
    bot.run(TOKEN, reconnect=True)
