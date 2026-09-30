import tkinter as tk
from tkinter import messagebox, ttk

from logger import Logger


class LoginWindow:
    """Janela de entrada do sistema."""

    def __init__(self, root, database, on_success):
        self.root = root
        self.database = database
        self.on_success = on_success

        self.root.title("StockFlow - Login")
        self.root.geometry("420x360")
        self.root.resizable(False, False)

        self.build()

    def build(self):
        self.root.configure(bg="#f4f6f8")

        frame = tk.Frame(self.root, bg="#f4f6f8", padx=35, pady=30)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="STOCKFLOW",
            font=("Segoe UI", 22, "bold"),
            bg="#f4f6f8",
            fg="#1f2937",
        ).pack(pady=(10, 2))

        tk.Label(
            frame,
            text="Controle de Estoque",
            font=("Segoe UI", 11),
            bg="#f4f6f8",
            fg="#6b7280",
        ).pack(pady=(0, 24))

        tk.Label(frame, text="Usuário", bg="#f4f6f8", anchor="w").pack(fill="x")
        self.user_entry = ttk.Entry(frame)
        self.user_entry.pack(fill="x", ipady=6, pady=(4, 12))

        tk.Label(frame, text="Senha", bg="#f4f6f8", anchor="w").pack(fill="x")
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.pack(fill="x", ipady=6, pady=(4, 20))

        ttk.Button(frame, text="ENTRAR", command=self.login).pack(fill="x", ipady=4)

        self.user_entry.focus()
        self.password_entry.bind("<Return>", lambda _event: self.login())

    def login(self):
        username = self.user_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Atenção", "Preencha usuário e senha.")
            return

        try:
            if self.database.verify_user(username, password):
                self.on_success()
            else:
                messagebox.showerror("Login", "Usuário ou senha incorretos.")
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror(
                "Erro",
                "Não foi possível acessar o banco de dados. "
                "Verifique a configuração e veja o error.log.",
            )
