from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether
)

ROOT = Path(__file__).resolve().parent

styles = getSampleStyleSheet()
TITLE = ParagraphStyle('TitleX', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=25, leading=30, textColor=colors.HexColor('#1f2937'), alignment=TA_CENTER, spaceAfter=10)
SUB = ParagraphStyle('SubX', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=16, textColor=colors.HexColor('#6b7280'), alignment=TA_CENTER, spaceAfter=18)
H1 = ParagraphStyle('H1X', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=colors.HexColor('#1f2937'), spaceBefore=4, spaceAfter=9)
H2 = ParagraphStyle('H2X', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#2563eb'), spaceBefore=7, spaceAfter=5)
BODY = ParagraphStyle('BodyX', parent=styles['BodyText'], fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor('#374151'), spaceAfter=7)
SMALL = ParagraphStyle('SmallX', parent=BODY, fontSize=8, leading=11)
CODE = ParagraphStyle('CodeX', parent=BODY, fontName='Courier', fontSize=8, leading=11, backColor=colors.HexColor('#f3f4f6'), borderPadding=6)


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = doc.pagesize
    canvas.setFillColor(colors.HexColor('#2563eb'))
    canvas.rect(0, h - 4*mm, w, 4*mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor('#6b7280'))
    canvas.setFont('Helvetica', 7)
    canvas.drawString(18*mm, 10*mm, 'StockFlow - Sistema de Controle de Estoque')
    canvas.drawRightString(w - 18*mm, 10*mm, f'Pagina {doc.page}')
    canvas.restoreState()


def p(text, style=BODY):
    return Paragraph(text, style)


def make_documentation():
    path = ROOT / 'documentacao.pdf'
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    story = []
    story += [Spacer(1, 32*mm), p('STOCKFLOW', TITLE), p('Documentacao do prototipo - Sistema de Controle de Estoque', SUB)]
    story += [p('Python + Tkinter + MySQL + Matplotlib', ParagraphStyle('Tech', parent=SUB, fontSize=12, textColor=colors.HexColor('#1f2937'))), Spacer(1, 25*mm)]
    story += [p('Objetivo', H1), p('O StockFlow e um prototipo desktop criado para demonstrar um sistema simples de controle de estoque. O projeto concentra cadastro de produtos, movimentacoes, indicadores e grafico em uma aplicacao pequena e facil de explicar.', BODY)]
    story += [p('1. Introducao', H1), p('A aplicacao possui uma janela de login e uma janela principal. Cada conta autenticada acessa somente seus proprios produtos e movimentacoes; contas novas comecam com estoque vazio. Depois da autenticacao, o usuario pode consultar o dashboard e realizar o CRUD de produtos. O historico e automatico: o cadastro registra a quantidade inicial como entrada, a edicao registra apenas a diferenca como entrada ou saida, e a exclusao registra a quantidade restante como saida. O historico continua visivel mesmo depois da exclusao do produto.', BODY)]
    story += [p('2. Atendimento aos criterios do trabalho', H1)]
    data = [
        [p('<b>Criterio</b>', SMALL), p('<b>Como foi atendido</b>', SMALL)],
        [p('Multiplas janelas', SMALL), p('Login, janela principal e formularios secundarios para cadastro/edicao.', SMALL)],
        [p('MySQL', SMALL), p('DatabaseManager cria/acessa estoque_db e filtra produtos e movimentacoes pelo usuario_id da sessao.', SMALL)],
        [p('CRUD completo', SMALL), p('Create, Read, Update e Delete implementados para produtos.', SMALL)],
        [p('Grafico', SMALL), p('Matplotlib gera um grafico de barras com a quantidade atual de cada produto.', SMALL)],
        [p('Log de erros', SMALL), p('Logger registra excecoes em error.log com data, hora e detalhes.', SMALL)],
        [p('POO', SMALL), p('Classes DatabaseManager, LoginWindow, MainWindow e Logger organizam as responsabilidades.', SMALL)],
        [p('Biblioteca extra', SMALL), p('Matplotlib e mysql-connector-python.', SMALL)],
        [p('Documentacao', SMALL), p('Este PDF explica objetivo, arquitetura, banco, execucao e demonstracao.', SMALL)],
    ]
    t = Table(data, colWidths=[45*mm, 125*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5e7eb')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#d1d5db')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    story += [t, PageBreak()]
    story += [p('3. Arquitetura do projeto', H1), p('A aplicacao separa responsabilidades em modulos. main.py inicia o sistema. LoginWindow cuida da autenticacao. MainWindow concentra a interface e as funcionalidades. DatabaseManager concentra as operacoes no MySQL. Logger centraliza o registro de erros.', BODY)]
    arch = [
        [p('<b>Arquivo / classe</b>', SMALL), p('<b>Responsabilidade</b>', SMALL)],
        [p('main.py', SMALL), p('Inicializar Logger, banco e janela de login.', SMALL)],
        [p('database.py / DatabaseManager', SMALL), p('Conexao, migracao do banco, autenticacao e consultas filtradas por usuario_id.', SMALL)],
        [p('login.py / LoginWindow', SMALL), p('Formulario de login e validacao de usuario e senha.', SMALL)],
        [p('gui.py / MainWindow', SMALL), p('Dashboard, produtos, formularios e historico de movimentacoes.', SMALL)],
        [p('logger.py / Logger', SMALL), p('Registro das excecoes no arquivo error.log.', SMALL)],
    ]
    t2 = Table(arch, colWidths=[58*mm, 112*mm])
    t2.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5e7eb')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#d1d5db')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    story += [t2, p('4. Banco de dados', H1)]
    story += [p('Tabelas utilizadas:', H2), p('usuarios - contas de acesso.<br/>produtos - cadastro, saldo atual e usuario_id (dono do registro).<br/>movimentacoes - historico, usuario_id e referencia opcional ao produto.', BODY)]
    story += [p('Cada produto e cada movimentacao pertence a uma conta por meio de usuario_id. As consultas do DatabaseManager filtram pelo usuario autenticado, evitando que uma conta veja ou altere o estoque de outra. O nome e unico dentro de cada conta, e contas diferentes podem cadastrar produtos com o mesmo nome.', BODY)]
    story += [p('Relacionamento: produtos.usuario_id e movimentacoes.usuario_id referenciam usuarios.id. movimentacoes.produto_id referencia produtos.id com ON DELETE SET NULL, e produto_nome guarda o nome no momento da movimentacao. Assim, o historico da propria conta sobrevive a exclusoes. Dados de bancos antigos sem proprietario sao associados ao admin durante a migracao.', BODY)]
    story += [p('5. CRUD de produtos', H1), p('<b>Create:</b> cadastra um produto.<br/><b>Read:</b> lista e consulta produtos.<br/><b>Update:</b> altera os dados de um produto.<br/><b>Delete:</b> exclui o produto selecionado.', BODY)]
    story += [p('6. Movimentacoes', H1), p('Ao cadastrar um produto com quantidade inicial maior que zero, o sistema registra uma ENTRADA. Ao editar, somente a diferenca de quantidade vira ENTRADA ou SAIDA. Ao excluir, a quantidade restante e registrada como SAIDA antes da exclusao. O sistema impede quantidade negativa e o historico mostra as 50 movimentacoes mais recentes.', BODY)]
    story += [p('7. Execucao', H1), p('1. Ligar o MySQL pelo XAMPP ou servidor local.<br/>2. Criar e ativar a venv.<br/>3. Executar pip install -r requirements.txt.<br/>4. Executar python main.py.', BODY)]
    story += [p('Login inicial: admin / admin123', CODE)]
    story += [p('8. Roteiro de demonstracao', H1), p('Login com admin -> mostrar estoque existente -> sair da conta -> criar/entrar com outra conta e comprovar que o estoque esta vazio e separado -> cadastrar um produto -> sair e retornar ao admin -> comprovar que o estoque do admin permaneceu separado -> cadastrar/editar/excluir produto de teste -> conferir entradas e saidas no historico -> dashboard/grafico -> error.log.', BODY)]
    story += [p('9. Personalizacao visual', H1), p('As cores principais estao concentradas em THEME, em gui.py. O login possui LOGIN_THEME em login.py. Tambem podem ser alterados nome do sistema, fontes, espacamentos, botoes, tamanho das janelas e logo, mantendo a logica do banco separada.', BODY)]
    story += [p('10. UML simplificado', H1), p('DatabaseManager fornece os dados para LoginWindow e MainWindow. Logger e utilizado para registrar excecoes. DatabaseManager se comunica com o MySQL. O relacionamento de banco principal e movimentacoes.produto_id -> produtos.id, com nome armazenado no historico para preservar registros de produtos excluidos.', BODY)]
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return path


def make_presentation():
    path = ROOT / 'apresentacao.pdf'
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=18*mm, leftMargin=18*mm, topMargin=14*mm, bottomMargin=14*mm)
    story = []
    slide_title = ParagraphStyle('SlideTitle', parent=H1, fontSize=22, leading=26, textColor=colors.HexColor('#1f2937'), spaceAfter=12)
    bullet = ParagraphStyle('Bullet', parent=BODY, fontSize=14, leading=20, leftIndent=10, bulletIndent=0, spaceAfter=7)
    center = ParagraphStyle('Center', parent=SUB, fontSize=12)

    slides = [
        ('STOCKFLOW', ['Sistema de Controle de Estoque', 'Python + Tkinter + MySQL + Matplotlib']),
        ('Problema e objetivo', ['Centralizar o cadastro de produtos.', 'Controlar o saldo atual do estoque.', 'Registrar automaticamente alteracoes de estoque no cadastro, edicao e exclusao.', 'Visualizar indicadores e um grafico.']),
        ('Funcionalidades', ['Login e cadastro de contas.', 'Cada conta ve somente seus produtos e movimentacoes.', 'Dashboard com produtos, unidades e estoque baixo.', 'CRUD completo de produtos.', 'Historico automatico de entradas e saidas.', 'Bloqueio de saida maior que o estoque.', 'Grafico com Matplotlib.']),
        ('Banco de dados', ['usuarios - autenticacao.', 'produtos possuem usuario_id e nome unico por conta.', 'movimentacoes tambem possuem usuario_id.', 'produto_id liga o historico ao produto quando ele existe.', 'Dados antigos sao migrados para o admin.']),
        ('POO e organizacao', ['DatabaseManager - MySQL e regras de dados.', 'LoginWindow - autenticacao.', 'MainWindow - interface.', 'Logger - registro de erros.', 'main.py - inicio da aplicacao.']),
        ('Demonstracao', ['Login -> Dashboard.', 'Cadastrar produto -> editar -> excluir.', 'Cadastrar -> conferir ENTRADA; editar -> conferir diferenca; excluir -> conferir SAIDA.', 'Tentar colocar quantidade negativa.', 'Mostrar historico e grafico.', 'Mostrar error.log.']),
        ('Codigo que vale explicar', ['Como o DatabaseManager abre conexao.', 'Como o CRUD usa INSERT, SELECT, UPDATE e DELETE.', 'Como cadastro, update_product e delete_product registram o historico automaticamente.', 'Como MainWindow troca as telas.', 'Como Logger grava excecoes.']),
        ('Conclusao', ['Protótipo pequeno, funcional e modular.', 'Todos os requisitos principais ficam demonstraveis.', 'A interface pode receber uma identidade visual propria do grupo.']),
    ]
    for i, (title, points) in enumerate(slides):
        story.append(Spacer(1, 18*mm))
        story.append(p(title, TITLE if i == 0 else slide_title))
        for point in points:
            story.append(p('• ' + point, bullet))
        if i == 0:
            story.append(Spacer(1, 12*mm))
            story.append(p('Trabalho de Aplicacao Tkinter com Banco de Dados MySQL', center))
        if i != len(slides) - 1:
            story.append(PageBreak())
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return path

if __name__ == '__main__':
    make_documentation()
    make_presentation()
    print('PDFs atualizados.')
