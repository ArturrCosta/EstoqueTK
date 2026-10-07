# StockFlow - Sistema de Controle de Estoque

Protótipo desktop em Python + Tkinter + MySQL desenvolvido para o trabalho de Aplicação Tkinter com Banco de Dados MySQL.

## Requisitos atendidos

- Janela de login e janela principal.
- CRUD completo de produtos.
- MySQL para persistência.
- Registro automatico de movimentacoes ao cadastrar, editar ou excluir produtos.
- Histórico das últimas movimentações.
- Dashboard com indicadores.
- Gráfico com Matplotlib.
- Registro de erros em `error.log`.
- Programação Orientada a Objetos.
- Código separado em módulos.
- `banco.sql` para criação manual do banco.
- `documentacao.pdf` e `apresentacao.pdf`.

## 1. Instalação

### Criar ambiente virtual

No PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Instalar dependências

```powershell
pip install -r requirements.txt
```

## 2. Configurar o MySQL

Abra o MySQL pelo XAMPP ou pelo seu servidor local e confira `database.py`:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "estoque_db",
}
```

Altere apenas os dados necessários para seu MySQL.

O programa cria automaticamente o banco `estoque_db`, as três tabelas e alguns registros iniciais.

Também existe `banco.sql` para executar manualmente no phpMyAdmin/MySQL Workbench.

## 3. Executar

```powershell
python main.py
```

Login inicial:

- usuário: `admin`
- senha: `admin123`

## 4. Roteiro de demonstração

1. Fazer login.
2. Abrir o Dashboard e mostrar os indicadores.
3. Abrir Produtos.
4. Cadastrar um produto novo.
5. Editar o produto.
6. Aumentar a quantidade de um produto.
7. Reduzir a quantidade de um produto.
8. Tentar colocar uma quantidade negativa e mostrar a validação.
9. Mostrar o histórico das alterações de estoque.
10. Excluir o produto de teste.
11. Voltar ao Dashboard e mostrar o gráfico atualizado.
12. Abrir `error.log` e explicar a classe Logger.

## 5. Onde personalizar a aparência

A interface está concentrada em `gui.py` e o login em `login.py`. A tela de Movimentações é somente de consulta: o cadastro registra a quantidade inicial, a edição registra a diferença e a exclusão registra a quantidade restante.

### Cores

Em `gui.py`, altere o dicionário `THEME`:

```python
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
```

Depois vocês podem alterar fontes, tamanhos, textos, nome/logo, largura da barra lateral e tamanhos das janelas.

A recomendação é mudar uma coisa por vez e executar o sistema depois de cada alteração.

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
├── UML.txt
├── documentacao.pdf
└── apresentacao.pdf
```

## 7. Como explicar o código na apresentação

### `main.py`
Inicializa o Logger, cria o objeto `DatabaseManager`, inicializa o banco e abre o login.

### `database.py`
Concentra a conexão com o MySQL e o CRUD. O CRUD usa transações para manter o estoque e o histórico sincronizados. Cadastro, edição e exclusão geram registros automáticos de movimentação.

### `login.py`
Cria a primeira janela e chama `verify_user()` para conferir as credenciais.

### `gui.py`
Cria a janela principal, dashboard, tabela de produtos, formulário de CRUD e histórico de movimentações. O gráfico é incorporado ao Tkinter com Matplotlib.

### `logger.py`
Centraliza o registro de exceções no arquivo `error.log`.

## 8. Critérios do trabalho

| Critério | Implementação |
|---|---|
| Funcionalidade | Login, CRUD, movimentações, dashboard e gráfico |
| POO e Organização | Classes e módulos separados por responsabilidade |
| Interface Gráfica | Login, navegação, tabelas, formulários e dashboard |
| Banco de Dados | MySQL com `usuarios`, `produtos` e `movimentacoes` |
| Gráfico/Animação | Gráfico de barras com Matplotlib |
| Log de Erros | `Logger` grava exceções em `error.log` |
| Documentação | `documentacao.pdf` e `UML.txt` |

### Categorias
No cadastro/edicao de produto, o campo Categoria mostra as categorias ja usadas e tambem permite digitar uma categoria nova.

## Regras de produtos e estoque

- O nome do produto e unico no sistema, evitando cadastros duplicados.
- Na tela Produtos, o botao **Adicionar estoque** permite escolher um produto em um Combobox e informar apenas quantas unidades foram acrescentadas.
- A edicao continua permitindo informar a quantidade total, o que e util para corrigir um estoque.
- As entradas de estoque ficam registradas automaticamente no historico de movimentacoes.

