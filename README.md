# StockFlow - Sistema de Controle de Estoque

Protótipo desktop em Python + Tkinter + MySQL desenvolvido para o trabalho de Aplicação Tkinter com Banco de Dados MySQL.

## Requisitos atendidos

- Duas janelas principais: login e sistema.
- CRUD completo de produtos.
- MySQL para persistência.
- Entradas e saídas de estoque.
- Gráfico com Matplotlib.
- Registro de erros em `error.log`.
- Programação Orientada a Objetos.
- Código separado em módulos.
- `banco.sql` para criação do banco.
- `documentacao.pdf` e `apresentacao.pdf` incluídos.

## 1. Instalação

### Criar ambiente virtual

No PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Instalar dependências

```powershell
pip install -r requirements.txt
```

## 2. Configurar o MySQL

Abra `database.py` e confira:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "estoque_db",
}
```

Troque apenas os dados necessários para o seu MySQL.

O programa tenta criar o banco, as tabelas e alguns registros iniciais automaticamente.
Também existe o arquivo `banco.sql` para executar manualmente no MySQL Workbench/phpMyAdmin.

## 3. Executar

```powershell
python main.py
```

Login inicial:

- usuário: `admin`
- senha: `admin123`

## 4. Roteiro de demonstração

1. Fazer login.
2. Abrir Dashboard.
3. Mostrar produtos e o gráfico.
4. Cadastrar um novo produto.
5. Editar o produto.
6. Registrar uma entrada.
7. Registrar uma saída.
8. Tentar uma saída maior que o estoque e mostrar o bloqueio.
9. Excluir o produto.
10. Mostrar `error.log` e explicar como os erros são registrados.

## 5. Onde personalizar a aparência

A interface está concentrada principalmente em `gui.py` e a tela de login em `login.py`.

Em `gui.py`, altere o dicionário `THEME` para trocar cores:

```python
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
```

Depois, vocês podem alterar fontes, tamanhos, textos dos botões, logo/nome, largura da barra lateral e tamanhos das janelas.

A recomendação é mudar uma coisa por vez e testar o sistema a cada mudança.

## 6. Estrutura

```text
SistemaEstoque_Protótipo/
├── main.py
├── database.py
├── login.py
├── gui.py
├── logger.py
├── banco.sql
├── requirements.txt
├── error.log
├── documentacao.pdf
└── apresentacao.pdf
```
