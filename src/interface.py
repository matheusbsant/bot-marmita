import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext

from dotenv import dotenv_values

from settings import (
    CONFIG_PATH,
    ENV_PATH,
    LOG_DIR,
    carregar_config,
    carregar_valor_marmita,
    normalizar_config,
)
from whatsapp import validar_numero_whatsapp


FROZEN = getattr(sys, 'frozen', False)

COR_FUNDO = "#f4f0e8"
COR_CARD = "#fffaf1"
COR_TEXTO = "#2a221b"
COR_MUTED = "#6e6258"
COR_OK = "#247a3d"
COR_AVISO = "#a56800"
COR_ERRO = "#a32929"
COR_BOTAO = "#235347"
COR_BOTAO_PARAR = "#9f3a2f"


def usuarios_para_interface(config: dict) -> list[dict]:
    config_normalizado = normalizar_config(config or {})
    usuarios = []
    for user_id, dados in config_normalizado["usuarios_cadastrados"].items():
        usuarios.append({
            "id": str(user_id),
            "nome": str(dados.get("nome") or f"Usuario {user_id}"),
            "monitorar": bool(dados.get("monitorar")),
        })
    return sorted(usuarios, key=lambda item: (item["nome"].lower(), int(item["id"])))


def aplicar_usuarios_no_config(config: dict, usuarios: list[dict]) -> dict:
    config_atualizado = dict(config or {})
    usuarios_cadastrados = {}
    usuarios_monitoramento = []
    ids_vistos = set()

    for usuario in usuarios:
        user_id = str(usuario.get("id") or "").strip()
        if not user_id.isdigit():
            raise ValueError("ID Discord deve conter apenas numeros.")
        if user_id in ids_vistos:
            raise ValueError(f"ID Discord duplicado: {user_id}")

        ids_vistos.add(user_id)
        nome = str(usuario.get("nome") or "").strip() or f"Usuario {user_id}"
        monitorar = bool(usuario.get("monitorar"))

        usuarios_cadastrados[user_id] = {
            "nome": nome,
            "monitorar": monitorar,
        }
        if monitorar:
            usuarios_monitoramento.append(int(user_id))

    config_atualizado["usuarios_cadastrados"] = usuarios_cadastrados
    config_atualizado["usuarios_monitoramento"] = usuarios_monitoramento
    return config_atualizado


def salvar_usuarios_config(config_path: Path, usuarios: list[dict]) -> dict:
    config = carregar_config(config_path)
    config_atualizado = aplicar_usuarios_no_config(config, usuarios)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_atualizado, f, ensure_ascii=False, indent=4)
        f.write("\n")
    return config_atualizado


class InterfaceBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Marmita - Netsul")
        self.root.geometry("940x760")
        self.root.minsize(840, 680)
        self.root.configure(bg=COR_FUNDO)
        self.root.resizable(True, True)

        self.processo = None
        self.rodando = False
        self.fila_logs = queue.Queue()
        self.cards = {}
        self.ultimo_diagnostico = {}
        self.usuarios_cadastrados = []
        self.usuarios_vars = {}
        self.usuarios_linhas = {}

        self.criar_widgets()
        self.carregar_usuarios_monitorados()
        self.revalidar_configuracoes(silencioso=True)
        self.root.after(100, self.processar_fila)

    def criar_widgets(self):
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_janela)

        header = tk.Frame(self.root, bg=COR_FUNDO)
        header.pack(fill=tk.X, padx=18, pady=(16, 8))

        tk.Label(
            header,
            text="Bot Marmita",
            font=("Segoe UI", 22, "bold"),
            fg=COR_TEXTO,
            bg=COR_FUNDO,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Painel operacional da Netsul",
            font=("Segoe UI", 10),
            fg=COR_MUTED,
            bg=COR_FUNDO,
        ).pack(anchor="w")

        self.label_resumo = tk.Label(
            header,
            text="Validando configurações...",
            font=("Segoe UI", 11, "bold"),
            fg=COR_MUTED,
            bg=COR_FUNDO,
        )
        self.label_resumo.pack(anchor="w", pady=(8, 0))

        frame_cards = tk.Frame(self.root, bg=COR_FUNDO)
        frame_cards.pack(fill=tk.X, padx=18, pady=8)
        for coluna in range(5):
            frame_cards.columnconfigure(coluna, weight=1)

        for idx, nome in enumerate(["Bot", "WhatsApp", "PIX", "Config", "Logs"]):
            self.cards[nome] = self.criar_card(frame_cards, nome, idx)

        frame_controle = tk.Frame(self.root, bg=COR_FUNDO)
        frame_controle.pack(fill=tk.X, padx=18, pady=(8, 4))

        self.btn_iniciar = tk.Button(
            frame_controle,
            text="▶ Iniciar Bot",
            command=self.iniciar_bot,
            width=16,
            bg=COR_BOTAO,
            fg="white",
            activebackground="#1b4037",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=(0, 8), ipady=4)

        self.btn_parar = tk.Button(
            frame_controle,
            text="■ Parar Bot",
            command=self.parar_bot,
            width=16,
            state=tk.DISABLED,
            bg=COR_BOTAO_PARAR,
            fg="white",
            activebackground="#7e2d25",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
        )
        self.btn_parar.pack(side=tk.LEFT, padx=8, ipady=4)

        self.btn_revalidar = tk.Button(
            frame_controle,
            text="Revalidar configurações",
            command=self.revalidar_configuracoes,
            bg="#d8c7a8",
            fg=COR_TEXTO,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        self.btn_revalidar.pack(side=tk.LEFT, padx=8, ipady=4)

        self.btn_limpar = tk.Button(
            frame_controle,
            text="Limpar logs",
            command=self.limpar_logs,
            bg="#e6ddcf",
            fg=COR_TEXTO,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        self.btn_limpar.pack(side=tk.RIGHT, padx=(8, 0), ipady=4)

        frame_atalhos = tk.Frame(self.root, bg=COR_FUNDO)
        frame_atalhos.pack(fill=tk.X, padx=18, pady=(2, 10))

        for texto, comando in [
            ("Abrir .env", lambda: self.abrir_caminho(self.env_path)),
            ("Abrir config.json", lambda: self.abrir_caminho(CONFIG_PATH)),
            ("Abrir pasta de logs", lambda: self.abrir_caminho(LOG_DIR)),
            ("Gerar pacote para outro PC", self.gerar_pacote_distribuicao),
        ]:
            tk.Button(
                frame_atalhos,
                text=texto,
                command=comando,
                bg="#efe4d2",
                fg=COR_TEXTO,
                relief=tk.FLAT,
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=(0, 8), ipady=3)

        self.criar_painel_usuarios()

        tk.Label(
            self.root,
            text="Logs do bot",
            font=("Segoe UI", 11, "bold"),
            fg=COR_TEXTO,
            bg=COR_FUNDO,
        ).pack(anchor="w", padx=18)

        self.area_logs = scrolledtext.ScrolledText(
            self.root,
            width=95,
            height=20,
            font=("Consolas", 9),
            bg="#1f2522",
            fg="#f4f0e8",
            insertbackground="#f4f0e8",
            relief=tk.FLAT,
        )
        self.area_logs.pack(padx=18, pady=(6, 16), fill=tk.BOTH, expand=True)
        self.configurar_tags_log()
        self.adicionar_log("Interface carregada. Revise os cartões e clique em Iniciar Bot.", "info")

    def criar_painel_usuarios(self):
        painel = tk.Frame(self.root, bg=COR_CARD, highlightthickness=1, highlightbackground="#ded1bd")
        painel.pack(fill=tk.X, padx=18, pady=(0, 10))

        cabecalho = tk.Frame(painel, bg=COR_CARD)
        cabecalho.pack(fill=tk.X, padx=10, pady=(8, 4))

        tk.Label(
            cabecalho,
            text="Usuarios monitorados",
            font=("Segoe UI", 11, "bold"),
            fg=COR_TEXTO,
            bg=COR_CARD,
        ).pack(side=tk.LEFT)

        self.btn_salvar_usuarios = tk.Button(
            cabecalho,
            text="Salvar usuarios",
            command=self.salvar_usuarios_monitorados,
            bg=COR_BOTAO,
            fg="white",
            activebackground="#1b4037",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
        )
        self.btn_salvar_usuarios.pack(side=tk.RIGHT, ipady=2)

        form = tk.Frame(painel, bg=COR_CARD)
        form.pack(fill=tk.X, padx=10, pady=(0, 8))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        tk.Label(form, text="Nome", font=("Segoe UI", 9), fg=COR_MUTED, bg=COR_CARD).grid(row=0, column=0, sticky="w")
        self.entry_usuario_nome = tk.Entry(form, font=("Segoe UI", 9), relief=tk.FLAT)
        self.entry_usuario_nome.grid(row=0, column=1, sticky="ew", padx=(6, 12), ipady=3)

        tk.Label(form, text="ID Discord", font=("Segoe UI", 9), fg=COR_MUTED, bg=COR_CARD).grid(row=0, column=2, sticky="w")
        self.entry_usuario_id = tk.Entry(form, font=("Segoe UI", 9), relief=tk.FLAT)
        self.entry_usuario_id.grid(row=0, column=3, sticky="ew", padx=(6, 12), ipady=3)

        tk.Button(
            form,
            text="Adicionar",
            command=self.adicionar_usuario_monitorado,
            bg="#d8c7a8",
            fg=COR_TEXTO,
            relief=tk.FLAT,
            font=("Segoe UI", 9),
        ).grid(row=0, column=4, sticky="ew", ipady=2)

        tabela = tk.Frame(painel, bg=COR_CARD)
        tabela.pack(fill=tk.X, padx=10, pady=(0, 8))
        tabela.columnconfigure(0, minsize=68)
        tabela.columnconfigure(1, weight=1)
        tabela.columnconfigure(2, minsize=190)
        tabela.columnconfigure(3, minsize=64)

        for coluna, texto in enumerate(["Monitorar", "Nome", "ID Discord", "Acao"]):
            tk.Label(
                tabela,
                text=texto,
                font=("Segoe UI", 8, "bold"),
                fg=COR_MUTED,
                bg=COR_CARD,
                anchor="w",
            ).grid(row=0, column=coluna, sticky="w", padx=4, pady=(0, 3))

        lista_container = tk.Frame(tabela, bg=COR_CARD)
        lista_container.grid(row=1, column=0, columnspan=4, sticky="ew")

        self.canvas_usuarios = tk.Canvas(lista_container, height=132, bg=COR_CARD, highlightthickness=0)
        scrollbar_usuarios = tk.Scrollbar(lista_container, orient=tk.VERTICAL, command=self.canvas_usuarios.yview)
        self.canvas_usuarios.configure(yscrollcommand=scrollbar_usuarios.set)

        self.canvas_usuarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_usuarios.pack(side=tk.RIGHT, fill=tk.Y)

        self.frame_linhas_usuarios = tk.Frame(self.canvas_usuarios, bg=COR_CARD)
        self.janela_usuarios_canvas = self.canvas_usuarios.create_window(
            (0, 0),
            window=self.frame_linhas_usuarios,
            anchor="nw",
        )
        self.frame_linhas_usuarios.bind(
            "<Configure>",
            lambda _event: self.canvas_usuarios.configure(scrollregion=self.canvas_usuarios.bbox("all")),
        )
        self.canvas_usuarios.bind(
            "<Configure>",
            lambda event: self.canvas_usuarios.itemconfigure(self.janela_usuarios_canvas, width=event.width),
        )

    def carregar_usuarios_monitorados(self):
        self.usuarios_cadastrados = usuarios_para_interface(carregar_config(CONFIG_PATH))
        self.renderizar_usuarios_monitorados()

    def renderizar_usuarios_monitorados(self):
        if not hasattr(self, "frame_linhas_usuarios"):
            return

        for widget in self.frame_linhas_usuarios.winfo_children():
            widget.destroy()

        self.usuarios_vars = {}
        if not self.usuarios_cadastrados:
            tk.Label(
                self.frame_linhas_usuarios,
                text="Nenhum usuario cadastrado.",
                font=("Segoe UI", 9),
                fg=COR_MUTED,
                bg=COR_CARD,
            ).pack(anchor="w", padx=4, pady=4)
            return

        for idx, usuario in enumerate(self.usuarios_cadastrados):
            user_id = usuario["id"]
            linha_bg = "#fffaf1" if idx % 2 == 0 else "#f6ead6"
            linha = tk.Frame(self.frame_linhas_usuarios, bg=linha_bg)
            linha.pack(fill=tk.X, pady=1)
            linha.columnconfigure(0, minsize=68)
            linha.columnconfigure(1, weight=1)
            linha.columnconfigure(2, minsize=190)
            linha.columnconfigure(3, minsize=64)

            ativo = tk.BooleanVar(value=bool(usuario.get("monitorar")))
            self.usuarios_vars[user_id] = ativo

            tk.Checkbutton(
                linha,
                variable=ativo,
                text="Ativo",
                bg=linha_bg,
                fg=COR_TEXTO,
                activebackground=linha_bg,
                font=("Segoe UI", 9),
            ).grid(row=0, column=0, sticky="w", padx=4)
            tk.Label(linha, text=usuario["nome"], bg=linha_bg, fg=COR_TEXTO, font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", padx=4)
            tk.Label(linha, text=user_id, bg=linha_bg, fg=COR_MUTED, font=("Consolas", 9)).grid(row=0, column=2, sticky="w", padx=4)
            tk.Button(
                linha,
                text="Excluir",
                command=lambda uid=user_id: self.excluir_usuario_monitorado(uid),
                bg="#e6ddcf",
                fg=COR_TEXTO,
                relief=tk.FLAT,
                font=("Segoe UI", 8),
            ).grid(row=0, column=3, sticky="e", padx=4, pady=2)

        self.canvas_usuarios.update_idletasks()
        self.canvas_usuarios.configure(scrollregion=self.canvas_usuarios.bbox("all"))

    def adicionar_usuario_monitorado(self):
        user_id = self.entry_usuario_id.get().strip()
        nome = self.entry_usuario_nome.get().strip()

        if not user_id.isdigit():
            messagebox.showerror("ID invalido", "O ID Discord deve conter apenas numeros.")
            return
        if any(usuario["id"] == user_id for usuario in self.usuarios_cadastrados):
            messagebox.showwarning("Usuario ja cadastrado", f"O ID {user_id} ja esta na lista.")
            return

        self.usuarios_cadastrados.append({
            "id": user_id,
            "nome": nome or f"Usuario {user_id}",
            "monitorar": True,
        })
        self.usuarios_cadastrados = sorted(
            self.usuarios_cadastrados,
            key=lambda item: (item["nome"].lower(), int(item["id"])),
        )
        self.entry_usuario_nome.delete(0, tk.END)
        self.entry_usuario_id.delete(0, tk.END)
        self.renderizar_usuarios_monitorados()
        self.adicionar_log(f"Usuario {user_id} adicionado. Clique em Salvar usuarios para aplicar.", "acao")

    def excluir_usuario_monitorado(self, user_id):
        usuario = next((item for item in self.usuarios_cadastrados if item["id"] == user_id), None)
        nome = usuario["nome"] if usuario else user_id
        if not messagebox.askyesno("Excluir usuario", f"Excluir {nome} da lista de usuarios?"):
            return

        self.usuarios_cadastrados = [item for item in self.usuarios_cadastrados if item["id"] != user_id]
        self.renderizar_usuarios_monitorados()
        self.adicionar_log(f"Usuario {user_id} removido. Clique em Salvar usuarios para aplicar.", "acao")

    def coletar_usuarios_da_tela(self):
        usuarios = []
        for usuario in self.usuarios_cadastrados:
            user_id = usuario["id"]
            var_monitorar = self.usuarios_vars.get(user_id)
            usuarios.append({
                "id": user_id,
                "nome": usuario["nome"],
                "monitorar": bool(var_monitorar.get()) if var_monitorar else False,
            })
        return usuarios

    def salvar_usuarios_monitorados(self):
        try:
            config_atualizado = salvar_usuarios_config(CONFIG_PATH, self.coletar_usuarios_da_tela())
        except Exception as e:
            self.adicionar_log(f"Erro ao salvar usuarios: {e}", "erro")
            messagebox.showerror("Erro ao salvar usuarios", str(e))
            return

        self.usuarios_cadastrados = usuarios_para_interface(config_atualizado)
        self.renderizar_usuarios_monitorados()
        self.revalidar_configuracoes(silencioso=True)
        self.adicionar_log("Usuarios monitorados salvos no config.json.", "ok")

        if self.rodando:
            aviso = "Configuracao salva. Reinicie o bot ou use !reload para aplicar."
            self.adicionar_log(aviso, "aviso")
            messagebox.showwarning("Bot em execucao", aviso)
        else:
            messagebox.showinfo("Usuarios salvos", "Configuracao de usuarios salva com sucesso.")

    def criar_card(self, parent, nome, coluna):
        frame = tk.Frame(parent, bg=COR_CARD, highlightthickness=1, highlightbackground="#ded1bd")
        frame.grid(row=0, column=coluna, sticky="ew", padx=4)

        titulo = tk.Label(frame, text=nome, font=("Segoe UI", 9, "bold"), fg=COR_MUTED, bg=COR_CARD)
        titulo.pack(anchor="w", padx=10, pady=(8, 0))

        status = tk.Label(frame, text="--", font=("Segoe UI", 13, "bold"), fg=COR_MUTED, bg=COR_CARD)
        status.pack(anchor="w", padx=10)

        detalhe = tk.Label(
            frame,
            text="Aguardando",
            font=("Segoe UI", 8),
            fg=COR_MUTED,
            bg=COR_CARD,
            wraplength=135,
            justify=tk.LEFT,
        )
        detalhe.pack(anchor="w", padx=10, pady=(0, 8))

        return {"frame": frame, "status": status, "detalhe": detalhe}

    @property
    def env_path(self):
        return ENV_PATH

    def configurar_tags_log(self):
        self.area_logs.tag_configure("info", foreground="#f4f0e8")
        self.area_logs.tag_configure("ok", foreground="#9ee6a8")
        self.area_logs.tag_configure("aviso", foreground="#ffd37a")
        self.area_logs.tag_configure("erro", foreground="#ff9b9b")
        self.area_logs.tag_configure("acao", foreground="#9bd7ff")

    def diagnosticar_configuracoes(self):
        env = dotenv_values(self.env_path)
        token = env.get("DISCORD_TOKEN")
        numero_marmita = env.get("NUMERO_MARMITA")
        numero_chef = env.get("NUMERO_CHEF")
        chave_pix = (env.get("CHAVE_PIX") or "").strip()
        valor_marmita = carregar_valor_marmita(env.get("VALOR_MARMITA"))
        config = carregar_config(CONFIG_PATH)
        config_ok = CONFIG_PATH.exists() and bool(config)
        config_normalizado = normalizar_config(config)

        token_ok = bool(token and token.strip())
        whatsapp_ok = validar_numero_whatsapp(numero_marmita) is not None
        pix_ok = validar_numero_whatsapp(numero_chef) is not None and bool(chave_pix)
        logs_ok = LOG_DIR.exists()

        bloqueios = []
        if not token_ok:
            bloqueios.append("DISCORD_TOKEN ausente")
        if not whatsapp_ok:
            bloqueios.append("NUMERO_MARMITA ausente ou inválido")

        return {
            "token_ok": token_ok,
            "whatsapp_ok": whatsapp_ok,
            "pix_ok": pix_ok,
            "config_ok": config_ok,
            "logs_ok": logs_ok,
            "bloqueios": bloqueios,
            "usuarios_monitoramento": len(config_normalizado["usuarios_monitoramento"]),
            "usuarios_cadastrados": len(config_normalizado["usuarios_cadastrados"]),
            "preferencias": len(config_normalizado["preferencias_sem"]),
            "valor_marmita": valor_marmita,
            "env_path": self.env_path,
            "config_path": CONFIG_PATH,
            "log_dir": LOG_DIR,
        }

    def revalidar_configuracoes(self, silencioso=False):
        self.ultimo_diagnostico = self.diagnosticar_configuracoes()
        diag = self.ultimo_diagnostico

        self.atualizar_card("Bot", "Rodando" if self.rodando else "Parado", "Processo ativo" if self.rodando else "Pronto para iniciar", COR_OK if self.rodando else COR_MUTED)
        self.atualizar_card("WhatsApp", "OK" if diag["whatsapp_ok"] else "Erro", "Número de pedido válido" if diag["whatsapp_ok"] else "Configure NUMERO_MARMITA", COR_OK if diag["whatsapp_ok"] else COR_ERRO)
        self.atualizar_card("PIX", "OK" if diag["pix_ok"] else "Opcional", "Cobrança ativada" if diag["pix_ok"] else "Cobrança PIX desativada", COR_OK if diag["pix_ok"] else COR_AVISO)
        self.atualizar_card("Config", "OK" if diag["config_ok"] else "Aviso", f"{diag['usuarios_monitoramento']} ativos / {diag['usuarios_cadastrados']} cadastrados", COR_OK if diag["config_ok"] else COR_AVISO)
        self.atualizar_card("Logs", "OK" if diag["logs_ok"] else "Aviso", str(diag["log_dir"]), COR_OK if diag["logs_ok"] else COR_AVISO)

        if diag["bloqueios"]:
            self.label_resumo.config(text="Não é possível iniciar: " + "; ".join(diag["bloqueios"]), fg=COR_ERRO)
            self.btn_iniciar.config(state=tk.DISABLED)
        elif self.rodando:
            self.label_resumo.config(text="Bot em execução", fg=COR_OK)
            self.btn_iniciar.config(state=tk.DISABLED)
        else:
            self.label_resumo.config(text=f"Pronto para iniciar · Marmita R$ {diag['valor_marmita']}", fg=COR_OK)
            self.btn_iniciar.config(state=tk.NORMAL)

        if not silencioso:
            self.adicionar_log("Configurações revalidadas.", "ok" if not diag["bloqueios"] else "aviso")
            if diag["bloqueios"]:
                self.adicionar_log("Pendências: " + "; ".join(diag["bloqueios"]), "erro")
            elif not diag["pix_ok"]:
                self.adicionar_log("Cobrança PIX desativada. O bot pode iniciar normalmente.", "aviso")

    def atualizar_card(self, nome, status, detalhe, cor):
        card = self.cards[nome]
        card["status"].config(text=status, fg=cor)
        card["detalhe"].config(text=detalhe)

    def iniciar_bot(self):
        if self.rodando:
            return

        self.revalidar_configuracoes(silencioso=True)
        if self.ultimo_diagnostico.get("bloqueios"):
            mensagem = "\n".join(self.ultimo_diagnostico["bloqueios"])
            self.adicionar_log("Bot não iniciado. Corrija as pendências de configuração.", "erro")
            messagebox.showerror("Configuração incompleta", mensagem)
            return

        self.rodando = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_parar.config(state=tk.NORMAL)
        self.atualizar_card("Bot", "Iniciando", "Abrindo processo do bot", COR_AVISO)
        self.label_resumo.config(text="Iniciando bot...", fg=COR_AVISO)
        self.adicionar_log("Iniciando bot...", "acao")

        env = os.environ.copy()
        env['BOT_MARMITA_MODE'] = 'bot'

        if FROZEN:
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
            exe_path = os.path.join(base_dir, 'BotMarmita.exe')
            cmd = [exe_path]
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bot_script = os.path.join(base_dir, "src", "bot.py")
            cmd = [sys.executable, bot_script]

        try:
            self.processo = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                cwd=base_dir,
                env=env,
            )
        except Exception as e:
            self.rodando = False
            self.btn_parar.config(state=tk.DISABLED)
            self.revalidar_configuracoes(silencioso=True)
            self.adicionar_log(f"Erro ao iniciar o bot: {e}", "erro")
            messagebox.showerror("Erro ao iniciar", str(e))
            return

        self.atualizar_card("Bot", "Rodando", "Processo ativo", COR_OK)
        self.label_resumo.config(text="Bot em execução", fg=COR_OK)
        threading.Thread(target=self.ler_saida, daemon=True).start()

    def ler_saida(self):
        ignorar = ["PyNaCl", "davey", "discord.client", "discord.gateway", "Shard ID"]

        for linha in iter(self.processo.stdout.readline, b''):
            if not self.rodando:
                break
            try:
                texto = linha.decode('utf-8', errors='replace').strip()
                if not texto or any(p in texto for p in ignorar):
                    continue
                self.fila_logs.put(texto)
            except Exception as e:
                self.fila_logs.put(f"Erro ao processar log do bot: {e}")

        if self.processo and self.processo.stdout:
            self.processo.stdout.close()

    def processar_fila(self):
        try:
            while True:
                texto = self.fila_logs.get_nowait()
                self.adicionar_log(texto, self.classificar_log(texto))
        except queue.Empty:
            pass

        if self.rodando and self.processo and self.processo.poll() is not None:
            codigo = self.processo.returncode
            self.adicionar_log(f"Processo do bot encerrou com código {codigo}.", "erro" if codigo else "aviso")
            self.rodando = False
            self.processo = None
            self.btn_parar.config(state=tk.DISABLED)
            self.revalidar_configuracoes(silencioso=True)

        self.root.after(100, self.processar_fila)

    def classificar_log(self, texto):
        texto_lower = texto.lower()
        if "erro" in texto_lower or "❌" in texto:
            return "erro"
        if "aviso" in texto_lower or "warning" in texto_lower or "⚠️" in texto:
            return "aviso"
        if "ativo" in texto_lower or "✅" in texto or "registrado" in texto_lower:
            return "ok"
        return "info"

    def parar_bot(self):
        if not self.rodando:
            return

        self.adicionar_log("Parando bot...", "acao")
        self.rodando = False

        if self.processo and self.processo.poll() is None:
            self.processo.terminate()
            try:
                self.processo.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.processo.kill()
                self.adicionar_log("Processo não respondeu e foi finalizado à força.", "aviso")

        self.processo = None
        self.btn_parar.config(state=tk.DISABLED)
        self.revalidar_configuracoes(silencioso=True)
        self.adicionar_log("Bot parado.", "acao")

    def adicionar_log(self, texto, tag="info"):
        if hasattr(self, 'area_logs'):
            self.area_logs.insert(tk.END, str(texto) + "\n", tag)
            self.area_logs.see(tk.END)

    def limpar_logs(self):
        if hasattr(self, 'area_logs'):
            self.area_logs.delete(1.0, tk.END)

    def abrir_caminho(self, caminho):
        caminho = Path(caminho)
        if not caminho.exists():
            self.adicionar_log(f"Caminho não encontrado: {caminho}", "erro")
            messagebox.showwarning("Caminho não encontrado", str(caminho))
            return

        try:
            os.startfile(caminho)
            self.adicionar_log(f"Abrindo: {caminho}", "acao")
        except Exception as e:
            self.adicionar_log(f"Erro ao abrir {caminho}: {e}", "erro")
            messagebox.showerror("Erro ao abrir", str(e))

    def localizar_pasta_executavel(self):
        if FROZEN:
            return Path(sys.executable).resolve().parent

        projeto = Path(__file__).resolve().parent.parent
        pasta_dist = projeto / "dist" / "BotMarmita"
        if pasta_dist.exists():
            return pasta_dist
        return projeto

    def gerar_pacote_distribuicao(self):
        pasta_origem = self.localizar_pasta_executavel()
        if not pasta_origem.exists():
            messagebox.showerror("Pacote nao gerado", f"Pasta nao encontrada: {pasta_origem}")
            return

        destino_dir = Path.home() / "Desktop"
        if not destino_dir.exists():
            destino_dir = Path.home()

        nome_zip = f"BotMarmita_para_outro_PC_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        destino_zip = destino_dir / nome_zip

        try:
            with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as pacote:
                for arquivo in pasta_origem.rglob("*"):
                    if arquivo.is_file():
                        pacote.write(arquivo, Path("BotMarmita") / arquivo.relative_to(pasta_origem))

                if CONFIG_PATH.exists():
                    pacote.write(CONFIG_PATH, Path("bot_marmita") / "config.json")

                instrucoes = (
                    "INSTALACAO BOT MARMITA\n"
                    "1. Extraia este ZIP no outro computador.\n"
                    "2. Abra a pasta BotMarmita e execute BotMarmita.exe.\n"
                    "3. Para levar os usuarios cadastrados, copie bot_marmita\\config.json para "
                    "C:\\Users\\NOME_DO_USUARIO\\bot_marmita\\config.json no outro computador.\n"
                    "4. Se alterar usuarios com o bot rodando, use !reload ou reinicie o bot.\n"
                )
                pacote.writestr("LEIA-ME.txt", instrucoes)

            self.adicionar_log(f"Pacote gerado: {destino_zip}", "ok")
            messagebox.showinfo("Pacote gerado", f"Pacote criado em:\n{destino_zip}")
        except Exception as e:
            self.adicionar_log(f"Erro ao gerar pacote: {e}", "erro")
            messagebox.showerror("Erro ao gerar pacote", str(e))

    def fechar_janela(self):
        self.parar_bot()
        self.root.destroy()
        os._exit(0)


def main_app():
    root = tk.Tk()
    InterfaceBot(root)
    root.mainloop()


if __name__ == "__main__":
    modo = os.environ.get('BOT_MARMITA_MODE', '')

    if modo == 'bot':
        import asyncio
        import main

        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main.bot.start(main.TOKEN, reconnect=True))
    else:
        main_app()
