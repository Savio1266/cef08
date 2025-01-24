import sqlite3
from app import conectar_bd  # Importa a função de conexão ao banco de app.py


# Testar conexão com o banco de dados
def testar_conexao():
    try:
        conn = conectar_bd()
        print("Conexão estabelecida com sucesso!")
        conn.close()
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")


# Testar estrutura da tabela `estudantes`
def testar_estrutura_estudantes():
    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(estudantes)")
        colunas = cursor.fetchall()
        print("Estrutura da tabela `estudantes`:")
        for coluna in colunas:
            print(f"Coluna: {coluna[1]}, Tipo: {coluna[2]}, Not Null: {coluna[3]}")
    except sqlite3.Error as e:
        print(f"Erro ao consultar estrutura da tabela: {e}")
    finally:
        cursor.close()
        conn.close()


# Testar inserção na tabela `estudantes`
def testar_insercao_estudante(nome, aluno_id):
    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO estudantes (nome, aluno_id)
            VALUES (?, ?)
        ''', (nome, aluno_id))
        conn.commit()
        print(f"Estudante `{nome}` registrado com sucesso!")
    except sqlite3.IntegrityError:
        print(f"Erro: O estudante `{nome}` ou o aluno_id `{aluno_id}` já existe.")
    except sqlite3.Error as e:
        print(f"Erro ao registrar estudante: {e}")
    finally:
        cursor.close()
        conn.close()


# Testar consulta de estudantes
def testar_consulta_estudantes():
    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM estudantes")
        estudantes = cursor.fetchall()
        print("Estudantes registrados:")
        for estudante in estudantes:
            print(dict(estudante))
    except sqlite3.Error as e:
        print(f"Erro ao consultar estudantes: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=== Testando Conexão ===")
    testar_conexao()

    print("\n=== Testando Estrutura da Tabela `estudantes` ===")
    testar_estrutura_estudantes()

    print("\n=== Testando Inserção de Estudante ===")
    testar_insercao_estudante("Estudante Teste", 1)  # Substitua `1` pelo ID de um aluno válido

    print("\n=== Testando Consulta de Estudantes ===")
    testar_consulta_estudantes()
