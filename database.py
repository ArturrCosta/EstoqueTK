import hashlib
from typing import Any, Optional

import mysql.connector
from mysql.connector import Error


# PERSONALIZE AQUI: altere estes dados para o seu MySQL local.
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "estoque_db",
}


class DatabaseManager:
    """Responsável pela conexão e pelas operações de banco de dados."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or DB_CONFIG.copy()

    def connect(self, include_database: bool = True):
        config = self.config.copy()
        if not include_database:
            config.pop("database", None)
        return mysql.connector.connect(**config)

    def initialize_database(self) -> None:
        """Cria o banco e as tabelas se ainda não existirem."""
        conn = None
        cursor = None
        try:
            conn = self.connect(include_database=False)
            cursor = conn.cursor()
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS estoque_db "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.close()
            conn.close()

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
                CREATE TABLE IF NOT EXISTS movimentacoes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    produto_id INT NOT NULL,
                    tipo ENUM('ENTRADA', 'SAIDA') NOT NULL,
                    quantidade INT NOT NULL,
                    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_mov_produto
                        FOREIGN KEY (produto_id) REFERENCES produtos(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )

            cursor.execute("SELECT COUNT(*) FROM usuarios")
            total_users = cursor.fetchone()[0]
            if total_users == 0:
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    ("admin", self.hash_password("admin123")),
                )

            cursor.execute("SELECT COUNT(*) FROM produtos")
            total_products = cursor.fetchone()[0]
            if total_products == 0:
                produtos = [
                    ("Teclado", "Periféricos", 12, 80.00, 5),
                    ("Mouse", "Periféricos", 4, 45.00, 5),
                    ("Cabo HDMI", "Cabos", 20, 25.00, 10),
                    ("Webcam", "Acessórios", 7, 120.00, 3),
                ]
                cursor.executemany(
                    """
                    INSERT INTO produtos
                    (nome, categoria, quantidade, preco, estoque_minimo)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    produtos,
                )

            conn.commit()
        except Error as error:
            raise RuntimeError(f"Erro ao inicializar o banco: {error}") from error
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()

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
                "SELECT id, nome, categoria, quantidade, preco, estoque_minimo "
                "FROM produtos WHERE id = %s",
                (product_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def create_product(self, nome, categoria, quantidade, preco, estoque_minimo):
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
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def update_product(self, product_id, nome, categoria, quantidade, preco, estoque_minimo):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE produtos
                SET nome = %s, categoria = %s, quantidade = %s,
                    preco = %s, estoque_minimo = %s
                WHERE id = %s
                """,
                (nome, categoria, quantidade, preco, estoque_minimo, product_id),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def delete_product(self, product_id: int):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM produtos WHERE id = %s", (product_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def add_movement(self, product_id: int, movement_type: str, quantity: int):
        if quantity <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT quantidade FROM produtos WHERE id = %s FOR UPDATE",
                (product_id,),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto não encontrado.")

            current = int(product["quantidade"])
            if movement_type == "SAIDA":
                if quantity > current:
                    raise ValueError("Estoque insuficiente para realizar a saída.")
                new_quantity = current - quantity
            elif movement_type == "ENTRADA":
                new_quantity = current + quantity
            else:
                raise ValueError("Tipo de movimentação inválido.")

            cursor.execute(
                "INSERT INTO movimentacoes (produto_id, tipo, quantidade) "
                "VALUES (%s, %s, %s)",
                (product_id, movement_type, quantity),
            )
            cursor.execute(
                "UPDATE produtos SET quantidade = %s WHERE id = %s",
                (new_quantity, product_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
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
