# Roteiro de apresentacao - StockFlow

Tempo sugerido: 15 a 20 minutos.

## Antonio - abertura e interface

1. Apresentar o problema: cadastro e controle da quantidade de produtos.
2. Mostrar a tela de login.
3. Explicar rapidamente a janela principal e o dashboard.
4. Abrir Produtos e apresentar os campos usados no cadastro.

## Artur C - banco, CRUD e codigo

1. Mostrar `database.py`.
2. Explicar a classe `DatabaseManager` e a conexao com MySQL.
3. Explicar o CRUD: `INSERT`, `SELECT`, `UPDATE` e `DELETE`.
4. Mostrar a classe `MainWindow` e como ela chama o banco.
5. Demonstrar o cadastro de outra conta e explicar que novas senhas são armazenadas com PBKDF2 e salt aleatório; hashes antigos são migrados após login válido.
6. Mostrar que a nova conta começa com estoque vazio e nao consegue ver ou alterar os produtos do admin.
7. Cadastrar um produto com nome igual em contas diferentes para explicar que o estoque e separado por usuario_id.
8. Mostrar que "Sair da conta" retorna para a tela de login sem encerrar a aplicacao.

## Eduardo - movimentacoes, grafico e testes

1. Cadastrar um produto com quantidade inicial e mostrar a ENTRADA automatica.
2. Editar a quantidade para cima e mostrar a ENTRADA apenas da diferenca.
3. Editar a quantidade para baixo e mostrar a SAIDA apenas da diferenca.
4. Excluir o produto de teste e mostrar que a SAIDA da quantidade restante continua no historico.
5. Tentar colocar uma quantidade negativa e mostrar a validacao.
6. Mostrar o historico.
7. Mostrar o grafico do dashboard.
8. Abrir `error.log` e explicar o `Logger`.

## Fechamento

Mostrar rapidamente a estrutura dos arquivos e relacionar o projeto aos criterios do trabalho: multiplas janelas, MySQL, CRUD, grafico, log, biblioteca extra e POO.
