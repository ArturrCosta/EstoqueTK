import hashlib
import hmac
import re
import secrets
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
    """Conexao MySQL e operacoes separadas por usuario autenticado."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or DB_CONFIG.copy()
        self.current_user_id: Optional[int] = None

    def connect(self, include_database: bool = True):
        config = self.config.copy()
        if not include_database:
            config.pop("database", None)
        return mysql.connector.connect(**config)

    def set_current_user(self, user_id: int) -> None:
        """Define o dono dos dados para a sessao atual."""
        self.current_user_id = int(user_id)

    def clear_current_user(self) -> None:
        """Remove o usuario ativo ao sair da conta."""
        self.current_user_id = None

    def _require_user_id(self) -> int:
        if self.current_user_id is None:
            raise RuntimeError("Nenhum usuario autenticado para acessar os dados.")
        return self.current_user_id

    @staticmethod
    def _column_exists(cursor, database_name: str, table_name: str, column_name: str) -> bool:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """,
            (database_name, table_name, column_name),
        )
        return cursor.fetchone()[0] > 0

    @staticmethod
    def _index_exists(cursor, database_name: str, table_name: str, index_name: str) -> bool:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s
            """,
            (database_name, table_name, index_name),
        )
        return cursor.fetchone()[0] > 0

    def initialize_database(self) -> None:
        """Cria as tabelas e migra dados antigos para o usuario admin."""
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

            # Detecta uma instalacao realmente nova para inserir dados de exemplo
            # uma unica vez. Nao recria produtos se um usuario esvaziar o estoque.
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'produtos'
                """,
                (database_name,),
            )
            products_table_existed = cursor.fetchone()[0] > 0

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario VARCHAR(50) NOT NULL UNIQUE,
                    senha VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB
                """
            )
            cursor.execute(
                """
                SELECT CHARACTER_MAXIMUM_LENGTH
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuarios'
                  AND COLUMN_NAME = 'senha'
                """,
                (database_name,),
            )
            senha_column = cursor.fetchone()
            if senha_column and senha_column[0] < 255:
                cursor.execute("ALTER TABLE usuarios MODIFY senha VARCHAR(255) NOT NULL")

            # usuario_id inicialmente aceita NULL para que bancos antigos possam
            # ser migrados sem perder produtos ou historicos existentes.
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS produtos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT NULL,
                    nome VARCHAR(100) NOT NULL,
                    categoria VARCHAR(80) NOT NULL,
                    quantidade INT NOT NULL DEFAULT 0,
                    preco DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    estoque_minimo INT NOT NULL DEFAULT 0
                ) ENGINE=InnoDB
                """
            )
            if not self._column_exists(cursor, database_name, "produtos", "usuario_id"):
                cursor.execute("ALTER TABLE produtos ADD COLUMN usuario_id INT NULL AFTER id")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS movimentacoes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT NULL,
                    produto_id INT NULL,
                    produto_nome VARCHAR(100) NULL,
                    tipo ENUM('ENTRADA', 'SAIDA') NOT NULL,
                    quantidade INT NOT NULL,
                    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )
            if not self._column_exists(cursor, database_name, "movimentacoes", "usuario_id"):
                cursor.execute("ALTER TABLE movimentacoes ADD COLUMN usuario_id INT NULL AFTER id")
            if not self._column_exists(cursor, database_name, "movimentacoes", "produto_nome"):
                cursor.execute(
                    "ALTER TABLE movimentacoes ADD COLUMN produto_nome VARCHAR(100) NULL AFTER produto_id"
                )

            # Mantem o login inicial de compatibilidade e nao substitui contas existentes.
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    ("admin", self.hash_password("admin123")),
                )

            cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", ("admin",))
            admin_row = cursor.fetchone()
            if admin_row:
                legacy_owner_id = int(admin_row[0])
            else:
                cursor.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1")
                first_user_row = cursor.fetchone()
                if first_user_row is None:
                    raise RuntimeError("Nao existe conta para associar os dados antigos.")
                legacy_owner_id = int(first_user_row[0])

            # Todos os registros sem proprietario vieram do modelo antigo, em que
            # os dados eram compartilhados. Associa-os ao admin (ou primeira conta).
            cursor.execute(
                "UPDATE produtos SET usuario_id = %s WHERE usuario_id IS NULL",
                (legacy_owner_id,),
            )
            cursor.execute(
                """
                UPDATE movimentacoes m
                LEFT JOIN produtos p ON p.id = m.produto_id
                SET m.usuario_id = COALESCE(p.usuario_id, %s)
                WHERE m.usuario_id IS NULL
                """,
                (legacy_owner_id,),
            )
            cursor.execute(
                """
                UPDATE movimentacoes m
                INNER JOIN produtos p ON p.id = m.produto_id
                SET m.produto_nome = p.nome
                WHERE m.produto_nome IS NULL OR m.produto_nome = ''
                """
            )
            cursor.execute(
                "UPDATE movimentacoes SET produto_nome = 'Produto removido' WHERE produto_nome IS NULL OR produto_nome = ''"
            )

            # Semeia exemplos somente ao criar pela primeira vez a tabela produtos.
            # Os exemplos pertencem ao admin, nunca a cada novo usuario cadastrado.
            if not products_table_existed:
                sample_products = [
                    (legacy_owner_id, "Teclado", "Perifericos", 12, 80.00, 5),
                    (legacy_owner_id, "Mouse", "Perifericos", 4, 45.00, 5),
                    (legacy_owner_id, "Cabo HDMI", "Cabos", 20, 25.00, 10),
                    (legacy_owner_id, "Webcam", "Acessorios", 7, 120.00, 3),
                ]
                cursor.executemany(
                    """
                    INSERT INTO produtos
                        (usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    sample_products,
                )
                # Busca os IDs inseridos e registra as entradas iniciais.
                cursor.execute(
                    "SELECT id, nome, quantidade FROM produtos WHERE usuario_id = %s AND nome IN (%s, %s, %s, %s)",
                    (legacy_owner_id, "Teclado", "Mouse", "Cabo HDMI", "Webcam"),
                )
                for product_id, name, quantity in cursor.fetchall():
                    cursor.execute(
                        """
                        INSERT INTO movimentacoes
                            (usuario_id, produto_id, produto_nome, tipo, quantidade)
                        VALUES (%s, %s, %s, 'ENTRADA', %s)
                        """,
                        (legacy_owner_id, product_id, name, quantity),
                    )

            # Remove a restricao antiga que proibia dois usuarios distintos de ter
            # produtos com o mesmo nome; a unicidade passa a ser por usuario + nome.
            if self._index_exists(cursor, database_name, "produtos", "uk_produto_nome"):
                cursor.execute("ALTER TABLE produtos DROP INDEX uk_produto_nome")
            if not self._index_exists(cursor, database_name, "produtos", "uk_produto_usuario_nome"):
                cursor.execute(
                    "ALTER TABLE produtos ADD CONSTRAINT uk_produto_usuario_nome UNIQUE (usuario_id, nome)"
                )

            cursor.execute("ALTER TABLE produtos MODIFY usuario_id INT NOT NULL")
            cursor.execute("ALTER TABLE movimentacoes MODIFY usuario_id INT NOT NULL")
            cursor.execute("ALTER TABLE movimentacoes MODIFY produto_id INT NULL")
            cursor.execute("ALTER TABLE movimentacoes MODIFY produto_nome VARCHAR(100) NOT NULL")

            # Recria a FK do produto para preservar o historico quando um produto
            # for excluido. O usuario_id da movimentacao continua preenchido.
            cursor.execute(
                """
                SELECT CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'movimentacoes'
                  AND COLUMN_NAME = 'produto_id' AND REFERENCED_TABLE_NAME = 'produtos'
                """,
                (database_name,),
            )
            for (constraint_name,) in cursor.fetchall():
                cursor.execute(f"ALTER TABLE movimentacoes DROP FOREIGN KEY `{constraint_name}`")
            cursor.execute(
                """
                ALTER TABLE movimentacoes
                ADD CONSTRAINT fk_mov_produto
                FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE SET NULL
                """
            )

            # Relaciona produtos e historicos ao dono da conta.
            cursor.execute(
                """
                SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'produtos'
                  AND COLUMN_NAME = 'usuario_id' AND REFERENCED_TABLE_NAME = 'usuarios'
                """,
                (database_name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    ALTER TABLE produtos ADD CONSTRAINT fk_produtos_usuario
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                    """
                )
            cursor.execute(
                """
                SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'movimentacoes'
                  AND COLUMN_NAME = 'usuario_id' AND REFERENCED_TABLE_NAME = 'usuarios'
                """,
                (database_name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    ALTER TABLE movimentacoes ADD CONSTRAINT fk_mov_usuario
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                    """
                )

            if not self._index_exists(cursor, database_name, "movimentacoes", "idx_movimentacoes_usuario"):
                cursor.execute(
                    "CREATE INDEX idx_movimentacoes_usuario ON movimentacoes (usuario_id, data_hora)"
                )

            conn.commit()
        except Error as error:
            if conn is not None:
                conn.rollback()
            raise RuntimeError(f"Erro ao inicializar o banco: {error}") from error
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()

    @staticmethod
    def hash_password(password: str) -> str:
        """Gera hash PBKDF2 com salt aleatorio para armazenar a senha."""
        iterations = 260_000
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("ascii"), iterations
        ).hex()
        return f"pbkdf2_sha256${iterations}${salt}${digest}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        """Valida hashes PBKDF2 e hashes SHA-256 antigos do projeto."""
        if stored_hash.startswith("pbkdf2_sha256$"):
            try:
                _, iterations_text, salt, expected = stored_hash.split("$", 3)
                iterations = int(iterations_text)
                actual = hashlib.pbkdf2_hmac(
                    "sha256", password.encode("utf-8"), salt.encode("ascii"), iterations
                ).hex()
                return hmac.compare_digest(actual, expected)
            except (ValueError, TypeError):
                return False
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, stored_hash)

    def create_user(self, username: str, password: str) -> None:
        """Cria uma conta nova. Seu estoque inicia vazio e separado."""
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", username):
            raise ValueError(
                "O usuario deve ter de 3 a 50 caracteres e usar apenas letras, "
                "numeros, ponto, hifen ou sublinhado."
            )
        if len(password) < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres.")

        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                (username, self.hash_password(password)),
            )
            conn.commit()
        except IntegrityError as error:
            conn.rollback()
            raise ValueError("Esse usuario ja esta cadastrado.") from error
        finally:
            cursor.close()
            conn.close()

    def authenticate_user(self, username: str, password: str):
        """Retorna os dados da conta autenticada, ou None se forem invalidos."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, usuario, senha FROM usuarios WHERE usuario = %s",
                (username.strip(),),
            )
            row = cursor.fetchone()
            if row is None or not self._verify_password(password, row[2]):
                return None

            if not row[2].startswith("pbkdf2_sha256$"):
                cursor.execute(
                    "UPDATE usuarios SET senha = %s WHERE id = %s",
                    (self.hash_password(password), row[0]),
                )
                conn.commit()
            return {"id": int(row[0]), "usuario": row[1]}
        finally:
            cursor.close()
            conn.close()

    def verify_user(self, username: str, password: str) -> bool:
        """Compatibilidade com chamadas antigas que esperam apenas True/False."""
        return self.authenticate_user(username, password) is not None

    def list_products(self):
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, nome, categoria, quantidade, preco, estoque_minimo
                FROM produtos WHERE usuario_id = %s ORDER BY nome
                """,
                (user_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_product(self, product_id: int):
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, nome, categoria, quantidade, preco, estoque_minimo
                FROM produtos WHERE id = %s AND usuario_id = %s
                """,
                (product_id, user_id),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def create_product(self, nome, categoria, quantidade, preco, estoque_minimo):
        """Cria produto e registra a quantidade inicial como entrada."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO produtos
                    (usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, nome, categoria, quantidade, preco, estoque_minimo),
            )
            product_id = cursor.lastrowid
            if int(quantidade) > 0:
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (usuario_id, produto_id, produto_nome, tipo, quantidade)
                    VALUES (%s, %s, %s, 'ENTRADA', %s)
                    """,
                    (user_id, product_id, nome, quantidade),
                )
            conn.commit()
        except IntegrityError as error:
            conn.rollback()
            if getattr(error, "errno", None) == 1062:
                raise ValueError("Voce ja possui um produto com esse nome.") from error
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def product_name_exists(self, nome, exclude_id=None):
        """Verifica duplicidade apenas no estoque do usuario autenticado."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor()
        try:
            if exclude_id is None:
                cursor.execute(
                    "SELECT 1 FROM produtos WHERE usuario_id = %s AND nome = %s LIMIT 1",
                    (user_id, nome),
                )
            else:
                cursor.execute(
                    """SELECT 1 FROM produtos
                    WHERE usuario_id = %s AND nome = %s AND id <> %s LIMIT 1""",
                    (user_id, nome, exclude_id),
                )
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def add_stock(self, product_id: int, amount: int):
        """Acrescenta unidades ao produto do usuario e registra a entrada."""
        user_id = self._require_user_id()
        if int(amount) <= 0:
            raise ValueError("A quantidade a adicionar deve ser maior que zero.")

        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """SELECT nome, quantidade FROM produtos
                WHERE id = %s AND usuario_id = %s FOR UPDATE""",
                (product_id, user_id),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto nao encontrado na sua conta.")

            new_quantity = int(product["quantidade"]) + int(amount)
            cursor.execute(
                "UPDATE produtos SET quantidade = %s WHERE id = %s AND usuario_id = %s",
                (new_quantity, product_id, user_id),
            )
            cursor.execute(
                """
                INSERT INTO movimentacoes
                    (usuario_id, produto_id, produto_nome, tipo, quantidade)
                VALUES (%s, %s, %s, 'ENTRADA', %s)
                """,
                (user_id, product_id, product["nome"], int(amount)),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def list_categories(self):
        """Retorna categorias usadas pelo usuario autenticado."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT DISTINCT categoria FROM produtos WHERE usuario_id = %s ORDER BY categoria",
                (user_id,),
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def update_product(self, product_id, nome, categoria, quantidade, preco, estoque_minimo):
        """Atualiza produto e registra apenas a diferenca do estoque."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """SELECT nome, quantidade FROM produtos
                WHERE id = %s AND usuario_id = %s FOR UPDATE""",
                (product_id, user_id),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto nao encontrado na sua conta.")

            difference = int(quantidade) - int(product["quantidade"])
            cursor.execute(
                """
                UPDATE produtos
                SET nome = %s, categoria = %s, quantidade = %s,
                    preco = %s, estoque_minimo = %s
                WHERE id = %s AND usuario_id = %s
                """,
                (nome, categoria, quantidade, preco, estoque_minimo, product_id, user_id),
            )
            if difference != 0:
                movement_type = "ENTRADA" if difference > 0 else "SAIDA"
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (usuario_id, produto_id, produto_nome, tipo, quantidade)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, product_id, nome, movement_type, abs(difference)),
                )
            conn.commit()
        except IntegrityError as error:
            conn.rollback()
            if getattr(error, "errno", None) == 1062:
                raise ValueError("Voce ja possui outro produto com esse nome.") from error
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def delete_product(self, product_id: int):
        """Registra a saida final e exclui apenas produto da conta atual."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """SELECT nome, quantidade FROM produtos
                WHERE id = %s AND usuario_id = %s FOR UPDATE""",
                (product_id, user_id),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto nao encontrado na sua conta.")

            cursor.execute(
                """
                INSERT INTO movimentacoes
                    (usuario_id, produto_id, produto_nome, tipo, quantidade)
                VALUES (%s, %s, %s, 'SAIDA', %s)
                """,
                (user_id, product_id, product["nome"], int(product["quantidade"])),
            )
            cursor.execute(
                "DELETE FROM produtos WHERE id = %s AND usuario_id = %s",
                (product_id, user_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def list_movements(self):
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT m.id, COALESCE(p.nome, m.produto_nome) AS produto,
                       m.tipo, m.quantidade, m.data_hora
                FROM movimentacoes m
                LEFT JOIN produtos p ON p.id = m.produto_id
                WHERE m.usuario_id = %s
                ORDER BY m.data_hora DESC, m.id DESC
                LIMIT 50
                """,
                (user_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def dashboard_stats(self):
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM produtos WHERE usuario_id = %s", (user_id,))
            total_products = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COALESCE(SUM(quantidade), 0) FROM produtos WHERE usuario_id = %s",
                (user_id,),
            )
            total_units = cursor.fetchone()[0]
            cursor.execute(
                """SELECT COUNT(*) FROM produtos
                WHERE usuario_id = %s AND quantidade <= estoque_minimo""",
                (user_id,),
            )
            low_stock = cursor.fetchone()[0]
            return total_products, total_units, low_stock
        finally:
            cursor.close()
            conn.close()
