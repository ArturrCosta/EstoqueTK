import hashlib
from typing import Any, Optional

import mysql.connector
from mysql.connector import Error, IntegrityError


# PERSONALIZE AQUI: altere estes dados para o seu MySQL local.
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "estoque_db",
}


class DatabaseManager:
    """Responsavel pela conexao e pelas operacoes com o MySQL."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or DB_CONFIG.copy()

    def connect(self, include_database: bool = True):
        config = self.config.copy()
        if not include_database:
            config.pop("database", None)
        return mysql.connector.connect(**config)

    def initialize_database(self) -> None:
        """Cria o banco, tabelas e ajusta bancos de versoes anteriores."""
        conn = None
        cursor = None
        database_name = self.config.get("database", "estoque_db")

        try:
            conn = self.connect(include_database=False)
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.commit()
            cursor.close()
            conn.close()
            conn = None
            cursor = None

            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario VARCHAR(50) NOT NULL UNIQUE,
                    senha VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS produtos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    categoria VARCHAR(80) NOT NULL,
                    quantidade INT NOT NULL DEFAULT 0,
                    preco DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    estoque_minimo INT NOT NULL DEFAULT 0
                ) ENGINE=InnoDB
                """
            )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'produtos'
                  AND INDEX_NAME = 'uk_produto_nome'
                """,
                (database_name,),
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "ALTER TABLE produtos ADD CONSTRAINT uk_produto_nome UNIQUE (nome)"
                )

            # Em uma instalacao nova, ja cria o historico preparado para
            # continuar existindo mesmo depois da exclusao do produto.
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS movimentacoes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    produto_id INT NULL,
                    produto_nome VARCHAR(100) NOT NULL,
                    tipo ENUM('ENTRADA', 'SAIDA') NOT NULL,
                    quantidade INT NOT NULL,
                    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_mov_produto
                        FOREIGN KEY (produto_id) REFERENCES produtos(id)
                        ON DELETE SET NULL
                ) ENGINE=InnoDB
                """
            )

            self._migrate_movement_table(cursor, database_name)

            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    ("admin", self.hash_password("admin123")),
                )

            cursor.execute("SELECT COUNT(*) FROM produtos")
            if cursor.fetchone()[0] == 0:
                produtos = [
                    ("Teclado", "Perifericos", 12, 80.00, 5),
                    ("Mouse", "Perifericos", 4, 45.00, 5),
                    ("Cabo HDMI", "Cabos", 20, 25.00, 10),
                    ("Webcam", "Acessorios", 7, 120.00, 3),
                ]
                cursor.executemany(
                    """
                    INSERT INTO produtos
                    (nome, categoria, quantidade, preco, estoque_minimo)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    produtos,
                )

                # Os produtos de exemplo tambem entram no historico.
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (produto_id, produto_nome, tipo, quantidade)
                    SELECT id, nome, 'ENTRADA', quantidade
                    FROM produtos
                    WHERE nome IN ('Teclado', 'Mouse', 'Cabo HDMI', 'Webcam')
                      AND quantidade > 0
                    """
                )

            conn.commit()
        except Error as error:
            if conn is not None:
                conn.rollback()
            raise RuntimeError(f"Erro ao inicializar o banco: {error}") from error
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()

    @staticmethod
    def _migrate_movement_table(cursor, database_name: str) -> None:
        """Atualiza a tabela antiga, mantendo as movimentacoes existentes."""
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'movimentacoes'
              AND COLUMN_NAME = 'produto_nome'
            """,
            (database_name,),
        )

        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "ALTER TABLE movimentacoes ADD COLUMN produto_nome VARCHAR(100) NULL AFTER produto_id"
            )
            cursor.execute(
                """
                UPDATE movimentacoes m
                INNER JOIN produtos p ON p.id = m.produto_id
                SET m.produto_nome = p.nome
                WHERE m.produto_nome IS NULL
                """
            )
            cursor.execute(
                "ALTER TABLE movimentacoes MODIFY produto_nome VARCHAR(100) NOT NULL"
            )

        # Bancos das versoes anteriores usavam ON DELETE CASCADE.
        # Trocamos por SET NULL para preservar o historico ao excluir produtos.
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'movimentacoes'
              AND COLUMN_NAME = 'produto_id'
              AND REFERENCED_TABLE_NAME = 'produtos'
            LIMIT 1
            """,
            (database_name,),
        )
        fk_row = cursor.fetchone()
        if fk_row:
            cursor.execute(f"ALTER TABLE movimentacoes DROP FOREIGN KEY `{fk_row[0]}`")

        cursor.execute("ALTER TABLE movimentacoes MODIFY produto_id INT NULL")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.REFERENTIAL_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = %s
              AND TABLE_NAME = 'movimentacoes'
              AND CONSTRAINT_NAME = 'fk_mov_produto'
            """,
            (database_name,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                ALTER TABLE movimentacoes
                ADD CONSTRAINT fk_mov_produto
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
                ON DELETE SET NULL
                """
            )

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_user(self, username: str, password: str) -> bool:
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM usuarios WHERE usuario = %s AND senha = %s",
                (username, self.hash_password(password)),
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def list_products(self):
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, nome, categoria, quantidade, preco, estoque_minimo
                FROM produtos
                ORDER BY nome
                """
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_product(self, product_id: int):
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, nome, categoria, quantidade, preco, estoque_minimo
                FROM produtos
                WHERE id = %s
                """,
                (product_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def create_product(self, nome, categoria, quantidade, preco, estoque_minimo):
        """Cria o produto e registra a quantidade inicial como entrada."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO produtos
                (nome, categoria, quantidade, preco, estoque_minimo)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (nome, categoria, quantidade, preco, estoque_minimo),
            )
            product_id = cursor.lastrowid

            if int(quantidade) > 0:
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (produto_id, produto_nome, tipo, quantidade)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (product_id, nome, "ENTRADA", quantidade),
                )

            conn.commit()
        except IntegrityError as error:
            conn.rollback()
            if getattr(error, "errno", None) == 1062:
                raise ValueError("Ja existe um produto com esse nome.") from error
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def product_name_exists(self, nome, exclude_id=None):
        """Verifica se ja existe um produto com esse nome."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            if exclude_id is None:
                cursor.execute(
                    "SELECT 1 FROM produtos WHERE nome = %s LIMIT 1",
                    (nome,),
                )
            else:
                cursor.execute(
                    "SELECT 1 FROM produtos WHERE nome = %s AND id <> %s LIMIT 1",
                    (nome, exclude_id),
                )
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def add_stock(self, product_id: int, amount: int):
        """Acrescenta unidades ao estoque e registra a entrada no historico."""
        if int(amount) <= 0:
            raise ValueError("A quantidade a adicionar deve ser maior que zero.")

        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT nome, quantidade FROM produtos WHERE id = %s FOR UPDATE",
                (product_id,),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto nao encontrado.")

            new_quantity = int(product["quantidade"]) + int(amount)
            cursor.execute(
                "UPDATE produtos SET quantidade = %s WHERE id = %s",
                (new_quantity, product_id),
            )
            cursor.execute(
                """
                INSERT INTO movimentacoes
                    (produto_id, produto_nome, tipo, quantidade)
                VALUES (%s, %s, %s, %s)
                """,
                (product_id, product["nome"], "ENTRADA", int(amount)),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()


    def list_categories(self):
        """Retorna as categorias ja utilizadas, em ordem alfabetica."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT DISTINCT categoria FROM produtos ORDER BY categoria"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def update_product(self, product_id, nome, categoria, quantidade, preco, estoque_minimo):
        """Atualiza o produto e registra automaticamente a diferenca no estoque."""
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT nome, quantidade FROM produtos WHERE id = %s FOR UPDATE",
                (product_id,),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto nao encontrado.")

            current = int(product["quantidade"])
            difference = int(quantidade) - current

            cursor.execute(
                """
                UPDATE produtos
                SET nome = %s,
                    categoria = %s,
                    quantidade = %s,
                    preco = %s,
                    estoque_minimo = %s
                WHERE id = %s
                """,
                (nome, categoria, quantidade, preco, estoque_minimo, product_id),
            )

            if difference > 0:
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (produto_id, produto_nome, tipo, quantidade)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (product_id, nome, "ENTRADA", difference),
                )
            elif difference < 0:
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (produto_id, produto_nome, tipo, quantidade)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (product_id, nome, "SAIDA", abs(difference)),
                )

            conn.commit()
        except IntegrityError as error:
            conn.rollback()
            if getattr(error, "errno", None) == 1062:
                raise ValueError("Ja existe outro produto com esse nome.") from error
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def delete_product(self, product_id: int):
        """Exclui o produto e registra a quantidade restante como saida."""
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT nome, quantidade FROM produtos WHERE id = %s FOR UPDATE",
                (product_id,),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto nao encontrado.")

            cursor.execute(
                """
                INSERT INTO movimentacoes
                    (produto_id, produto_nome, tipo, quantidade)
                VALUES (%s, %s, %s, %s)
                """,
                (product_id, product["nome"], "SAIDA", int(product["quantidade"])),
            )

            cursor.execute("DELETE FROM produtos WHERE id = %s", (product_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def list_movements(self):
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    m.id,
                    COALESCE(p.nome, m.produto_nome) AS produto,
                    m.tipo,
                    m.quantidade,
                    m.data_hora
                FROM movimentacoes m
                LEFT JOIN produtos p ON p.id = m.produto_id
                ORDER BY m.data_hora DESC, m.id DESC
                LIMIT 50
                """
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def dashboard_stats(self):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM produtos")
            total_products = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(quantidade), 0) FROM produtos")
            total_units = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM produtos WHERE quantidade <= estoque_minimo"
            )
            low_stock = cursor.fetchone()[0]
            return total_products, total_units, low_stock
        finally:
            cursor.close()
            conn.close()
