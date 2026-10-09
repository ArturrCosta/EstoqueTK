CREATE DATABASE IF NOT EXISTS estoque_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE estoque_db;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- Conta inicial para demonstracao. O programa aceita esse hash legado e o
-- atualiza para PBKDF2 depois do primeiro login valido.
INSERT INTO usuarios (usuario, senha)
SELECT 'admin', SHA2('admin123', 256)
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE usuario = 'admin');

CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nome VARCHAR(100) NOT NULL,
    categoria VARCHAR(80) NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    preco DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estoque_minimo INT NOT NULL DEFAULT 0,
    CONSTRAINT uk_produto_usuario_nome UNIQUE (usuario_id, nome),
    CONSTRAINT fk_produtos_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    produto_id INT NULL,
    produto_nome VARCHAR(100) NOT NULL,
    tipo ENUM('ENTRADA', 'SAIDA') NOT NULL,
    quantidade INT NOT NULL,
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_movimentacoes_usuario (usuario_id, data_hora),
    CONSTRAINT fk_mov_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mov_produto FOREIGN KEY (produto_id)
        REFERENCES produtos(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Dados de exemplo pertencem somente ao admin; novas contas começam vazias.
INSERT INTO produtos (usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
SELECT u.id, 'Teclado', 'Perifericos', 12, 80.00, 5
FROM usuarios u
WHERE u.usuario = 'admin'
  AND NOT EXISTS (
      SELECT 1 FROM produtos p WHERE p.usuario_id = u.id AND p.nome = 'Teclado'
  );

INSERT INTO produtos (usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
SELECT u.id, 'Mouse', 'Perifericos', 4, 45.00, 5
FROM usuarios u
WHERE u.usuario = 'admin'
  AND NOT EXISTS (
      SELECT 1 FROM produtos p WHERE p.usuario_id = u.id AND p.nome = 'Mouse'
  );

INSERT INTO produtos (usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
SELECT u.id, 'Cabo HDMI', 'Cabos', 20, 25.00, 10
FROM usuarios u
WHERE u.usuario = 'admin'
  AND NOT EXISTS (
      SELECT 1 FROM produtos p WHERE p.usuario_id = u.id AND p.nome = 'Cabo HDMI'
  );

INSERT INTO produtos (usuario_id, nome, categoria, quantidade, preco, estoque_minimo)
SELECT u.id, 'Webcam', 'Acessorios', 7, 120.00, 3
FROM usuarios u
WHERE u.usuario = 'admin'
  AND NOT EXISTS (
      SELECT 1 FROM produtos p WHERE p.usuario_id = u.id AND p.nome = 'Webcam'
  );

-- Registra entrada inicial para os produtos de exemplo que ainda nao tenham
-- uma entrada equivalente no historico.
INSERT INTO movimentacoes (usuario_id, produto_id, produto_nome, tipo, quantidade)
SELECT p.usuario_id, p.id, p.nome, 'ENTRADA', p.quantidade
FROM produtos p
INNER JOIN usuarios u ON u.id = p.usuario_id
WHERE u.usuario = 'admin'
  AND p.nome IN ('Teclado', 'Mouse', 'Cabo HDMI', 'Webcam')
  AND NOT EXISTS (
      SELECT 1 FROM movimentacoes m
      WHERE m.produto_id = p.id AND m.tipo = 'ENTRADA'
        AND m.quantidade = p.quantidade
  );
