import tkinter as tk
from tkinter import scrolledtext
import threading
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

class InterfaceBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Marmita - Netsul")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        self.rodando = False
        self.loop = None
        self.thread = None
        
        self.criar_widgets()
        self.log_original = main.log.info
        
        def log_wrapper(msg):
            self.adicionar_log(msg)
        main.log.info = log_wrapper
    
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
        
        self.thread = threading.Thread(target=self.rodar_bot, daemon=True)
        self.thread.start()
    
    def rodar_bot(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(main.bot.start(main.TOKEN, reconnect=True))
    
    def parar_bot(self):
        if not self.rodando:
            return
        
        self.adicionar_log("■ Parando bot...")
        try:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(main.bot.close(), self.loop)
        except:
            pass
        
        self.rodando = False
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_parar.config(state=tk.DISABLED)
        self.label_status.config(text="Status: Parado", fg="red")
        self.adicionar_log("■ Bot parado")
    
    def adicionar_log(self, texto):
        if hasattr(self, 'area_logs'):
            self.area_logs.insert(tk.END, texto + "\n")
            self.area_logs.see(tk.END)
    
    def limpar_logs(self):
        if hasattr(self, 'area_logs'):
            self.area_logs.delete(1.0, tk.END)
    
    def fechar_janela(self):
        self.rodando = False
        self.root.destroy()
        import os
        os._exit(0)


def main_app():
    root = tk.Tk()
    app = InterfaceBot(root)
    root.mainloop()


if __name__ == "__main__":
    main_app()
