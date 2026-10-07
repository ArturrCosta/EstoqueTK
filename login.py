import tkinter as tk
from tkinter import messagebox, ttk

from logger import Logger


# PERSONALIZE AQUI: mantenha estas cores alinhadas ao THEME de gui.py.
LOGIN_THEME = {
    "background": "#f4f6f8",
    "text": "#1f2937",
    "muted": "#6b7280",
    "accent": "#2563eb",
}


class LoginWindow:
    """Janela de autenticacao do sistema."""

    def __init__(self, root, database, on_success):
        self.root = root
        self.database = database
        self.on_success = on_success

        self.root.title("StockFlow - Login")
        self.root.geometry("420x360")
        self.root.resizable(False, False)

        self.setup_styles()
        self.build()

    def setup_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Login.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 9))

    def build(self):
        self.root.configure(bg=LOGIN_THEME["background"])

        frame = tk.Frame(
            self.root,
            bg=LOGIN_THEME["background"],
            padx=35,
            pady=30,
        )
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="STOCKFLOW",
            font=("Segoe UI", 22, "bold"),
            bg=LOGIN_THEME["background"],
            fg=LOGIN_THEME["text"],
        ).pack(pady=(10, 2))

        tk.Label(
            frame,
            text="Controle de Estoque",
            font=("Segoe UI", 11),
            bg=LOGIN_THEME["background"],
            fg=LOGIN_THEME["muted"],
        ).pack(pady=(0, 24))

        tk.Label(
            frame, text="Usuario", bg=LOGIN_THEME["background"], anchor="w"
        ).pack(fill="x")
        self.user_entry = ttk.Entry(frame)
        self.user_entry.pack(fill="x", ipady=6, pady=(4, 12))

        tk.Label(
            frame, text="Senha", bg=LOGIN_THEME["background"], anchor="w"
        ).pack(fill="x")
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.pack(fill="x", ipady=6, pady=(4, 20))

        ttk.Button(
            frame, text="ENTRAR", command=self.login, style="Login.TButton"
        ).pack(fill="x")

        self.user_entry.focus()
        self.password_entry.bind("<Return>", lambda _event: self.login())

    def login(self):
        username = self.user_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Atencao", "Preencha usuario e senha.")
            return

        try:
            if self.database.verify_user(username, password):
                self.on_success()
            else:
                messagebox.showerror("Login", "Usuario ou senha incorretos.")
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror(
                "Erro",
                "Nao foi possivel acessar o banco de dados.\n"
                "Verifique a configuracao e veja o error.log.",
            )
