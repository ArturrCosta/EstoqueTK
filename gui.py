import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from logger import Logger


# PERSONALIZE AQUI: troque estas cores e fontes para criar a identidade do grupo.
THEME = {
    "background": "#f4f6f8",
    "sidebar": "#1f2937",
    "sidebar_hover": "#374151",
    "sidebar_text": "#ffffff",
    "text": "#1f2937",
    "muted": "#6b7280",
    "panel": "#ffffff",
    "border": "#d9dee5",
    "accent": "#2563eb",
    "accent_dark": "#1d4ed8",
    "danger": "#dc2626",
    "warning": "#b45309",
    "success": "#15803d",
}


class MainWindow:
    """Janela principal, dashboard, produtos e movimentacoes."""

    def __init__(self, root, database):
        self.root = root
        self.database = database
        self.window = tk.Toplevel(root)
        self.window.title("StockFlow - Controle de Estoque")
        self.window.geometry("1100x680")
        self.window.minsize(950, 600)
        self.window.configure(bg=THEME["background"])
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.setup_styles()
        self.sidebar = None
        self.content = None
        self.build_shell()
        self.show_dashboard()

    def setup_styles(self):
        style = ttk.Style(self.window)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=(10, 7))
        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 9))
        style.configure("TEntry", padding=5)
        style.configure("TCombobox", padding=5)
        style.configure(
            "Treeview",
            rowheight=30,
            font=("Segoe UI", 9),
            background=THEME["panel"],
            fieldbackground=THEME["panel"],
        )
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=8)

    def build_shell(self):
        self.sidebar = tk.Frame(self.window, bg=THEME["sidebar"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="STOCKFLOW",
            font=("Segoe UI", 20, "bold"),
            bg=THEME["sidebar"],
            fg=THEME["sidebar_text"],
        ).pack(pady=(28, 2))

        tk.Label(
            self.sidebar,
            text="Controle de Estoque",
            font=("Segoe UI", 9),
            bg=THEME["sidebar"],
            fg="#cbd5e1",
        ).pack(pady=(0, 30))

        self.add_nav_button("Dashboard", self.show_dashboard)
        self.add_nav_button("Produtos", self.show_products)
        self.add_nav_button("Movimentacoes", self.show_movements)

        ttk.Button(self.sidebar, text="Sair", command=self.close).pack(
            side="bottom", fill="x", padx=22, pady=22
        )

        self.content = tk.Frame(self.window, bg=THEME["background"])
        self.content.pack(side="left", fill="both", expand=True)

    def add_nav_button(self, text, command):
        button = tk.Button(
            self.sidebar,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            anchor="w",
            padx=20,
            pady=12,
            bg=THEME["sidebar"],
            fg=THEME["sidebar_text"],
            activebackground=THEME["sidebar_hover"],
            activeforeground=THEME["sidebar_text"],
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        button.pack(fill="x", padx=10, pady=2)

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def title_label(self, title, subtitle):
        frame = tk.Frame(self.content, bg=THEME["background"])
        frame.pack(fill="x", padx=28, pady=(24, 15))
        tk.Label(
            frame,
            text=title,
            font=("Segoe UI", 22, "bold"),
            bg=THEME["background"],
            fg=THEME["text"],
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=subtitle,
            font=("Segoe UI", 10),
            bg=THEME["background"],
            fg=THEME["muted"],
        ).pack(anchor="w", pady=(2, 0))

    def show_dashboard(self):
        self.clear_content()
        self.title_label("Dashboard", "Visao geral do estoque atual.")

        try:
            total_products, total_units, low_stock = self.database.dashboard_stats()
            products = self.database.list_products()
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel carregar o dashboard.")
            return

        top = tk.Frame(self.content, bg=THEME["background"])
        top.pack(fill="x", padx=28)
        cards = tk.Frame(top, bg=THEME["background"])
        cards.pack(side="left", fill="x", expand=True)
        self.stat_card(cards, "PRODUTOS", total_products, 0)
        self.stat_card(cards, "UNIDADES", total_units, 1)
        self.stat_card(cards, "ESTOQUE BAIXO", low_stock, 2)
        ttk.Button(top, text="Atualizar", command=self.show_dashboard).pack(
            side="right", padx=(12, 0), anchor="n"
        )

        chart_frame = tk.Frame(
            self.content,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        chart_frame.pack(fill="both", expand=True, padx=28, pady=22)

        if products:
            figure = Figure(figsize=(7, 3.6), dpi=100)
            axis = figure.add_subplot(111)
            names = [item["nome"] for item in products]
            quantities = [item["quantidade"] for item in products]
            axis.bar(names, quantities)
            axis.set_title("Quantidade em estoque por produto")
            axis.set_ylabel("Unidades")
            axis.tick_params(axis="x", rotation=25)
            figure.tight_layout()

            canvas = FigureCanvasTkAgg(figure, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        else:
            tk.Label(
                chart_frame,
                text="Nenhum produto cadastrado para gerar o grafico.",
                font=("Segoe UI", 11),
                bg=THEME["panel"],
                fg=THEME["muted"],
            ).pack(expand=True)

    def stat_card(self, parent, title, value, column):
        card = tk.Frame(
            parent,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        parent.columnconfigure(column, weight=1)

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 9, "bold"),
            bg=THEME["panel"],
            fg=THEME["muted"],
        ).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(
            card,
            text=str(value),
            font=("Segoe UI", 24, "bold"),
            bg=THEME["panel"],
            fg=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(0, 16))

    def show_products(self):
        self.clear_content()
        self.title_label("Produtos", "Cadastre produtos, ajuste dados e adicione estoque.")

        toolbar = tk.Frame(self.content, bg=THEME["background"])
        toolbar.pack(fill="x", padx=28, pady=(0, 12))
        ttk.Button(toolbar, text="Novo produto", command=self.open_product_form).pack(side="left")
        ttk.Button(toolbar, text="Adicionar estoque", command=self.open_add_stock_dialog).pack(
            side="left", padx=8
        )
        ttk.Button(toolbar, text="Editar selecionado", command=self.edit_selected_product).pack(
            side="left", padx=8
        )
        ttk.Button(toolbar, text="Excluir selecionado", command=self.delete_selected_product).pack(
            side="left"
        )
        ttk.Button(toolbar, text="Atualizar", command=self.refresh_products).pack(side="right")

        table_frame = tk.Frame(self.content, bg=THEME["panel"])
        table_frame.pack(fill="both", expand=True, padx=28, pady=(0, 28))

        columns = ("id", "nome", "categoria", "quantidade", "preco", "minimo")
        self.product_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "id": "ID",
            "nome": "Produto",
            "categoria": "Categoria",
            "quantidade": "Quantidade",
            "preco": "Preco",
            "minimo": "Estoque min.",
        }
        widths = {"id": 50, "nome": 200, "categoria": 150, "quantidade": 100, "preco": 100, "minimo": 100}
        for key in columns:
            self.product_tree.heading(key, text=headings[key])
            self.product_tree.column(key, width=widths[key], anchor="center")
        self.product_tree.column("nome", anchor="w")
        self.product_tree.column("categoria", anchor="w")
        self.product_tree.tag_configure("low", foreground=THEME["warning"])

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        self.product_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

        self.refresh_products()

    def refresh_products(self):
        if not hasattr(self, "product_tree"):
            return
        try:
            for item in self.product_tree.get_children():
                self.product_tree.delete(item)
            for product in self.database.list_products():
                low = product["quantidade"] <= product["estoque_minimo"]
                self.product_tree.insert(
                    "",
                    "end",
                    values=(
                        product["id"],
                        product["nome"],
                        product["categoria"],
                        product["quantidade"],
                        f"R$ {float(product['preco']):.2f}",
                        product["estoque_minimo"],
                    ),
                    tags=("low",) if low else (),
                )
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel carregar os produtos.")

    def get_selected_product_id(self):
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showwarning("Atencao", "Selecione um produto primeiro.")
            return None
        return int(self.product_tree.item(selected[0], "values")[0])

    def open_product_form(self, product=None):
        dialog = tk.Toplevel(self.window)
        dialog.title("Novo produto" if product is None else "Editar produto")
        dialog.geometry("430x520")
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()

        frame = tk.Frame(
            dialog,
            padx=25,
            pady=22,
            bg=THEME["background"],
        )
        frame.pack(fill="both", expand=True)

        fields = [
            ("Nome", "nome"),
            ("Categoria", "categoria"),
            ("Quantidade", "quantidade"),
            ("Preco", "preco"),
            ("Estoque minimo", "minimo"),
        ]
        entries = {}
        for label, key in fields:
            tk.Label(
                frame,
                text=label,
                anchor="w",
                bg=THEME["background"],
                fg=THEME["text"],
                font=("Segoe UI", 9, "bold"),
            ).pack(fill="x")

            if key == "categoria":
                try:
                    categories = self.database.list_categories()
                except Exception as error:
                    Logger.registrar(error)
                    categories = []
                entry = ttk.Combobox(frame, values=categories)
                entry.set("")
            else:
                entry = ttk.Entry(frame)

            entry.pack(fill="x", pady=(4, 10), ipady=5)
            entries[key] = entry

        if product:
            entries["nome"].insert(0, product["nome"])
            entries["categoria"].insert(0, product["categoria"])
            entries["quantidade"].insert(0, product["quantidade"])
            entries["preco"].insert(0, product["preco"])
            entries["minimo"].insert(0, product["estoque_minimo"])

        def save():
            try:
                nome = entries["nome"].get().strip()
                categoria = entries["categoria"].get().strip()
                quantidade = int(entries["quantidade"].get())
                preco = Decimal(entries["preco"].get().replace(",", "."))
                minimo = int(entries["minimo"].get())

                if not nome or not categoria:
                    raise ValueError("Nome e categoria sao obrigatorios.")
                if quantidade < 0 or minimo < 0 or preco < 0:
                    raise ValueError("Os valores nao podem ser negativos.")

                if self.database.product_name_exists(
                    nome, product["id"] if product else None
                ):
                    raise ValueError("Ja existe um produto com esse nome.")

                if product:
                    self.database.update_product(
                        product["id"], nome, categoria, quantidade, preco, minimo
                    )
                else:
                    self.database.create_product(nome, categoria, quantidade, preco, minimo)

                dialog.destroy()
                self.refresh_products()
                messagebox.showinfo("Sucesso", "Produto salvo com sucesso.")
            except (ValueError, InvalidOperation) as error:
                messagebox.showwarning("Dados invalidos", str(error))
            except Exception as error:
                Logger.registrar(error)
                messagebox.showerror("Erro", "Nao foi possivel salvar o produto.")

        buttons = tk.Frame(frame, bg=THEME["background"])
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Salvar", command=save, style="Action.TButton").pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy, style="Action.TButton").pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )

        entries["nome"].focus()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def open_add_stock_dialog(self):
        """Abre uma janela simples para acrescentar unidades a um produto."""
        dialog = tk.Toplevel(self.window)
        dialog.title("Adicionar estoque")
        dialog.geometry("430x330")
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()

        frame = tk.Frame(
            dialog,
            padx=25,
            pady=22,
            bg=THEME["background"],
        )
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Adicionar estoque",
            bg=THEME["background"],
            fg=THEME["text"],
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            text="Escolha o produto e informe somente quantas unidades chegaram.",
            bg=THEME["background"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
            wraplength=370,
            justify="left",
        ).pack(anchor="w", pady=(3, 18))

        try:
            products = self.database.list_products()
        except Exception as error:
            Logger.registrar(error)
            dialog.destroy()
            messagebox.showerror("Erro", "Nao foi possivel carregar os produtos.")
            return

        if not products:
            dialog.destroy()
            messagebox.showwarning("Atencao", "Cadastre um produto antes de adicionar estoque.")
            return

        product_values = [
            f"{product['nome']}  —  estoque atual: {product['quantidade']}"
            for product in products
        ]
        product_map = {value: product["id"] for value, product in zip(product_values, products)}

        tk.Label(
            frame,
            text="Produto",
            bg=THEME["background"],
            fg=THEME["text"],
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x")
        product_combo = ttk.Combobox(
            frame,
            values=product_values,
            state="readonly",
        )
        product_combo.pack(fill="x", pady=(4, 13), ipady=5)
        product_combo.set(product_values[0])

        tk.Label(
            frame,
            text="Unidades para acrescentar",
            bg=THEME["background"],
            fg=THEME["text"],
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x")
        amount_entry = ttk.Entry(frame)
        amount_entry.pack(fill="x", pady=(4, 18), ipady=5)

        def add():
            try:
                selected = product_combo.get()
                if selected not in product_map:
                    raise ValueError("Selecione um produto.")

                amount_text = amount_entry.get().strip()
                if not amount_text:
                    raise ValueError("Informe quantas unidades deseja adicionar.")

                amount = int(amount_text)
                if amount <= 0:
                    raise ValueError("A quantidade deve ser maior que zero.")

                self.database.add_stock(product_map[selected], amount)
                dialog.destroy()
                self.refresh_products()
                messagebox.showinfo(
                    "Sucesso",
                    f"{amount} unidade(s) adicionada(s) ao estoque.",
                )
            except ValueError as error:
                messagebox.showwarning("Dados invalidos", str(error))
            except Exception as error:
                Logger.registrar(error)
                messagebox.showerror("Erro", "Nao foi possivel adicionar o estoque.")

        buttons = tk.Frame(frame, bg=THEME["background"])
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Adicionar", command=add, style="Action.TButton").pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy, style="Action.TButton").pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )

        amount_entry.focus()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def edit_selected_product(self):
        product_id = self.get_selected_product_id()
        if product_id is None:
            return
        try:
            product = self.database.get_product(product_id)
            if product is None:
                raise ValueError("Produto nao encontrado.")
            self.open_product_form(product)
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel abrir o produto.")

    def delete_selected_product(self):
        product_id = self.get_selected_product_id()
        if product_id is None:
            return
        if not messagebox.askyesno("Confirmar", "Excluir o produto selecionado?"):
            return
        try:
            self.database.delete_product(product_id)
            self.refresh_products()
            messagebox.showinfo("Sucesso", "Produto excluido.")
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel excluir o produto.")

    def show_movements(self):
        self.clear_content()
        self.title_label(
            "Movimentacoes",
            "Historico automatico das alteracoes na quantidade dos produtos.",
        )

        info = tk.Frame(
            self.content,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=24,
            pady=18,
        )
        info.pack(fill="x", padx=28, pady=(0, 15))

        tk.Label(
            info,
            text="Como funciona",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            info,
            text=(
                "O historico e automatico: ao cadastrar, a quantidade inicial vira uma ENTRADA; "
                "ao editar, apenas a diferenca vira ENTRADA ou SAIDA; ao excluir, a quantidade "
                "restante e registrada como SAIDA. A tela e somente de consulta."
            ),
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=760,
        ).pack(anchor="w", pady=(5, 0))

        try:
            movements = self.database.list_movements()
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel carregar o historico.")
            return

        history_frame = tk.Frame(self.content, bg=THEME["panel"])
        history_frame.pack(fill="both", expand=True, padx=28, pady=(0, 28))
        tk.Label(
            history_frame,
            text="Ultimas movimentacoes",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        columns = ("id", "produto", "tipo", "quantidade", "data")
        tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=10)
        headings = {
            "id": "ID",
            "produto": "Produto",
            "tipo": "Tipo",
            "quantidade": "Quantidade",
            "data": "Data/Hora",
        }
        widths = {"id": 50, "produto": 250, "tipo": 110, "quantidade": 110, "data": 180}
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="center")
        tree.column("produto", anchor="w")
        for movement in movements:
            data_hora = movement["data_hora"]
            data_text = (
                data_hora.strftime("%d/%m/%Y %H:%M")
                if hasattr(data_hora, "strftime")
                else str(data_hora)
            )
            tree.insert(
                "",
                "end",
                values=(
                    movement["id"],
                    movement["produto"],
                    movement["tipo"],
                    movement["quantidade"],
                    data_text,
                ),
            )
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def close(self):
        self.window.destroy()
        self.root.destroy()
