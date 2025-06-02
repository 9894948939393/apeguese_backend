from flask import Flask, request, session, jsonify
from flask_cors import CORS
import os
import json
import random
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from db import get_db_connection

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], supports_credentials=True)

app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'public', 'images'))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# ---------------------------------------------------------------------
# Criptografia
try:
    with open("chave_protecao.key", "rb") as f:
        key = f.read()
    print("Chave de proteção carregada do arquivo.")
except FileNotFoundError:
    key = Fernet.generate_key()
    with open("chave_protecao.key", "wb") as f:
        f.write(key)
    print("Nova chave gerada e salva.")
cipher_suite = Fernet(key)

def encriptar_dados(dado):
    return cipher_suite.encrypt(str(dado).encode()).decode()

def decriptar_dados(dado):
    return cipher_suite.decrypt(str(dado).encode()).decode()

# ---------------------------------------------------------------------
def gerar_codigo_produto():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo FROM produtos")
    codigos_existentes = [str(row['codigo']) for row in cursor.fetchall()]
    while True:
        codigo = str(random.randint(100000000, 999999999))
        if codigo not in codigos_existentes:
            cursor.close()
            conn.close()
            return codigo

def salvar_imagem(imagem, codigo, nome):
    if imagem:
        nome_limpo = secure_filename(f"{nome.replace(' ', '')}_{codigo}.jpg")
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_limpo)
        imagem.save(caminho)
        return nome_limpo
    return ''

def adicionar_item(nome, marca, cor, numeracao, genero, valor, descricao, imagem):
    codigo = gerar_codigo_produto()
    nome_imagem = salvar_imagem(imagem, codigo, nome)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO produtos (nome, marca, cor, numeracao, genero, valor, descricao, imagem, codigo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (nome, marca, cor, numeracao, genero, valor, descricao, nome_imagem, codigo))
    conn.commit()
    cursor.close()
    conn.close()
    return True

def carregar_produtos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return dados

def carregar_pedidos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return dados

# ---------------------------------------------------------------------
@app.route('/api/hello')
def hello():
    return jsonify({"message": "Olá do Flask!"})

@app.route('/api/data', methods=['POST'])
def receive_data():
    return jsonify({"received": request.get_json()})

@app.route('/produtos', methods=['GET'])
def listar_produtos():
    produtos = carregar_produtos()
    return jsonify({"produtos": produtos})

@app.route('/pedidos', methods=['GET'])
def listar_pedidos():
    pedidos = carregar_pedidos()
    return jsonify({"pedidos": pedidos})

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    nome = request.form.get('nome')
    marca = request.form.get("marca")
    cor = request.form.get("cor")
    numeracao = request.form.get("numeracao")
    genero = request.form.get("genero")
    valor = request.form.get("valor")
    descricao = request.form.get("descricao")
    imagem = request.files.get("imagem")

    sucesso = adicionar_item(nome, marca, cor, numeracao, genero, valor, descricao, imagem)
    if sucesso:
        return jsonify({"message": "Produto adicionado com sucesso!"})
    return jsonify({"message": "Erro ao adicionar produto."}), 500

@app.route('/atualizar_preco', methods=['POST'])
def atualizar_preco():
    produto = request.form.get("produto")
    preco = request.form.get("preco")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE produtos SET valor = %s WHERE nome = %s", (preco, produto))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Valor atualizado com sucesso!"})

@app.route('/deletar_produto', methods=['POST'])
def deletar_produto():
    produto = request.form.get("produto")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos WHERE nome = %s", (produto,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Produto deletado com sucesso"})

# ---------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
