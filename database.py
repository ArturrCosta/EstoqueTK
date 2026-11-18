import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import mysql.connector
from mysql.connector import Error, IntegrityError

from text_utils import normalize_text


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

    @staticmethod
    def _backup_path() -> Path:
        """Arquivo portatil que acompanha o projeto e guarda os dados completos."""
        return Path(__file__).resolve().parent / "stockflow_backup.json"

    @staticmethod
    def _json_value(value):
        """Converte tipos do MySQL para valores que o JSON consegue salvar."""
        if isinstance(value, datetime):
            return value.isoformat(sep=" ", timespec="seconds")
        if isinstance(value, Decimal):
            return str(value)
        raise TypeError(f"Tipo nao suportado no backup: {type(value).__name__}")

    def _read_backup(self):
        """Lê e valida o backup sem alterar o banco de dados."""
        path = self._backup_path()
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"O arquivo de recuperacao {path.name} existe, mas nao pode ser lido. "
                "Nao o apague antes de verificar o arquivo."
            ) from error

        tables = snapshot.get("tables") if isinstance(snapshot, dict) else None
        required_tables = ("usuarios", "produtos", "movimentacoes")
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1 or not isinstance(tables, dict) or any(
            not isinstance(tables.get(name), list) for name in required_tables
        ):
            raise RuntimeError(
                f"O arquivo {path.name} nao tem um formato de backup StockFlow valido."
            )
        return snapshot

    def _backup_is_valid(self) -> bool:
        """Indica se existe um backup que pode ser usado para recuperacao."""
        if not self._backup_path().exists():
            return False
        try:
            self._read_backup()
            return True
        except RuntimeError:
            # Se o banco atual tiver dados, a inicializacao podera substituir um
            # backup corrompido; se estiver vazio, a tentativa de restaurar falha
            # de forma segura em vez de apagar a unica copia existente.
            return False

    def _write_backup(self) -> None:
        """Salva usuarios, produtos e historico em arquivo de forma atomica."""
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            tables = {}
            for table in ("usuarios", "produtos", "movimentacoes"):
                cursor.execute(f"SELECT * FROM `{table}` ORDER BY id")
                tables[table] = cursor.fetchall()
            snapshot = {
                "version": 1,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "tables": tables,
            }
        finally:
            cursor.close()
            conn.close()

        path = self._backup_path()
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, default=self._json_value),
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def _restore_backup_if_database_empty(self, cursor) -> bool:
        """Restaura o snapshot quando o banco acabou de ser criado ou esta vazio."""
        path = self._backup_path()
        if not path.exists():
            return False

        counts = {}
        for table in ("usuarios", "produtos", "movimentacoes"):
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            counts[table] = int(cursor.fetchone()[0])

        # Um banco recem-criado tambem pode ter apenas o admin padrao. Nesse caso,
        # produtos e historico vazios indicam que podemos recuperar o snapshot sem
        # misturar os IDs da instalacao nova com os dados que serao restaurados.
        if counts["produtos"] != 0 or counts["movimentacoes"] != 0:
            return False
        cursor.execute("SELECT id, usuario FROM usuarios")
        existing_users = cursor.fetchall()
        if existing_users and not (
            len(existing_users) == 1 and str(existing_users[0][1]).casefold() == "admin"
        ):
            return False

        # Valida antes de apagar o usuario inicial, para nunca perder dados por um
        # arquivo de backup incompleto ou corrompido.
        tables = self._read_backup()["tables"]
        if existing_users:
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (existing_users[0][0],))

        # A ordem respeita os relacionamentos: usuarios, produtos e movimentacoes.
        for user in tables["usuarios"]:
            cursor.execute(
                "INSERT INTO usuarios (id, usuario, senha) VALUES (%s, %s, %s)",
                (user["id"], user["usuario"], user["senha"]),
            )

        for product in tables["produtos"]:
            cursor.execute(
                """INSERT INTO produtos
                   (id, usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    product["id"], product["usuario_id"], product["nome"],
                    product["categoria"], product["quantidade"], product["preco"],
                    product["estoque_minimo"],
                ),
            )

        for movement in tables["movimentacoes"]:
            recorded_at = movement.get("data_hora")
            if isinstance(recorded_at, str):
                recorded_at = datetime.fromisoformat(recorded_at)
            if recorded_at is None:
                # Compatibilidade com snapshots antigos sem a coluna de data/hora.
                recorded_at = datetime.now()
            cursor.execute(
                """INSERT INTO movimentacoes
                   (id, usuario_id, produto_id, produto_nome, tipo, quantidade,
                    preco_unitario, data_hora)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    movement["id"], movement["usuario_id"], movement.get("produto_id"),
                    movement.get("produto_nome") or "Produto removido", movement["tipo"],
                    movement["quantidade"], movement.get("preco_unitario"), recorded_at,
                ),
            )
        return True

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
        backup_existed = self._backup_path().exists()
        backup_was_valid = self._backup_is_valid() if backup_existed else False
        restored_from_backup = False

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
                    preco_unitario DECIMAL(10,2) NULL DEFAULT NULL,
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
            # Guarda o preco unitario apenas nas saidas registradas como venda
            # pelo ajuste negativo de estoque. Registros antigos ficam NULL porque
            # o preco historico deles nao pode ser recuperado com seguranca.
            if not self._column_exists(cursor, database_name, "movimentacoes", "preco_unitario"):
                cursor.execute(
                    "ALTER TABLE movimentacoes ADD COLUMN preco_unitario DECIMAL(10,2) NULL DEFAULT NULL AFTER quantidade"
                )
            if not self._column_exists(cursor, database_name, "movimentacoes", "data_hora"):
                cursor.execute(
                    "ALTER TABLE movimentacoes ADD COLUMN data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                )

            # Se as tres tabelas estiverem vazias, tenta recuperar todos os dados
            # e datas do snapshot antes de criar a conta e os exemplos iniciais.
            restored_from_backup = self._restore_backup_if_database_empty(cursor)

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
            if not products_table_existed and not restored_from_backup:
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
                    "SELECT id, nome, quantidade, preco FROM produtos WHERE usuario_id = %s AND nome IN (%s, %s, %s, %s)",
                    (legacy_owner_id, "Teclado", "Mouse", "Cabo HDMI", "Webcam"),
                )
                for product_id, name, quantity, price in cursor.fetchall():
                    cursor.execute(
                        """
                        INSERT INTO movimentacoes
                            (usuario_id, produto_id, produto_nome, tipo, quantidade, preco_unitario, data_hora)
                        VALUES (%s, %s, %s, 'ENTRADA', %s, %s, %s)
                        """,
                        (legacy_owner_id, product_id, name, quantity, price, datetime.now()),
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
            # Um backup valido existente e mantido para nao sobrescrever uma copia
            # de recuperacao com um banco que possa estar incompleto. Operacoes novas
            # atualizam o snapshot logo depois de cada commit.
            if not backup_was_valid or restored_from_backup:
                self._write_backup()
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
            self._write_backup()
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
                self._write_backup()
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
        nome = normalize_text(nome)
        categoria = normalize_text(categoria)
        if not nome or not categoria:
            raise ValueError("Nome e categoria sao obrigatorios.")

        conn = self.connect()
        cursor = conn.cursor()
        try:
            # Compara nomes ja existentes depois da mesma normalizacao, inclusive
            # registros antigos que possam ter maiusculas ou acentos.
            cursor.execute("SELECT nome FROM produtos WHERE usuario_id = %s", (user_id,))
            if any(normalize_text(row[0]) == nome for row in cursor.fetchall()):
                raise ValueError("Voce ja possui um produto com esse nome.")

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
                        (usuario_id, produto_id, produto_nome, tipo, quantidade, data_hora)
                    VALUES (%s, %s, %s, 'ENTRADA', %s, %s)
                    """,
                    (user_id, product_id, nome, quantidade, datetime.now()),
                )
            conn.commit()
            self._write_backup()
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
        """Verifica duplicidade sem diferenciar maiusculas, acentos ou espacos extras."""
        user_id = self._require_user_id()
        normalized_name = normalize_text(nome)
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, nome FROM produtos WHERE usuario_id = %s", (user_id,))
            for product_id, existing_name in cursor.fetchall():
                if exclude_id is not None and int(product_id) == int(exclude_id):
                    continue
                if normalize_text(existing_name) == normalized_name:
                    return True
            return False
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
                    (usuario_id, produto_id, produto_nome, tipo, quantidade, data_hora)
                VALUES (%s, %s, %s, 'ENTRADA', %s, %s)
                """,
                (user_id, product_id, product["nome"], int(amount), datetime.now()),
            )
            conn.commit()
            self._write_backup()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def remove_stock(self, product_id: int, amount: int):
        """Retira unidades do estoque e registra a saída no histórico."""
        user_id = self._require_user_id()
        amount = int(amount)
        if amount <= 0:
            raise ValueError("A quantidade a retirar deve ser maior que zero.")

        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """SELECT nome, quantidade, preco FROM produtos
                WHERE id = %s AND usuario_id = %s FOR UPDATE""",
                (product_id, user_id),
            )
            product = cursor.fetchone()
            if product is None:
                raise ValueError("Produto não encontrado na sua conta.")

            current_quantity = int(product["quantidade"])
            if amount > current_quantity:
                raise ValueError(
                    f"Estoque insuficiente. Disponível: {current_quantity} unidade(s)."
                )

            new_quantity = current_quantity - amount
            cursor.execute(
                "UPDATE produtos SET quantidade = %s WHERE id = %s AND usuario_id = %s",
                (new_quantity, product_id, user_id),
            )
            cursor.execute(
                """
                INSERT INTO movimentacoes
                    (usuario_id, produto_id, produto_nome, tipo, quantidade, preco_unitario, data_hora)
                VALUES (%s, %s, %s, 'SAIDA', %s, %s, %s)
                """,
                (user_id, product_id, product["nome"], amount, product["preco"], datetime.now()),
            )
            conn.commit()
            self._write_backup()
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
        nome = normalize_text(nome)
        categoria = normalize_text(categoria)
        if not nome or not categoria:
            raise ValueError("Nome e categoria sao obrigatorios.")

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
                "SELECT id, nome FROM produtos WHERE usuario_id = %s AND id <> %s",
                (user_id, product_id),
            )
            for other_product in cursor.fetchall():
                if normalize_text(other_product["nome"]) == nome:
                    raise ValueError("Voce ja possui outro produto com esse nome.")

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
                # Alteracoes de quantidade pelo formulario sao ajustes de inventario,
                # nao vendas: deixam preco_unitario NULL para nao inflar a receita.
                cursor.execute(
                    """
                    INSERT INTO movimentacoes
                        (usuario_id, produto_id, produto_nome, tipo, quantidade, data_hora)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, product_id, nome, movement_type, abs(difference), datetime.now()),
                )
            conn.commit()
            self._write_backup()
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
                    (usuario_id, produto_id, produto_nome, tipo, quantidade, data_hora)
                VALUES (%s, %s, %s, 'SAIDA', %s, %s)
                """,
                (user_id, product_id, product["nome"], int(product["quantidade"]), datetime.now()),
            )
            cursor.execute(
                "DELETE FROM produtos WHERE id = %s AND usuario_id = %s",
                (product_id, user_id),
            )
            conn.commit()
            self._write_backup()
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

    def dashboard_stats(self, category=None):
        """Retorna indicadores gerais ou filtrados por categoria."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor()
        try:
            where = "usuario_id = %s"
            params = [user_id]
            if category:
                where += " AND categoria = %s"
                params.append(category)

            cursor.execute(f"SELECT COUNT(*) FROM produtos WHERE {where}", tuple(params))
            total_products = cursor.fetchone()[0]
            cursor.execute(
                f"SELECT COALESCE(SUM(quantidade), 0) FROM produtos WHERE {where}",
                tuple(params),
            )
            total_units = cursor.fetchone()[0]
            cursor.execute(
                f"SELECT COUNT(*) FROM produtos WHERE {where} AND quantidade <= estoque_minimo",
                tuple(params),
            )
            low_stock = cursor.fetchone()[0]
            return total_products, total_units, low_stock
        finally:
            cursor.close()
            conn.close()

    def dashboard_movement_totals(self, limit=8, category=None):
        """Retorna entradas e saidas por produto, opcionalmente filtradas por categoria atual."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            category_clause = ""
            params = [user_id]
            if category:
                # Quando uma categoria especifica é selecionada, considera apenas
                # movimentações de produtos atualmente pertencentes a ela.
                category_clause = " AND p.categoria = %s"
                params.append(category)
            params.append(int(limit))
            cursor.execute(
                f"""
                SELECT COALESCE(p.nome, m.produto_nome) AS produto,
                       COALESCE(SUM(CASE WHEN m.tipo = 'ENTRADA' THEN m.quantidade ELSE 0 END), 0) AS entradas,
                       COALESCE(SUM(CASE WHEN m.tipo = 'SAIDA' THEN m.quantidade ELSE 0 END), 0) AS saidas
                FROM movimentacoes m
                LEFT JOIN produtos p ON p.id = m.produto_id AND p.usuario_id = m.usuario_id
                WHERE m.usuario_id = %s {category_clause}
                GROUP BY COALESCE(p.nome, m.produto_nome)
                ORDER BY saidas DESC, entradas DESC, produto ASC
                LIMIT %s
                """,
                tuple(params),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def dashboard_gross_revenue(self, limit=8, category=None):
        """Calcula valor bruto das saidas, opcionalmente filtradas por categoria."""
        user_id = self._require_user_id()
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            category_clause = ""
            params = [user_id]
            if category:
                category_clause = " AND p.categoria = %s"
                params.append(category)
            params.append(int(limit))
            cursor.execute(
                f"""
                SELECT COALESCE(p.nome, m.produto_nome) AS produto,
                       COALESCE(SUM(m.quantidade * m.preco_unitario), 0) AS receita_bruta
                FROM movimentacoes m
                LEFT JOIN produtos p ON p.id = m.produto_id AND p.usuario_id = m.usuario_id
                WHERE m.usuario_id = %s
                  AND m.tipo = 'SAIDA'
                  AND m.preco_unitario IS NOT NULL
                  {category_clause}
                GROUP BY COALESCE(p.nome, m.produto_nome)
                ORDER BY receita_bruta DESC, produto ASC
                LIMIT %s
                """,
                tuple(params),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
