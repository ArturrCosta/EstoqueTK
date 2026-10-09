# StockFlow - Sistema de Controle de Estoque

Protótipo desktop em Python + Tkinter + MySQL desenvolvido para o trabalho de Aplicação Tkinter com Banco de Dados MySQL.

## Requisitos atendidos

- Janela de login e janela principal.
- Cadastro de novas contas pela tela de login.
- Estoque e historico de movimentacoes separados por conta autenticada.
- Botão **Sair da conta** retorna ao login sem encerrar a aplicação.
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

O programa cria automaticamente o banco `estoque_db`, as tabelas e faz a migracao de bancos antigos. Os produtos e historicos existentes antes desta versao sao associados ao `admin`, preservando os dados ja cadastrados.

O arquivo `banco.sql` descreve a estrutura atual para uma instalacao nova e inclui produtos de exemplo para o `admin`. Em uma base ja existente, abra o programa para que `initialize_database()` aplique a migracao automaticamente; faca um backup antes de migrar.

## 3. Executar

```powershell
python main.py
```

Login inicial:

- usuário: `admin`
- senha: `admin123`

Na tela de login, use **Criar outra conta** para cadastrar um usuário adicional. O nome deve ter de 3 a 50 caracteres e usar letras sem acento, números, ponto, hífen ou sublinhado. A senha deve ter pelo menos 8 caracteres e precisa ser confirmada. Os nomes de usuário não podem se repetir. Todas as contas cadastradas têm as mesmas permissões neste protótipo.

Cada conta possui seu próprio conjunto de produtos e movimentações. Uma conta nova começa com o estoque vazio: ela não vê, altera nem exclui os produtos do `admin` ou de outra conta. O nome de um produto deve ser único dentro da mesma conta, mas contas diferentes podem usar o mesmo nome.

A coluna `id` do MySQL é uma chave primária global e continua contando entre todas as contas (por exemplo, pode chegar a 7 quando uma conta nova cadastra seu primeiro produto). Isso é normal e não mistura os dados: a separação é feita por `usuario_id`. Na tela, a coluna `Nº` mostra uma numeração sequencial própria da conta, começando em 1; o programa mantém o ID interno real para editar ou excluir o registro certo. Todas as janelas do programa usam o tamanho 800x600.

Ao clicar em **Sair da conta**, a janela principal é fechada e o login reaparece. Para encerrar completamente o programa, feche a janela de login.

## 4. Roteiro de demonstração

1. Se necessário, usar **Criar outra conta** para cadastrar um usuário.
2. Fazer login com uma conta válida e mostrar que senha incorreta é recusada.
3. Abrir o Dashboard e mostrar os indicadores.
4. Abrir Produtos.
5. Cadastrar um produto novo.
6. Editar o produto.
7. Aumentar a quantidade de um produto.
8. Reduzir a quantidade de um produto.
9. Tentar colocar uma quantidade negativa e mostrar a validação.
10. Mostrar o histórico das alterações de estoque.
11. Excluir o produto de teste.
12. Voltar ao Dashboard e mostrar o gráfico atualizado.
13. Clicar em **Sair da conta** e demonstrar que retorna ao login.
14. Entrar com a outra conta cadastrada.
15. Abrir `error.log` e explicar a classe Logger.

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
Cria a janela de login, chama `authenticate_user()` para validar as credenciais e identificar o usuário; permite cadastrar novas contas com `create_user()`.

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

- O nome do produto e unico dentro da conta autenticada, evitando duplicados no mesmo estoque.
- Na tela Produtos, o botao **Adicionar estoque** permite escolher um produto em um Combobox e informar apenas quantas unidades foram acrescentadas.
- A edicao continua permitindo informar a quantidade total, o que e util para corrigir um estoque.
- As entradas de estoque ficam registradas automaticamente no historico de movimentacoes.
- Os dados de produtos e movimentacoes sao filtrados pelo usuario autenticado.
- As senhas novas são armazenadas com PBKDF2 e salt aleatório. Hashes SHA-256 antigos são aceitos para compatibilidade e atualizados após um login válido.

