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
        self.root.geometry("800x600")
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

        ttk.Button(
            frame,
            text="Criar outra conta",
            command=self.open_registration,
            style="Login.TButton",
        ).pack(fill="x", pady=(8, 0))

        self.user_entry.focus()
        self.password_entry.bind("<Return>", lambda _event: self.login())

    def login(self):
        username = self.user_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Atencao", "Preencha usuario e senha.")
            return

        try:
            user = self.database.authenticate_user(username, password)
            if user is not None:
                # Evita manter a senha digitada no campo enquanto o login esta oculto.
                self.password_entry.delete(0, tk.END)
                self.on_success(user)
            else:
                messagebox.showerror("Login", "Usuário ou senha incorretos.", parent=self.root)
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror(
                "Erro",
                "Nao foi possivel acessar o banco de dados.\n"
                "Verifique a configuracao e veja o error.log.",
                parent=self.root,
            )

    def open_registration(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Criar conta - StockFlow")
        dialog.geometry("800x600")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=LOGIN_THEME["background"], padx=30, pady=24)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Criar conta",
            font=("Segoe UI", 18, "bold"),
            bg=LOGIN_THEME["background"],
            fg=LOGIN_THEME["text"],
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            frame,
            text="Usuário de 3 a 50 caracteres; senha com 8 ou mais.",
            font=("Segoe UI", 9),
            bg=LOGIN_THEME["background"],
            fg=LOGIN_THEME["muted"],
        ).pack(anchor="w", pady=(0, 16))

        tk.Label(frame, text="Usuário", bg=LOGIN_THEME["background"], anchor="w").pack(fill="x")
        username_entry = ttk.Entry(frame)
        username_entry.pack(fill="x", ipady=5, pady=(4, 10))

        tk.Label(frame, text="Senha", bg=LOGIN_THEME["background"], anchor="w").pack(fill="x")
        password_entry = ttk.Entry(frame, show="*")
        password_entry.pack(fill="x", ipady=5, pady=(4, 10))

        tk.Label(
            frame, text="Confirmar senha", bg=LOGIN_THEME["background"], anchor="w"
        ).pack(fill="x")
        confirm_entry = ttk.Entry(frame, show="*")
        confirm_entry.pack(fill="x", ipady=5, pady=(4, 16))

        def register():
            username = username_entry.get().strip()
            password = password_entry.get()
            confirmation = confirm_entry.get()

            if password != confirmation:
                messagebox.showwarning(
                    "Dados inválidos", "As senhas não coincidem.", parent=dialog
                )
                return

            try:
                self.database.create_user(username, password)
            except ValueError as error:
                messagebox.showwarning("Dados inválidos", str(error), parent=dialog)
                return
            except Exception as error:
                Logger.registrar(error)
                messagebox.showerror(
                    "Erro",
                    "Não foi possível criar a conta. Verifique o banco e o error.log.",
                    parent=dialog,
                )
                return

            self.user_entry.delete(0, tk.END)
            self.user_entry.insert(0, username)
            self.password_entry.delete(0, tk.END)
            messagebox.showinfo(
                "Conta criada", "Conta criada. Agora entre com seu usuário e senha.", parent=dialog
            )
            dialog.destroy()
            self.password_entry.focus_set()

        ttk.Button(
            frame, text="Cadastrar conta", command=register, style="Login.TButton"
        ).pack(fill="x")
        confirm_entry.bind("<Return>", lambda _event: register())
        username_entry.focus_set()
