import tkinter as tk
from tkinter import messagebox, ttk
from decimal import Decimal, InvalidOperation

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from logger import Logger


# PERSONALIZE AQUI: troque estas cores e fontes depois de o sistema estar funcionando.
THEME = {
    "background": "#f4f6f8",
    "sidebar": "#1f2937",
    "sidebar_text": "#ffffff",
    "text": "#1f2937",
    "muted": "#6b7280",
    "panel": "#ffffff",
    "border": "#d9dee5",
    "accent": "#2563eb",
    "danger": "#dc2626",
}


class MainWindow:
    """Janela principal e navegação do sistema."""

    def __init__(self, root, database):
        self.root = root
        self.database = database
        self.window = tk.Toplevel(root)
        self.window.title("StockFlow - Controle de Estoque")
        self.window.geometry("1100x680")
        self.window.minsize(950, 600)
        self.window.configure(bg=THEME["background"])
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.sidebar = None
        self.content = None
        self.build_shell()
        self.show_dashboard()

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
        self.add_nav_button("Movimentações", self.show_movements)

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
            activebackground="#374151",
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
        self.title_label("Dashboard", "Visão geral do estoque atual.")

        try:
            total_products, total_units, low_stock = self.database.dashboard_stats()
            products = self.database.list_products()
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível carregar o dashboard.")
            return

        cards = tk.Frame(self.content, bg=THEME["background"])
        cards.pack(fill="x", padx=28)

        self.stat_card(cards, "PRODUTOS", total_products, 0)
        self.stat_card(cards, "UNIDADES", total_units, 1)
        self.stat_card(cards, "ESTOQUE BAIXO", low_stock, 2)

        chart_frame = tk.Frame(
            self.content,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        chart_frame.pack(fill="both", expand=True, padx=28, pady=22)

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
        self.title_label("Produtos", "Cadastre, consulte, edite e exclua produtos.")

        toolbar = tk.Frame(self.content, bg=THEME["background"])
        toolbar.pack(fill="x", padx=28, pady=(0, 12))
        ttk.Button(toolbar, text="Novo produto", command=self.open_product_form).pack(side="left")
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
            "preco": "Preço",
            "minimo": "Estoque mín.",
        }
        widths = {"id": 50, "nome": 200, "categoria": 150, "quantidade": 100, "preco": 100, "minimo": 100}
        for key in columns:
            self.product_tree.heading(key, text=headings[key])
            self.product_tree.column(key, width=widths[key], anchor="center")
        self.product_tree.column("nome", anchor="w")
        self.product_tree.column("categoria", anchor="w")

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
                )
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível carregar os produtos.")

    def get_selected_product_id(self):
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um produto primeiro.")
            return None
        return int(self.product_tree.item(selected[0], "values")[0])

    def open_product_form(self, product=None):
        dialog = tk.Toplevel(self.window)
        dialog.title("Novo produto" if product is None else "Editar produto")
        dialog.geometry("430x450")
        dialog.resizable(False, False)

        frame = tk.Frame(dialog, padx=25, pady=25)
        frame.pack(fill="both", expand=True)

        fields = [
            ("Nome", "nome"),
            ("Categoria", "categoria"),
            ("Quantidade", "quantidade"),
            ("Preço", "preco"),
            ("Estoque mínimo", "minimo"),
        ]
        entries = {}
        for label, key in fields:
            tk.Label(frame, text=label, anchor="w").pack(fill="x")
            entry = ttk.Entry(frame)
            entry.pack(fill="x", pady=(4, 12), ipady=5)
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
                    raise ValueError("Nome e categoria são obrigatórios.")
                if quantidade < 0 or minimo < 0 or preco < 0:
                    raise ValueError("Os valores não podem ser negativos.")

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
                messagebox.showwarning("Dados inválidos", str(error))
            except Exception as error:
                Logger.registrar(error)
                messagebox.showerror("Erro", "Não foi possível salvar o produto.")

        ttk.Button(frame, text="Salvar", command=save).pack(fill="x", pady=(8, 6), ipady=4)
        ttk.Button(frame, text="Cancelar", command=dialog.destroy).pack(fill="x", ipady=4)

        entries["nome"].focus()

    def edit_selected_product(self):
        product_id = self.get_selected_product_id()
        if product_id is None:
            return
        try:
            product = self.database.get_product(product_id)
            self.open_product_form(product)
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível abrir o produto.")

    def delete_selected_product(self):
        product_id = self.get_selected_product_id()
        if product_id is None:
            return
        if not messagebox.askyesno("Confirmar", "Excluir o produto selecionado?"):
            return
        try:
            self.database.delete_product(product_id)
            self.refresh_products()
            messagebox.showinfo("Sucesso", "Produto excluído.")
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível excluir o produto.")

    def show_movements(self):
        self.clear_content()
        self.title_label("Movimentações", "Registre entradas e saídas do estoque.")

        card = tk.Frame(
            self.content,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=28,
            pady=28,
        )
        card.pack(fill="x", padx=28, pady=(0, 18))

        try:
            products = self.database.list_products()
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível carregar os produtos.")
            return

        tk.Label(card, text="Produto", bg=THEME["panel"], anchor="w").pack(fill="x")
        product_values = [f"{p['id']} - {p['nome']} (estoque: {p['quantidade']})" for p in products]
        product_map = {value: p["id"] for value, p in zip(product_values, products)}
        product_combo = ttk.Combobox(card, values=product_values, state="readonly")
        product_combo.pack(fill="x", pady=(4, 14), ipady=4)

        tk.Label(card, text="Tipo", bg=THEME["panel"], anchor="w").pack(fill="x")
        type_combo = ttk.Combobox(card, values=["ENTRADA", "SAIDA"], state="readonly")
        type_combo.set("ENTRADA")
        type_combo.pack(fill="x", pady=(4, 14), ipady=4)

        tk.Label(card, text="Quantidade", bg=THEME["panel"], anchor="w").pack(fill="x")
        quantity_entry = ttk.Entry(card)
        quantity_entry.pack(fill="x", pady=(4, 18), ipady=5)

        def register():
            try:
                selected_product = product_combo.get()
                if selected_product not in product_map:
                    raise ValueError("Selecione um produto.")
                quantity = int(quantity_entry.get())
                self.database.add_movement(
                    product_map[selected_product], type_combo.get(), quantity
                )
                messagebox.showinfo("Sucesso", "Movimentação registrada.")
                self.show_movements()
            except ValueError as error:
                messagebox.showwarning("Dados inválidos", str(error))
            except Exception as error:
                Logger.registrar(error)
                messagebox.showerror("Erro", "Não foi possível registrar a movimentação.")

        ttk.Button(card, text="Registrar movimentação", command=register).pack(fill="x", ipady=4)

        info = tk.Frame(self.content, bg=THEME["background"])
        info.pack(fill="x", padx=28)
        tk.Label(
            info,
            text="Regra: uma saída maior que o estoque disponível é bloqueada automaticamente.",
            bg=THEME["background"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

    def close(self):
        self.window.destroy()
        self.root.destroy()
