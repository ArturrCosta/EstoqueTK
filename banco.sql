CREATE DATABASE IF NOT EXISTS estoque_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE estoque_db;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    senha VARCHAR(64) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    categoria VARCHAR(80) NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    preco DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estoque_minimo INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    tipo ENUM('ENTRADA', 'SAIDA') NOT NULL,
    quantidade INT NOT NULL,
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mov_produto
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- Login inicial: admin / admin123
INSERT INTO usuarios (usuario, senha)
SELECT 'admin', SHA2('admin123', 256)
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE usuario = 'admin');

INSERT INTO produtos (nome, categoria, quantidade, preco, estoque_minimo)
SELECT 'Teclado', 'Periféricos', 12, 80.00, 5
WHERE NOT EXISTS (SELECT 1 FROM produtos WHERE nome = 'Teclado');

INSERT INTO produtos (nome, categoria, quantidade, preco, estoque_minimo)
SELECT 'Mouse', 'Periféricos', 4, 45.00, 5
WHERE NOT EXISTS (SELECT 1 FROM produtos WHERE nome = 'Mouse');

INSERT INTO produtos (nome, categoria, quantidade, preco, estoque_minimo)
SELECT 'Cabo HDMI', 'Cabos', 20, 25.00, 10
WHERE NOT EXISTS (SELECT 1 FROM produtos WHERE nome = 'Cabo HDMI');

INSERT INTO produtos (nome, categoria, quantidade, preco, estoque_minimo)
SELECT 'Webcam', 'Acessórios', 7, 120.00, 3
WHERE NOT EXISTS (SELECT 1 FROM produtos WHERE nome = 'Webcam');
