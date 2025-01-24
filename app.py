import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from flask import send_file
from io import BytesIO
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import sqlite3
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Função para conectar ao banco de dados SQLite
def conectar_bd():
    conn = sqlite3.connect('7coins.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para inicializar o banco de dados
def inicializar_bd():
    conn = conectar_bd()
    cursor = conn.cursor()

    # Criação das tabelas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            turma_id INTEGER DEFAULT NULL,
            FOREIGN KEY (turma_id) REFERENCES turmas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            turno TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            turma_id INTEGER NOT NULL,
            saldo INTEGER DEFAULT 0,
            senha TEXT,
            FOREIGN KEY (turma_id) REFERENCES turmas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moderadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            data TEXT,
            tipo_ocorrencia TEXT,
            motivo TEXT,
            professor TEXT,
            chamar_responsavel TEXT,
            data_reuniao TEXT,
            hora_reuniao TEXT,
            total_dias INTEGER DEFAULT 0,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id),
            FOREIGN KEY (turma_id) REFERENCES turmas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responsaveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            aluno_id INTEGER,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conteudo TEXT NOT NULL,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Criar moderador padrão, se não existir
    senha_hash = generate_password_hash('reginaldodiretor123')
    cursor.execute("INSERT OR IGNORE INTO moderadores (login, senha) VALUES ('REGINALDO', ?)", (senha_hash,))

    conn.commit()
    cursor.close()
    conn.close()

# Função para atualizar tabelas existentes
def atualizar_bd():
    conn = conectar_bd()
    cursor = conn.cursor()

    def adicionar_coluna(tabela, coluna, tipo, default=None):
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = [col[1] for col in cursor.fetchall()]
        if coluna not in colunas:
            alter_cmd = f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"
            if default is not None:
                alter_cmd += f" DEFAULT {default}"
            cursor.execute(alter_cmd)
            conn.commit()
            print(f"Coluna '{coluna}' adicionada à tabela '{tabela}'.")

    cursor.close()
    conn.close()
    print("Banco de dados atualizado com sucesso!")

# Inicializar o banco de dados e atualizar tabelas
inicializar_bd()

# Página inicial
@app.route('/')
def index():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT conteudo FROM recados")
    recados = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', recados=recados)

# Login do professor ou moderador
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        conn = conectar_bd()
        cursor = conn.cursor()

        # Verificar se é moderador
        cursor.execute("SELECT senha FROM moderadores WHERE login = ?", (usuario,))
        moderador = cursor.fetchone()

        if moderador and check_password_hash(moderador['senha'], senha):
            session['usuario'] = usuario
            session['tipo'] = 'moderador'
            return redirect(url_for('dashboard_moderador'))

        # Verificar se é professor
        cursor.execute("SELECT senha, status FROM professores WHERE login = ?", (usuario,))
        professor = cursor.fetchone()

        if professor and check_password_hash(professor['senha'], senha):
            if professor['status'] == 'pendente':
                flash("Cadastro pendente de aprovação.")
                return redirect(url_for('login'))
            session['usuario'] = usuario
            session['tipo'] = 'professor'
            return redirect(url_for('dashboard_professor'))

        flash("Usuário ou senha inválidos.")
        return redirect(url_for('login'))

    return render_template('login.html')


# Rota para cadastrar um novo moderador
@app.route('/cadastrar_moderador', methods=['GET', 'POST'])
def cadastrar_moderador():
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        conn = conectar_bd()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO moderadores (login, senha) VALUES (?, ?)", (login, senha_hash))
            conn.commit()
            flash("Moderador cadastrado com sucesso!")
        except sqlite3.IntegrityError:
            flash("Login já está em uso. Escolha outro.")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard_moderador'))

    return render_template('cadastrar_moderador.html')

@app.route('/visualizar_moderadores')
def visualizar_moderadores():
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    # Buscar todos os moderadores cadastrados
    cursor.execute("SELECT id, login FROM moderadores")
    moderadores = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('visualizar_moderadores.html', moderadores=moderadores)

@app.route('/excluir_moderador/<int:moderador_id>', methods=['POST'])
def excluir_moderador(moderador_id):
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM moderadores WHERE id = ?", (moderador_id,))
        conn.commit()
        flash("Moderador excluído com sucesso!")
    except sqlite3.Error as e:
        flash(f"Erro ao excluir moderador: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('visualizar_moderadores'))

# Cadastro de professor
@app.route('/cadastro_professor', methods=['GET', 'POST'])
def cadastro_professor():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        conn = conectar_bd()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO professores (login, senha, status) VALUES (?, ?, 'pendente')", (login, senha_hash))
            conn.commit()
            flash("Cadastro realizado com sucesso. Aguarde aprovação pelo moderador.")
        except sqlite3.IntegrityError:
            flash("Usuário já cadastrado. Escolha outro login.")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('index'))  # Redireciona ao login após cadastro

    return render_template('cadastro_professor.html')

@app.route('/visualizar_professores', methods=['GET'])
def visualizar_professores():
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    # Buscar todos os professores aprovados
    cursor.execute("SELECT id, login FROM professores WHERE status = 'aprovado'")
    professores = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('visualizar_professores.html', professores=professores)

# Dashboard do moderador
@app.route('/dashboard_moderador')
def dashboard_moderador():
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    # Obter professores pendentes
    cursor.execute("SELECT id, login FROM professores WHERE status = 'pendente'")
    professores_pendentes = cursor.fetchall()

    # Obter professores aprovados ou rejeitados
    cursor.execute("SELECT id, login, status FROM professores WHERE status IN ('aprovado', 'rejeitado')")
    professores_aprovados = cursor.fetchall()

    # Obter turmas
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    # Obter alunos
    cursor.execute("""
        SELECT alunos.id, alunos.nome, turmas.nome AS turma_nome
        FROM alunos
        JOIN turmas ON alunos.turma_id = turmas.id
    """)
    alunos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard_moderador.html',
        professores_pendentes=professores_pendentes,
        professores_aprovados=professores_aprovados,
        turmas=turmas,
        alunos=alunos
    )

# Aprovar professor
@app.route('/aprovar_professor/<int:professor_id>', methods=['POST'])
def aprovar_professor(professor_id):
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("UPDATE professores SET status = 'aprovado' WHERE id = ?", (professor_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Professor aprovado com sucesso.")
    return redirect(url_for('dashboard_moderador'))

# Rejeitar professor
@app.route('/rejeitar_professor/<int:professor_id>', methods=['POST'])
def rejeitar_professor(professor_id):
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("UPDATE professores SET status = 'rejeitado' WHERE id = ?", (professor_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Professor rejeitado com sucesso.")
    return redirect(url_for('dashboard_moderador'))

# Excluir professor
@app.route('/excluir_professor/<int:professor_id>', methods=['POST'])
def excluir_professor(professor_id):
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM professores WHERE id = ?", (professor_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Professor excluído com sucesso.")
    return redirect(url_for('dashboard_moderador'))


@app.route('/exclusao', methods=['POST', 'GET'])
def exclusao():
    if request.method == 'POST':
        categoria = request.form.get('categoria')
        item_id = request.form.get('item_id')
        if not categoria or not item_id:
            flash("Por favor, selecione uma categoria e um item.")
            return redirect(url_for('exclusao'))

        conn = conectar_bd()
        cursor = conn.cursor()
        try:
            tabela = {
                'moderador': 'moderadores',
                'professor': 'professores',
                'aluno': 'alunos',
                'responsavel': 'responsaveis',
                'turma': 'turmas',
                'ocorrencia': 'ocorrencias',
            }.get(categoria)

            if tabela:
                cursor.execute(f"DELETE FROM {tabela} WHERE id = ?", (item_id,))
                conn.commit()
                flash(f"Item da categoria '{categoria}' excluído com sucesso!")
            else:
                flash("Categoria inválida.")
        except sqlite3.Error as e:
            flash(f"Erro ao excluir item: {e}")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('exclusao'))

    # Para GET, retorna os dados
    conn = conectar_bd()
    cursor = conn.cursor()

    def safe_fetch(query):
        try:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    moderadores = safe_fetch("SELECT * FROM moderadores")
    professores = safe_fetch("SELECT * FROM professores")
    turmas = safe_fetch("SELECT * FROM turmas")
    alunos = safe_fetch("SELECT * FROM alunos")
    responsaveis = safe_fetch("SELECT * FROM responsaveis")

    cursor.close()
    conn.close()

    return render_template(
        'exclusao.html',
        moderadores=moderadores or [],
        professores=professores or [],
        turmas=turmas or [],
        alunos=alunos or [],
        responsaveis=responsaveis or []
    )

@app.route('/dashboard_professor')
def dashboard_professor():
    if 'usuario' not in session or session['tipo'] != 'professor':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    # Obter todas as turmas cadastradas
    cursor.execute("SELECT id, nome, turno FROM turmas")
    todas_turmas = cursor.fetchall()

    # Separar turmas por turno
    turmas_matutino = [turma for turma in todas_turmas if turma['turno'].lower() == 'matutino']
    turmas_vespertino = [turma for turma in todas_turmas if turma['turno'].lower() == 'vespertino']

    cursor.close()
    conn.close()

    return render_template(
        'dashboard_professor.html',
        turmas_matutino=turmas_matutino,
        turmas_vespertino=turmas_vespertino,
        usuario=session['usuario']
    )

# Cadastro de turma
@app.route('/cadastrar_turma', methods=['GET', 'POST'])
def cadastrar_turma():
    if 'usuario' not in session or session['tipo'] != 'professor':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        turno = request.form['turno']

        conn = conectar_bd()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO turmas (nome, turno) VALUES (?, ?)", (nome, turno))
            conn.commit()
            flash("Turma cadastrada com sucesso!")
        except sqlite3.IntegrityError:
            flash("Essa turma já existe.")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard_professor'))

    return render_template('cadastrar_turma.html')

@app.route('/login_responsavel', methods=['GET', 'POST'])
def login_responsavel():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']

        conn = conectar_bd()
        cursor = conn.cursor()

        cursor.execute("SELECT senha, aluno_id FROM responsaveis WHERE login = ?", (login,))
        responsavel = cursor.fetchone()
        cursor.close()
        conn.close()

        if responsavel and check_password_hash(responsavel['senha'], senha):
            session['responsavel'] = login
            session['aluno_id'] = responsavel['aluno_id']
            return redirect(url_for('area_responsavel'))

        flash("Login ou senha inválidos.")
        return redirect(url_for('login_responsavel'))

    return render_template('login_responsavel.html')

@app.route('/area_responsavel')
def area_responsavel():
    if 'responsavel' not in session:
        flash("Faça login para acessar.")
        return redirect(url_for('login_responsavel'))

    aluno_id = session.get('aluno_id')

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT alunos.nome AS aluno_nome, turmas.nome AS turma_nome, ocorrencias.data, ocorrencias.tipo_ocorrencia, 
               ocorrencias.motivo, ocorrencias.total_dias, ocorrencias.chamar_responsavel, 
               COALESCE(ocorrencias.data_reuniao, 'N/A') AS data_reuniao, 
               COALESCE(ocorrencias.hora_reuniao, 'N/A') AS hora_reuniao
        FROM alunos
        JOIN turmas ON alunos.turma_id = turmas.id
        LEFT JOIN ocorrencias ON alunos.id = ocorrencias.aluno_id
        WHERE alunos.id = ?
        ORDER BY ocorrencias.data DESC
    ''', (aluno_id,))
    ocorrencias = cursor.fetchall()
    cursor.close()
    conn.close()

    aluno_nome = ocorrencias[0]['aluno_nome'] if ocorrencias else "Aluno não encontrado"
    return render_template('area_responsavel.html', aluno_nome=aluno_nome, ocorrencias=ocorrencias)

@app.route('/cadastrar_responsavel', methods=['GET', 'POST'])
def cadastrar_responsavel():
    conn = conectar_bd()
    cursor = conn.cursor()

    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        aluno_id = request.form['aluno_id']
        senha_hash = generate_password_hash(senha)

        # Verifica se já há dois responsáveis cadastrados para o aluno
        cursor.execute("SELECT COUNT(*) FROM responsaveis WHERE aluno_id = ?", (aluno_id,))
        num_responsaveis = cursor.fetchone()[0]

        if num_responsaveis >= 2:
            flash("Este aluno já possui dois responsáveis cadastrados.")
            return redirect(url_for('cadastrar_responsavel'))

        try:
            cursor.execute("INSERT INTO responsaveis (login, senha, aluno_id) VALUES (?, ?, ?)",
                           (login, senha_hash, aluno_id))
            conn.commit()
            flash("Responsável cadastrado com sucesso!")
        except sqlite3.IntegrityError:
            flash("Login já está em uso. Escolha outro.")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('login_responsavel'))

    # Busca todas as turmas para exibir no formulário
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('cadastrar_responsavel.html', turmas=turmas)


@app.route('/redefinir_senha', methods=['GET', 'POST'])
def redefinir_senha():
    if request.method == 'POST':
        login = request.form.get('login')
        nova_senha = request.form.get('nova_senha')

        if not login or not nova_senha:
            flash("Por favor, preencha todos os campos.")
            return redirect(url_for('redefinir_senha'))

        conn = conectar_bd()
        cursor = conn.cursor()

        try:
            # Verificar se o login existe
            cursor.execute("SELECT id FROM responsaveis WHERE login = ?", (login,))
            responsavel = cursor.fetchone()

            if not responsavel:
                flash("Login não encontrado.")
                return redirect(url_for('redefinir_senha'))

            # Atualizar a senha
            nova_senha_hash = generate_password_hash(nova_senha)
            cursor.execute("UPDATE responsaveis SET senha = ? WHERE login = ?", (nova_senha_hash, login))
            conn.commit()
            flash("Senha redefinida com sucesso!")
        except sqlite3.Error as e:
            flash(f"Erro ao redefinir senha: {e}")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('login_responsavel'))

    return render_template('redefinir_senha.html')


# Rota para visualizar os responsáveis por turma
@app.route('/visualizar_responsaveis', methods=['GET'])
def visualizar_responsaveis():
    conn = conectar_bd()
    cursor = conn.cursor()

    # Buscar todas as turmas para exibir no filtro
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    # Verificar se uma turma foi selecionada
    turma_id = request.args.get('turma_id')

    responsaveis = []
    if turma_id:
        # Buscar os responsáveis e seus alunos para a turma selecionada
        cursor.execute('''
            SELECT responsaveis.login, alunos.nome, responsaveis.id
            FROM responsaveis
            JOIN alunos ON responsaveis.aluno_id = alunos.id
            WHERE alunos.turma_id = ?
        ''', (turma_id,))
        responsaveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('visualizar_responsaveis.html', turmas=turmas, responsaveis=responsaveis)

# Rota para excluir responsável
@app.route('/excluir_responsavel', methods=['POST'])
def excluir_responsavel():
    responsavel_id = request.form['responsavel_id']

    conn = conectar_bd()
    cursor = conn.cursor()

    # Excluir o responsável pelo ID
    cursor.execute("DELETE FROM responsaveis WHERE id = ?", (responsavel_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # Redirecionar de volta para a página de visualização de responsáveis
    return redirect(url_for('visualizar_responsaveis'))

# Cadastro de aluno em uma turma
@app.route('/cadastrar_aluno', methods=['GET', 'POST'])
def cadastrar_aluno():
    if 'usuario' not in session or session['tipo'] != 'professor':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, turno FROM turmas")
    turmas = cursor.fetchall()

    if request.method == 'POST':
        turma_id = request.form.get('turma_id')
        nomes = request.form.getlist('nomes[]')

        if not turma_id or not nomes:
            flash("Por favor, selecione uma turma e insira pelo menos um aluno.")
            return redirect(url_for('cadastrar_aluno'))

        try:
            for nome in nomes:
                cursor.execute("INSERT INTO alunos (nome, turma_id) VALUES (?, ?)", (nome, turma_id))
            conn.commit()
            flash(f"{len(nomes)} aluno(s) cadastrado(s) com sucesso!")
        except sqlite3.IntegrityError:
            flash("Erro ao cadastrar os alunos. Verifique os dados e tente novamente.")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard_professor'))

    cursor.close()
    conn.close()
    return render_template('cadastrar_aluno.html', turmas=turmas)


# Selecionar turma para excluir aluno
@app.route('/selecionar_turma', methods=['GET'])
def selecionar_turma():
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    turma_id = request.args.get('turma_id')
    if not turma_id:
        flash("Turma não selecionada.")
        return redirect(url_for('dashboard_moderador'))

    conn = conectar_bd()
    cursor = conn.cursor()

    # Obter alunos da turma selecionada
    cursor.execute('''
        SELECT alunos.id, alunos.nome
        FROM alunos
        WHERE alunos.turma_id = ?
    ''', (turma_id,))
    alunos_da_turma = cursor.fetchall()

    # Obter todas as turmas para exibição
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard_moderador.html',
        turmas=turmas,
        alunos_da_turma=alunos_da_turma
    )

# Excluir aluno
@app.route('/excluir_aluno/<int:aluno_id>', methods=['POST'])
def excluir_aluno(aluno_id):
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
        conn.commit()
        flash("Aluno excluído com sucesso.")
    except sqlite3.Error as e:
        flash(f"Erro ao excluir aluno: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('dashboard_moderador'))

# Excluir turma
@app.route('/excluir_turma/<int:turma_id>', methods=['POST'])
def excluir_turma(turma_id):
    if 'usuario' not in session or session['tipo'] != 'moderador':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        # Verifica se há alunos na turma antes de excluir
        cursor.execute("SELECT COUNT(*) AS total FROM alunos WHERE turma_id = ?", (turma_id,))
        total_alunos = cursor.fetchone()['total']

        if total_alunos > 0:
            flash("Não é possível excluir a turma. Existem alunos cadastrados nela.")
            return redirect(url_for('dashboard_moderador'))

        cursor.execute("DELETE FROM turmas WHERE id = ?", (turma_id,))
        conn.commit()
        flash("Turma excluída com sucesso.")
    except sqlite3.Error as e:
        flash(f"Erro ao excluir turma: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('dashboard_moderador'))

@app.route('/registrar_ocorrencia', methods=['GET', 'POST'])
def registrar_ocorrencia():
    if request.method == 'POST':
        turma_id = request.form['turma_id']
        aluno_id = request.form['aluno_id']
        data_ocorrencia = request.form['data_ocorrencia']
        tipo_ocorrencia = request.form['tipo_ocorrencia']
        motivo = request.form['motivo']
        professor = request.form['professor']
        chamar_responsavel = request.form.get('chamar_responsavel', 'nao')
        data_reuniao = request.form.get('data_reuniao')
        hora_reuniao = request.form.get('hora_reuniao')
        total_dias = request.form.get('total_dias', 0) if tipo_ocorrencia == 'SUSPENSAO' else 0

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ocorrencias (aluno_id, turma_id, data, tipo_ocorrencia, motivo, professor, 
                                     chamar_responsavel, data_reuniao, hora_reuniao, total_dias)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (aluno_id, turma_id, data_ocorrencia, tipo_ocorrencia, motivo, professor,
              chamar_responsavel, data_reuniao, hora_reuniao, total_dias))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('dashboard_professor'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    cursor.execute("SELECT id, nome FROM alunos")
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('registro_ocorrencia.html', turmas=turmas, alunos=alunos)

@app.route('/visualizar_ocorrencias', methods=['GET'])
def visualizar_ocorrencias():
    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    turma_id = request.args.get('turma_id')
    ocorrencias = []

    if turma_id:
        cursor.execute('''
            SELECT ocorrencias.id, alunos.nome AS aluno_nome, turmas.nome AS turma_nome, ocorrencias.data, 
                   ocorrencias.tipo_ocorrencia, ocorrencias.motivo, ocorrencias.total_dias, 
                   ocorrencias.chamar_responsavel, COALESCE(ocorrencias.data_reuniao, 'N/A') AS data_reuniao, 
                   COALESCE(ocorrencias.hora_reuniao, 'N/A') AS hora_reuniao
            FROM ocorrencias
            JOIN alunos ON ocorrencias.aluno_id = alunos.id
            JOIN turmas ON alunos.turma_id = turmas.id
            WHERE turmas.id = ?
            ORDER BY ocorrencias.data DESC
        ''', (turma_id,))
        ocorrencias = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('visualizar_ocorrencias.html', ocorrencias=ocorrencias, turmas=turmas, turma_selecionada=turma_id)

@app.route('/ocorrencias/download_pdf/<int:turma_id>')
def download_ocorrencias_pdf(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()

    # Buscar ocorrências da turma
    cursor.execute('''
        SELECT alunos.nome AS aluno_nome, turmas.nome AS turma_nome, ocorrencias.data, 
               ocorrencias.tipo_ocorrencia, ocorrencias.motivo, ocorrencias.total_dias, 
               ocorrencias.chamar_responsavel, COALESCE(ocorrencias.data_reuniao, 'N/A') AS data_reuniao, 
               COALESCE(ocorrencias.hora_reuniao, 'N/A') AS hora_reuniao
        FROM ocorrencias
        JOIN alunos ON ocorrencias.aluno_id = alunos.id
        JOIN turmas ON ocorrencias.turma_id = turmas.id
        WHERE turmas.id = ?
        ORDER BY ocorrencias.data DESC
    ''', (turma_id,))
    ocorrencias = cursor.fetchall()
    cursor.close()
    conn.close()

    # Criar buffer de memória para o PDF
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf.setTitle("Relatório de Ocorrências")

    # Adicionar cabeçalho
    pdf.drawString(100, 750, f"Relatório de Ocorrências - Turma {ocorrencias[0]['turma_nome'] if ocorrencias else 'N/A'}")

    # Adicionar conteúdo
    y_position = 700
    for ocorrencia in ocorrencias:
        pdf.drawString(50, y_position, f"Aluno: {ocorrencia['aluno_nome']} | Data: {ocorrencia['data']} | Tipo: {ocorrencia['tipo_ocorrencia']}")
        pdf.drawString(50, y_position - 15, f"Motivo: {ocorrencia['motivo']} | Reunião: {ocorrencia['data_reuniao']} às {ocorrencia['hora_reuniao']}")
        y_position -= 40

        # Criar uma nova página, se necessário
        if y_position < 100:
            pdf.showPage()
            y_position = 750

    pdf.save()

    # Retornar o PDF gerado
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"ocorrencias_turma_{turma_id}.pdf"
    )


@app.route('/excluir_ocorrencia', methods=['GET', 'POST'])
def excluir_ocorrencia():
    conn = conectar_bd()
    cursor = conn.cursor()

    if request.method == 'POST':
        ocorrencia_id = request.form['ocorrencia_id']
        cursor.execute("DELETE FROM ocorrencias WHERE id = ?", (ocorrencia_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('excluir_ocorrencia'))

    cursor.execute('''
        SELECT ocorrencias.id, alunos.nome, turmas.nome, ocorrencias.data, ocorrencias.tipo_ocorrencia, ocorrencias.motivo
        FROM ocorrencias
        JOIN alunos ON ocorrencias.aluno_id = alunos.id
        JOIN turmas ON ocorrencias.turma_id = turmas.id
        ORDER BY ocorrencias.data DESC
    ''')
    ocorrencias = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('excluir_ocorrencia.html', ocorrencias=ocorrencias)

@app.route('/registrar_recado', methods=['GET', 'POST'])
def registrar_recado():
    if 'usuario' not in session or session['tipo'] != 'professor':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        conteudo = request.form.get('conteudo')

        if not conteudo:
            flash("Por favor, preencha o recado.")
            return redirect(url_for('registrar_recado'))

        conn = conectar_bd()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO recados (conteudo) VALUES (?)", (conteudo,))
            conn.commit()
            flash("Recado registrado com sucesso!")
        except sqlite3.Error as e:
            flash(f"Erro ao registrar recado: {e}")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard_professor'))

    return render_template('registrar_recado.html')

@app.route('/visualizar_recados', methods=['GET', 'POST'])
def visualizar_recados():
    if 'usuario' not in session or session['tipo'] != 'professor':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    # Buscar todos os recados cadastrados
    cursor.execute("SELECT id, conteudo, data_criacao FROM recados ORDER BY data_criacao DESC")
    recados = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('visualizar_recados.html', recados=recados)


@app.route('/excluir_recado/<int:recado_id>', methods=['POST'])
def excluir_recado(recado_id):
    if 'usuario' not in session or session['tipo'] != 'professor':
        flash("Acesso não autorizado.")
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        # Excluir o recado pelo ID
        cursor.execute("DELETE FROM recados WHERE id = ?", (recado_id,))
        conn.commit()
        flash("Recado excluído com sucesso!")
    except sqlite3.Error as e:
        flash(f"Erro ao excluir recado: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('visualizar_recados'))

@app.route('/verificar_senha', methods=['POST'])
def verificar_senha():
    senha_digitada = request.form.get('senha')
    destino = request.form.get('destino')  # Pode ser 'registrar', 'visualizar', ou 'gerar_pdf'

    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        # Verifica a senha do moderador
        cursor.execute("SELECT senha FROM moderadores WHERE login = 'SAVIO'")
        moderador = cursor.fetchone()

        if moderador and check_password_hash(moderador['senha'], senha_digitada):
            if destino == 'registrar':
                return redirect(url_for('registrar_recado'))
            elif destino == 'visualizar':
                return redirect(url_for('visualizar_recados'))
            elif destino == 'gerar_pdf':
                return redirect(url_for('gerar_pdf'))
            else:
                flash("Destino inválido.")
                return redirect(url_for('dashboard_professor'))
        else:
            flash("Senha do moderador incorreta.")
            return redirect(url_for('dashboard_professor'))
    except Exception as e:
        flash(f"Erro ao verificar senha: {e}")
        return redirect(url_for('dashboard_professor'))
    finally:
        cursor.close()
        conn.close()

#gerar pdf
@app.route('/gerar_pdf', methods=['GET', 'POST'])
def gerar_pdf():
    if request.method == 'POST':
        tabelas_selecionadas = request.form.getlist('tabelas')  # Obtém as tabelas selecionadas
        if not tabelas_selecionadas:
            flash("Por favor, selecione pelo menos uma tabela para gerar o PDF.")
            return redirect(url_for('gerar_pdf'))

        conn = conectar_bd()
        cursor = conn.cursor()
        dados = {}

        # Mapear consultas personalizadas com JOIN para exibir dados legíveis
        consultas = {
            "professores": """
                SELECT p.id, p.login, p.status, t.nome AS turma 
                FROM professores p
                LEFT JOIN turmas t ON p.turma_id = t.id
            """,
            "turmas": "SELECT id, nome, turno FROM turmas",
            "alunos": """
                SELECT a.id, a.nome, t.nome AS turma, a.saldo
                FROM alunos a
                LEFT JOIN turmas t ON a.turma_id = t.id
                ORDER BY t.nome, a.nome
            """,

            "ocorrencias": """
                SELECT o.id, a.nome AS aluno, t.nome AS turma, o.data, o.tipo_ocorrencia, o.motivo, o.professor,
                       COALESCE(o.data_reuniao, 'N/A') AS data_reuniao, COALESCE(o.hora_reuniao, 'N/A') AS hora_reuniao
                FROM ocorrencias o
                LEFT JOIN alunos a ON o.aluno_id = a.id
                LEFT JOIN turmas t ON o.turma_id = t.id
            """,
            "responsaveis": """
                SELECT r.id, r.login, a.nome AS aluno 
                FROM responsaveis r
                LEFT JOIN alunos a ON r.aluno_id = a.id
            """
        }

        try:
            for tabela in tabelas_selecionadas:
                if tabela in consultas:
                    cursor.execute(consultas[tabela])
                    registros = cursor.fetchall()
                    colunas = [desc[0] for desc in cursor.description]
                    dados[tabela] = {"registros": registros, "colunas": colunas}

            # Calcular pontuação total por turma
            cursor.execute("""
                SELECT t.nome AS turma, SUM(lg.pontos) AS total_pontos
                FROM lancamentos_gincana lg
                JOIN turmas t ON lg.turma_id = t.id
                GROUP BY t.id, t.nome
                ORDER BY total_pontos DESC
            """)
            pontuacoes_gincana = cursor.fetchall()
        except sqlite3.Error as e:
            flash(f"Erro ao acessar os dados: {e}")
            return redirect(url_for('dashboard_professor'))
        finally:
            cursor.close()
            conn.close()

        # Gerar o PDF formatado
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Adicionar título geral
        elements.append(Paragraph("Relatório Personalizado", styles["Title"]))
        elements.append(Spacer(1, 12))

        for tabela, info in dados.items():
            # Adicionar título da tabela
            elements.append(Paragraph(f"Tabela: {tabela.capitalize()}", styles["Heading2"]))
            elements.append(Spacer(1, 6))

            # Preparar dados da tabela
            colunas = info["colunas"]
            registros = info["registros"]
            data = [colunas] + [list(row) for row in registros]

            # Criar tabela estilizada
            tabela_pdf = Table(data)
            tabela_pdf.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(tabela_pdf)
            elements.append(Spacer(1, 24))

        # Retornar o PDF
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="relatorio_personalizado.pdf"
        )

    # Renderizar o formulário inicial
    return render_template('gerar_pdf.html')


# Visualizar alunos de uma turma
@app.route('/visualizar_turmas/<int:turma_id>')
def visualizar_alunos_turma(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,))
    turma = cursor.fetchone()

    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('visualizar_alunos_turma.html', turma=turma, alunos=alunos)

# Obter alunos de uma turma em formato JSON
@app.route('/get_alunos/<int:turma_id>')
def get_alunos(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{'id': aluno['id'], 'nome': aluno['nome']} for aluno in alunos])

# Rota para obter alunos de uma turma em formato JSON
@app.route('/get_alunos_turma/<int:turma_id>')
def get_alunos_turma(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{'id': aluno['id'], 'nome': aluno['nome']} for aluno in alunos])

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Você saiu com sucesso.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)