import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator

from logger import Logger
from text_utils import normalize_text


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


def parse_integer_input(value, field_name):
    """Converte um campo para inteiro e mostra uma mensagem clara se falhar."""
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field_name} deve ser um número inteiro, sem casas decimais."
        ) from error


class MainWindow:
    """Janela principal, dashboard, produtos e movimentacoes."""

    def __init__(self, root, database, on_logout=None):
        self.root = root
        self.database = database
        self.on_logout = on_logout
        self.window = tk.Toplevel(root)
        self.window.title("StockFlow - Controle de Estoque")
        self.window.geometry("1100x700")
        self.window.resizable(True, True)
        # Abre maximizada, mas continua sendo uma janela normal do Windows.
        try:
            self.window.state("zoomed")
        except tk.TclError:
            pass
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
        self.sidebar = tk.Frame(self.window, bg=THEME["sidebar"], width=180)
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

        ttk.Button(self.sidebar, text="Sair da conta", command=self.logout).pack(
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
        # O Dashboard usa bind_all para permitir rolagem do mouse sobre os graficos.
        # Remova esse bind ao trocar de tela para nao interceptar a roda em outras telas.
        try:
            self.window.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        self.dashboard_canvas = None
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
        """Mostra indicadores e graficos maiores, organizados verticalmente."""
        self.clear_content()
        self.title_label("Dashboard", "Visao geral do estoque atual.")

        try:
            total_products, total_units, low_stock = self.database.dashboard_stats()
            products = self.database.list_products()
            movement_totals = self.database.dashboard_movement_totals(limit=8)
            gross_revenue = self.database.dashboard_gross_revenue(limit=8)
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel carregar o dashboard.")
            return

        # O conteudo do Dashboard pode ser mais alto que a janela; por isso
        # fica dentro de uma area rolavel, com barra lateral e rolagem do mouse.
        scroll_frame = tk.Frame(self.content, bg=THEME["background"])
        scroll_frame.pack(fill="both", expand=True, padx=(8, 3), pady=(0, 8))

        canvas = tk.Canvas(
            scroll_frame,
            bg=THEME["background"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        dashboard_body = tk.Frame(canvas, bg=THEME["background"])
        body_window = canvas.create_window((0, 0), window=dashboard_body, anchor="nw")
        self.dashboard_canvas = canvas

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_body_width(event):
            canvas.itemconfigure(body_window, width=event.width)

        dashboard_body.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_body_width)

        # Limpa o bind global ao trocar de tela em clear_content().
        canvas.bind_all("<MouseWheel>", self._scroll_dashboard)

        # Indicadores principais.
        cards = tk.Frame(dashboard_body, bg=THEME["background"])
        cards.pack(fill="x", padx=18, pady=(0, 14))
        self.stat_card(cards, "PRODUTOS", total_products, 0)
        self.stat_card(cards, "UNIDADES", total_units, 1)
        self.stat_card(cards, "ESTOQUE BAIXO", low_stock, 2)

        def make_chart_panel(title, subtitle=None):
            """Cria um painel de grafico de largura completa."""
            panel = tk.Frame(
                dashboard_body,
                bg=THEME["panel"],
                highlightbackground=THEME["border"],
                highlightthickness=1,
            )
            panel.pack(fill="x", padx=18, pady=(0, 14))
            tk.Label(
                panel,
                text=title,
                bg=THEME["panel"],
                fg=THEME["text"],
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", padx=14, pady=(12, 2))
            if subtitle:
                tk.Label(
                    panel,
                    text=subtitle,
                    bg=THEME["panel"],
                    fg=THEME["muted"],
                    font=("Segoe UI", 9),
                    justify="left",
                    wraplength=900,
                ).pack(anchor="w", padx=14, pady=(0, 4))
            return panel

        def show_empty(panel, text):
            tk.Label(
                panel,
                text=text,
                bg=THEME["panel"],
                fg=THEME["muted"],
                font=("Segoe UI", 10),
                wraplength=850,
                justify="center",
            ).pack(fill="both", expand=True, padx=16, pady=24)

        def add_canvas(panel, figure):
            figure.tight_layout()
            chart_canvas = FigureCanvasTkAgg(figure, master=panel)
            chart_canvas.draw()
            chart_canvas.get_tk_widget().pack(
                fill="x", expand=True, padx=10, pady=(0, 12)
            )

        # Grafico 1: estoque atual, com cores alternadas para diferenciar os produtos.
        stock_panel = make_chart_panel(
            "Estoque atual",
            "Quantidade disponível de cada produto (mostrando até os 8 maiores estoques).",
        )
        if products:
            stock_products = sorted(
                products, key=lambda item: int(item["quantidade"]), reverse=True
            )[:8]
            names = [item["nome"] for item in stock_products]
            quantities = [int(item["quantidade"]) for item in stock_products]
            figure = Figure(figsize=(9.5, max(3.5, 0.43 * len(names) + 1.0)), dpi=100)
            axis = figure.add_subplot(111)
            bar_colors = [THEME["accent"], "#60a5fa"]
            axis.barh(names, quantities, color=[bar_colors[i % 2] for i in range(len(names))])
            axis.invert_yaxis()
            axis.set_xlabel("Unidades", fontsize=9)
            axis.tick_params(axis="both", labelsize=9)
            axis.grid(axis="x", linestyle=":", alpha=0.35)
            axis.set_axisbelow(True)
            add_canvas(stock_panel, figure)
        else:
            show_empty(stock_panel, "Nenhum produto cadastrado.")

        # Grafico 2: comparacao historica de entradas e saidas, em barras horizontais.
        movement_panel = make_chart_panel(
            "Entradas x saídas",
            "Saídas incluem baixas e ajustes de estoque, não apenas vendas. Os produtos são ordenados pelas maiores saídas.",
        )
        if movement_totals:
            names = [item["produto"] for item in movement_totals]
            entries = [int(item["entradas"]) for item in movement_totals]
            exits = [int(item["saidas"]) for item in movement_totals]
            positions = list(range(len(names)))
            bar_height = 0.36
            figure = Figure(figsize=(9.5, max(3.5, 0.43 * len(names) + 1.0)), dpi=100)
            axis = figure.add_subplot(111)
            axis.barh(
                [position - bar_height / 2 for position in positions],
                entries,
                height=bar_height,
                label="Entradas",
                color=THEME["accent"],
            )
            axis.barh(
                [position + bar_height / 2 for position in positions],
                exits,
                height=bar_height,
                label="Saídas",
                color="#f59e0b",
            )
            axis.set_yticks(positions)
            axis.set_yticklabels(names)
            axis.invert_yaxis()
            axis.set_xlabel("Unidades", fontsize=9)
            axis.tick_params(axis="both", labelsize=9)
            axis.legend(fontsize=9, loc="best", frameon=False, ncol=2)
            axis.grid(axis="x", linestyle=":", alpha=0.35)
            axis.set_axisbelow(True)
            add_canvas(movement_panel, figure)
        else:
            show_empty(
                movement_panel,
                "As movimentações aparecerão aqui quando houver entradas ou saídas.",
            )

        # Grafico 3: valor bruto por produto, com poucos marcadores no eixo e
        # valor exato no final de cada barra para evitar textos sobrepostos.
        revenue_panel = make_chart_panel(
            "Valor bruto das saídas",
            "Soma quantidade × preço unitário registrado no momento de cada saída. Saídas antigas sem preço histórico não entram no cálculo.",
        )
        if gross_revenue:
            revenue_rows = gross_revenue[:8]
            names = [item["produto"] for item in revenue_rows]
            values = [float(item["receita_bruta"]) for item in revenue_rows]
            figure = Figure(figsize=(9.5, max(3.5, 0.43 * len(names) + 1.0)), dpi=100)
            axis = figure.add_subplot(111)
            bar_colors = [THEME["accent"], "#8b5cf6"]
            bars = axis.barh(
                names,
                values,
                color=[bar_colors[i % 2] for i in range(len(names))],
            )
            axis.invert_yaxis()
            axis.set_xlabel("Valor bruto (R$)", fontsize=9)
            axis.tick_params(axis="both", labelsize=9)
            axis.xaxis.set_major_locator(MaxNLocator(nbins=4))
            axis.xaxis.set_major_formatter(
                FuncFormatter(
                    lambda value, _position: "R$ "
                    + f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            )
            max_value = max(values) if values else 0
            axis.set_xlim(left=0, right=max_value * 1.25 if max_value > 0 else 1)
            for bar, value in zip(bars, values):
                value_text = "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                axis.text(
                    value + (max_value * 0.015 if max_value > 0 else 0.02),
                    bar.get_y() + bar.get_height() / 2,
                    value_text,
                    va="center",
                    ha="left",
                    fontsize=9,
                )
            axis.grid(axis="x", linestyle=":", alpha=0.35)
            axis.set_axisbelow(True)
            add_canvas(revenue_panel, figure)
        else:
            show_empty(
                revenue_panel,
                "Ainda não há saídas com preço histórico. Registre uma saída usando uma quantidade negativa na tela Produtos.",
            )

    def _scroll_dashboard(self, event):
        """Rola o Dashboard com a roda do mouse enquanto essa tela estiver aberta."""
        canvas = getattr(self, "dashboard_canvas", None)
        if canvas is not None and canvas.winfo_exists():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
        """Mostra o cadastro de produtos e o ajuste rápido do estoque."""
        self.clear_content()
        self.title_label("Produtos", "Cadastre produtos, edite informações e ajuste o estoque.")

        # Barra de ações do cadastro: botões relacionados ficam alinhados na mesma linha.
        toolbar = tk.Frame(self.content, bg=THEME["background"])
        toolbar.pack(fill="x", padx=20, pady=(0, 12))

        actions_row = tk.Frame(toolbar, bg=THEME["background"])
        actions_row.pack(fill="x")

        ttk.Button(
            actions_row,
            text="+ Novo produto",
            command=self.open_product_form,
            style="Action.TButton",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            actions_row,
            text="Editar selecionado",
            command=self.edit_selected_product,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            actions_row,
            text="Excluir selecionado",
            command=self.delete_selected_product,
        ).pack(side="left")

        # Ajuste rápido: positivo adiciona unidades; negativo retira unidades.
        stock_frame = tk.Frame(
            toolbar,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        stock_frame.pack(fill="x", pady=(12, 0))

        tk.Label(
            stock_frame,
            text="Ajuste de estoque",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(
            stock_frame,
            text="Use um número positivo para entrada e negativo para saída (ex.: 20 ou -20).",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 8))

        tk.Label(
            stock_frame,
            text="Produto",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 3))
        tk.Label(
            stock_frame,
            text="Quantidade (+/-)",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=1, sticky="w", padx=(0, 10), pady=(0, 3))

        self.stock_product_combo = ttk.Combobox(stock_frame, state="readonly", width=45)
        self.stock_product_combo.grid(row=3, column=0, sticky="ew", padx=(0, 10))

        self.stock_amount_entry = ttk.Entry(stock_frame, width=16)
        self.stock_amount_entry.grid(row=3, column=1, sticky="ew", padx=(0, 10))
        self.stock_amount_entry.bind("<Return>", lambda _event: self.apply_stock_adjustment())

        ttk.Button(
            stock_frame,
            text="Aplicar ajuste",
            command=self.apply_stock_adjustment,
            style="Action.TButton",
        ).grid(row=3, column=2, sticky="e")

        stock_frame.columnconfigure(0, weight=4)
        stock_frame.columnconfigure(1, weight=1)

        # Tabela de produtos: ocupa o espaço restante da janela.
        table_frame = tk.Frame(self.content, bg=THEME["panel"])
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        columns = ("id", "nome", "categoria", "quantidade", "preco", "minimo")
        self.product_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "id": "Nº",
            "nome": "Produto",
            "categoria": "Categoria",
            "quantidade": "Quantidade",
            "preco": "Preço",
            "minimo": "Estoque min.",
        }
        widths = {
            "id": 55,
            "nome": 150,
            "categoria": 120,
            "quantidade": 100,
            "preco": 100,
            "minimo": 105,
        }
        for key in columns:
            self.product_tree.heading(key, text=headings[key])
            self.product_tree.column(key, width=widths[key], anchor="center")
        self.product_tree.column("nome", anchor="w")
        self.product_tree.column("categoria", anchor="w")
        self.product_tree.tag_configure("low", foreground=THEME["warning"])

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        self.product_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        self.refresh_products()

    def refresh_products(self):
        """Atualiza a tabela e as opções do seletor de estoque após mudanças."""
        if not hasattr(self, "product_tree"):
            return

        try:
            products = self.database.list_products()
            selected_label = self.stock_product_combo.get() if hasattr(self, "stock_product_combo") else ""
            previous_product_id = getattr(self, "stock_product_map", {}).get(selected_label)

            # Recria as linhas da tabela sem alterar os IDs reais usados pelo banco.
            for item in self.product_tree.get_children():
                self.product_tree.delete(item)

            self.stock_product_map = {}
            for display_number, product in enumerate(products, start=1):
                low = product["quantidade"] <= product["estoque_minimo"]
                self.product_tree.insert(
                    "",
                    "end",
                    iid=str(product["id"]),
                    values=(
                        display_number,
                        product["nome"],
                        product["categoria"],
                        product["quantidade"],
                        f"R$ {float(product['preco']):.2f}",
                        product["estoque_minimo"],
                    ),
                    tags=("low",) if low else (),
                )

                # O seletor mostra também o estoque atual para facilitar a conferência.
                label = f"{product['nome']} — estoque atual: {product['quantidade']}"
                self.stock_product_map[label] = product["id"]

            if hasattr(self, "stock_product_combo"):
                labels = list(self.stock_product_map.keys())
                self.stock_product_combo.configure(values=labels)
                chosen_label = next(
                    (label for label, product_id in self.stock_product_map.items()
                     if product_id == previous_product_id),
                    labels[0] if labels else "",
                )
                self.stock_product_combo.set(chosen_label)

        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível carregar os produtos.")

    def apply_stock_adjustment(self):
        """Aplica entrada (valor positivo) ou saída (valor negativo) de estoque."""
        try:
            selected_product = self.stock_product_combo.get()
            product_id = self.stock_product_map.get(selected_product)
            if product_id is None:
                raise ValueError("Selecione um produto para ajustar o estoque.")

            quantity_text = self.stock_amount_entry.get().strip()
            if not quantity_text:
                raise ValueError("Informe a quantidade. Use 20 para entrada ou -20 para saída.")

            adjustment = parse_integer_input(quantity_text, "A quantidade do ajuste")
            if adjustment == 0:
                raise ValueError("A quantidade não pode ser zero.")

            if adjustment > 0:
                self.database.add_stock(product_id, adjustment)
                success_message = f"Entrada de {adjustment} unidade(s) registrada."
            else:
                quantity_to_remove = abs(adjustment)
                self.database.remove_stock(product_id, quantity_to_remove)
                success_message = f"Saída de {quantity_to_remove} unidade(s) registrada."

            self.stock_amount_entry.delete(0, tk.END)
            self.refresh_products()
            messagebox.showinfo("Sucesso", success_message, parent=self.window)

        except ValueError as error:
            messagebox.showwarning("Quantidade inválida", str(error), parent=self.window)
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Não foi possível ajustar o estoque.", parent=self.window)

    def get_selected_product_id(self):
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showwarning("Atencao", "Selecione um produto primeiro.")
            return None
        return int(selected[0])

    def open_product_form(self, product=None):
        dialog = tk.Toplevel(self.window)
        dialog.title("Novo produto" if product is None else "Editar produto")
        dialog.geometry("520x540")
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
                # Valida os campos vazios antes de converter para numero, para
                # apresentar avisos claros em vez de erros de conversao confusos.
                nome_original = entries["nome"].get().strip()
                categoria_original = entries["categoria"].get().strip()
                quantidade_text = entries["quantidade"].get().strip()
                preco_text = entries["preco"].get().strip()
                minimo_text = entries["minimo"].get().strip()

                if not nome_original:
                    raise ValueError("Informe o nome do produto.")
                if not categoria_original:
                    raise ValueError("Informe a categoria do produto.")
                if not quantidade_text:
                    raise ValueError("Informe a quantidade em estoque.")
                if not preco_text:
                    raise ValueError("Informe o preço do produto.")
                if not minimo_text:
                    raise ValueError("Informe o estoque mínimo.")

                # Padroniza nomes/categorias: minusculas, sem acentos e sem
                # espacos duplicados. A mesma regra tambem existe no banco.
                nome = normalize_text(nome_original)
                categoria = normalize_text(categoria_original)
                if not nome or not categoria:
                    raise ValueError("Nome e categoria devem conter letras ou números.")

                quantidade = parse_integer_input(quantidade_text, "A quantidade em estoque")
                preco = Decimal(preco_text.replace(",", "."))
                minimo = parse_integer_input(minimo_text, "O estoque mínimo")

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
        info.pack(fill="x", padx=20, pady=(0, 12))

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
            wraplength=520,
        ).pack(anchor="w", pady=(5, 0))

        try:
            movements = self.database.list_movements()
        except Exception as error:
            Logger.registrar(error)
            messagebox.showerror("Erro", "Nao foi possivel carregar o historico.")
            return

        history_frame = tk.Frame(self.content, bg=THEME["panel"])
        history_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
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
            "id": "Nº",
            "produto": "Produto",
            "tipo": "Tipo",
            "quantidade": "Quantidade",
            "data": "Data/Hora",
        }
        widths = {"id": 40, "produto": 150, "tipo": 80, "quantidade": 85, "data": 130}
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="center")
        tree.column("produto", anchor="center")
        # O numero exibido no historico tambem e sequencial por conta.
        # O ID real da movimentacao continua guardado apenas no banco.
        for display_number, movement in enumerate(movements, start=1):
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
                    display_number,
                    movement["produto"],
                    movement["tipo"],
                    movement["quantidade"],
                    data_text,
                ),
            )
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def logout(self):
        """Encerra a sessao atual e volta para a tela de login."""
        if not messagebox.askyesno(
            "Sair da conta",
            "Deseja sair da conta e voltar para a tela de login?",
            parent=self.window,
        ):
            return

        self.window.destroy()
        if self.on_logout:
            self.on_logout()
        else:
            self.root.deiconify()

    def close(self):
        """Fecha a aplicacao quando o usuario fecha a janela principal."""
        self.window.destroy()
        self.root.destroy()
