import tkinter as tk
from tkinter import scrolledtext
import subprocess
import os
import sys
import threading
import queue

LOGOS_IMPORTANTES = ["✅", "❌", "📋", "⚠️", "NETSUL", "erro", "ERRO", "ativo", "ATIVO", "monitoramento"]

class InterfaceBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Marmita - Netsul")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        self.processo = None
        self.rodando = False
        self.fila_logs = queue.Queue()
        
        self.criar_widgets()
        self.root.after(100, self.processar_fila)
    
    def criar_widgets(self):
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_janela)
        
        frame_controle = tk.Frame(self.root)
        frame_controle.pack(pady=10)
        
        self.btn_iniciar = tk.Button(
            frame_controle, text="▶ Iniciar Bot",
            command=self.iniciar_bot, width=15, bg="green", fg="white"
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)
        
        self.btn_parar = tk.Button(
            frame_controle, text="■ Parar Bot",
            command=self.parar_bot, width=15, state=tk.DISABLED, bg="red", fg="white"
        )
        self.btn_parar.pack(side=tk.LEFT, padx=5)
        
        self.btn_limpar = tk.Button(
            frame_controle, text="🗑 Limpar",
            command=self.limpar_logs, width=10
        )
        self.btn_limpar.pack(side=tk.LEFT, padx=5)
        
        self.label_status = tk.Label(
            self.root, text="Status: Parado",
            font=("Arial", 12, "bold"), fg="red"
        )
        self.label_status.pack(pady=5)
        
        self.area_logs = scrolledtext.ScrolledText(
            self.root, width=70, height=20,
            font=("Consolas", 9)
        )
        self.area_logs.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.adicionar_log("📝 Interface carregada. Clique em Iniciar Bot para começar.")
    
    def iniciar_bot(self):
        if self.rodando:
            return
        
        self.rodando = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_parar.config(state=tk.NORMAL)
        self.label_status.config(text="Status: Rodando", fg="green")
        self.adicionar_log("▶ Iniciando bot...")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bot_script = os.path.join(base_dir, "src", "bot.py")
        
        self.processo = subprocess.Popen(
            [sys.executable, bot_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            cwd=base_dir
        )
        
        threading.Thread(target=self.ler_saida, daemon=True).start()
    
    def ler_saida(self):
        IGNORAR = ["PyNaCl", "davey", "discord.client", "discord.gateway", "Shard ID"]
        
        for linha in iter(self.processo.stdout.readline, b''):
            if not self.rodando:
                break
            try:
                texto = linha.decode('utf-8', errors='replace').strip()
                if any(p in texto for p in IGNORAR):
                    continue
                if any(p in texto for p in LOGOS_IMPORTANTES):
                    self.fila_logs.put(texto)
            except:
                pass
        if self.processo and self.processo.stdout:
            self.processo.stdout.close()
    
    def processar_fila(self):
        try:
            while True:
                texto = self.fila_logs.get_nowait()
                self.adicionar_log(texto)
        except queue.Empty:
            pass
        
        if self.rodando and self.processo and self.processo.poll() is not None:
            self.adicionar_log("⚠️ Processo encerrou inesperadamente")
            self.rodando = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_parar.config(state=tk.DISABLED)
            self.label_status.config(text="Status: Parado", fg="red")
        
        self.root.after(100, self.processar_fila)
    
    def parar_bot(self):
        if not self.rodando:
            return
        
        self.adicionar_log("■ Parando bot...")
        self.rodando = False
        
        if self.processo and self.processo.poll() is None:
            self.processo.terminate()
            try:
                self.processo.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.processo.kill()
        
        self.processo = None
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_parar.config(state=tk.DISABLED)
        self.label_status.config(text="Status: Parado", fg="red")
        self.adicionar_log("■ Bot parado")
    
    def adicionar_log(self, texto):
        if hasattr(self, 'area_logs'):
            self.area_logs.insert(tk.END, str(texto) + "\n")
            self.area_logs.see(tk.END)
    
    def limpar_logs(self):
        if hasattr(self, 'area_logs'):
            self.area_logs.delete(1.0, tk.END)
    
    def fechar_janela(self):
        self.parar_bot()
        self.root.destroy()
        os._exit(0)


def main_app():
    root = tk.Tk()
    app = InterfaceBot(root)
    root.mainloop()


if __name__ == "__main__":
    main_app()
