import os
import json
import ast
import random
import logging
from flask import Flask, request, jsonify, session,send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from db import get_db_connection, criar_tabelas
from security import encriptar_dados, decriptar_dados
from werkzeug.utils import secure_filename
load_dotenv()

def criar_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
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
            send_from_directory(app.config['UPLOAD_FOLDER'], nome_limpo)
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
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    app.secret_key = os.getenv("SECRET_KEY")
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    origins = [
    os.getenv("FRONTEND_URL"),
    os.getenv("FRONTEND_URL2"),
    os.getenv("FRONTEND_URL3")
]
    origins = [url for url in origins if url]
    logging.basicConfig(level=logging.INFO)
    CORS(app, origins=origins, supports_credentials=True, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    @app.route("/init-db")
    def init_db():
        try:
            criar_tabelas()
            return jsonify({"status": "Tabelas criadas com sucesso"})
        except Exception as e:
            return jsonify({"erro": str(e)}), 500



    def gerar_email():
        return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))




    @app.route("/cadastro", methods=["POST"])
    def cadastro():
        dados = request.form
        usuario = dados.get("nome")
        email = dados.get("email")
        senha = dados.get("senha")
        telefone = dados.get("telefone")
        cpf = dados.get("cpf")
        data_nascimento = dados.get("dataNascimento")
        confirmarSenha = dados.get("confirmarSenha")
        if not (usuario and email and senha):
            return jsonify({"erro": "Campos obrigatórios não preenchidos."}), 400
        if confirmarSenha == senha:
            senha_encriptada = encriptar_dados(senha)
            cpf_encriptado = encriptar_dados(cpf) if cpf else None
            email = gerar_email()

            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO usuarios (usuario, email, senha, telefone, cpf, data_nascimento, email, historico, favoritos, carrinho, cep, numero, rua, bairro, cidade, estado, complemento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (usuario, email, senha_encriptada, telefone, cpf_encriptado, data_nascimento, email, "[]", "[]", "[]", "", "", "", "", "", "", "",))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logging.error(f"Erro ao inserir usuário: {e}")
                return jsonify({"erro": "Erro ao cadastrar usuário. Email pode estar duplicado."})
            finally:
                cursor.close()
                conn.close()

            return jsonify({"message": "Usuário cadastrado com sucesso", "codigo": email})
        else:
            return jsonify({"message": "As senhas não correspondem"})
    @app.route("/login", methods=["POST"])
    def login():
        dados = request.form
        email = dados.get("email")
        senha = dados.get("senha")

        if not (email and senha):
            return jsonify({"erro": "Email e senha são obrigatórios"}),400

        if email == "clubraro65@gmail.com" and senha == "clubraro335555777777":
            return jsonify({"message": "admin", "usuario": "admin", "codigo": "admin", "role": "admin"})

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        if not usuario:
            return jsonify({"message": "Usuário ou senha incorretos, tente novamente"})

        senha_decriptada = decriptar_dados(usuario['senha'])
        if senha != senha_decriptada:
            return jsonify({"message": "Usuário ou senha incorretos, tente novamente"})

        session['usuario'] = email
        return jsonify({"message": "Login realizado com sucesso", "usuario": usuario['usuario'], "codigo": usuario['email']})


    @app.route('/session', methods=['GET'])
    def listar_sessao():
        sessao = session.get("usuario")
        print(sessao)
        return jsonify({"sessao": sessao})


    @app.route('/perfil', methods=['GET'])
    def listar_perfil():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (session.get("usuario"),))
        perfil = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"perfil": perfil})


    @app.route('/produtos', methods=['GET'])
    def listar_produtos():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos")
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"produtos": produtos})


    @app.route('/pedidos', methods=['GET'])
    def listar_pedidos():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pedidos")
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"pedidos": produtos})


    @app.route('/selecionar_produto', methods=['POST'])
    def selecionar_produto():
        escolha = request.form.get("escolha")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos WHERE nome = %s", (escolha,))
        produto = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"produto": produto})


    @app.route('/adicionar_carrinho', methods=['POST'])
    def adicionar_carrinho():
        produto = request.form.get("produto")
        usuario = session.get("usuario")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario,))
        resultado = cursor.fetchone()
        carrinho = json.loads(resultado['carrinho']) if resultado else []

        carrinho.append(produto)

        cursor.execute("UPDATE usuarios SET carrinho = %s WHERE email = %s", (json.dumps(carrinho), usuario))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Produto adicionado ao carrinho com sucesso!"})


    @app.route('/mostrar_carrinho', methods=['GET'])
    def mostrar_carrinho():
        usuario = session.get('usuario')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario,))
        resultado = cursor.fetchone()
        carrinho = json.loads(resultado['carrinho']) if resultado and resultado['carrinho'] else []

        produtos_carrinho = []
        valor_total = 0

        for pid in carrinho:
            cursor.execute("SELECT * FROM produtos WHERE id = %s", (pid,))
            produto = cursor.fetchone()
            if produto:
                produtos_carrinho.append(produto)
                valor_total += float(produto['preco'])

        session['carrinho'] = carrinho
        session['valor'] = valor_total
        cursor.close()
        conn.close()
        return jsonify({"produto": produtos_carrinho, "valor": valor_total})


    @app.route('/deletar_carrinho', methods=['POST'])
    def deletar_carrinho():
        produto = request.form.get("produto")
        usuario = session.get('usuario')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario,))
        resultado = cursor.fetchone()
        carrinho = json.loads(resultado['carrinho']) if resultado and resultado['carrinho'] else []

        carrinho = [item for item in carrinho if item != produto]

        cursor.execute("UPDATE usuarios SET carrinho = %s WHERE email = %s", (json.dumps(carrinho), usuario))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Produto excluído do carrinho com sucesso"})


    @app.route('/finalizar_pedido', methods=['POST'])
    def finalizar_pedido():
        valor = session.get('valor')
        carrinho = session.get('carrinho')
        comprador = request.form.get("comprador")
        usuario = session.get("usuario")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (usuario,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"message": "Usuário não encontrado"})

        endereco = {
            "cep": user['cep'],
            "numero": user['numero'],
            "rua": user['rua'],
            "bairro": user['bairro'],
            "cidade": user['cidade'],
            "estado": user['estado'],
            "complemento": user['complemento'],
        }

        frete = calcular_frete_sudeste_com_margem(user['cep'], len(carrinho) // 2)
        if frete is None:
            return jsonify({"message": "CEP fora da região de entrega"})

        total = float(valor) + frete
        status = "Aguardando verificação do pagamento"

        cursor.execute('''
            INSERT INTO pedidos (usuario, comprador, produtos, valor, endereco, telefone, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (usuario, comprador, json.dumps(carrinho), total, json.dumps(endereco), user['telefone'], status))

        cursor.execute("UPDATE usuarios SET historico = %s, carrinho = %s WHERE email = %s",
                    (json.dumps(carrinho), json.dumps([]), usuario))

        conn.commit()
        cursor.close()
        conn.close()
        session.pop('carrinho', None)
        session.pop('valor', None)
        return jsonify({"message": "Pedido realizado com sucesso!"})


    @app.route('/mostrar_pedidos', methods=['GET'])
    def mostrar_pedidos():
        usuario = session.get('usuario')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM pedidos WHERE email = %s", (usuario,))
        pedidos = cursor.fetchall()
        produtos_carrinho = []

        cursor.execute("SELECT * FROM produtos")
        todos_produtos = cursor.fetchall()

        for pedido in pedidos:
            carrinho = json.loads(pedido['produtos']) if pedido['produtos'] else []
            for produto in todos_produtos:
                if produto['id'] in carrinho:
                    produtos_carrinho.append(produto)

        valor = sum(float(p['valor']) for p in pedidos)
        cursor.close()
        conn.close()
        return jsonify({"produto": produtos_carrinho, "valor": valor})


    def calcular_frete_sudeste_com_margem(cep_destino, qtd_caixas):
        cep_origem = "31340520"

        def gerar_faixas_cep(inicio_str, fim_str):
            return [str(i).zfill(3) for i in range(int(inicio_str), int(fim_str) + 1)]

        sudeste_faixas = {
            "SP": gerar_faixas_cep("010", "199"),
            "RJ": gerar_faixas_cep("200", "289"),
            "MG": gerar_faixas_cep("300", "399"),
            "ES": gerar_faixas_cep("290", "299"),
        }

        precos_por_estado = {
            "SP": 22.00,
            "RJ": 20.00,
            "MG": 18.00,
            "ES": 25.00,
        }

        faixa_destino = str(cep_destino)[:3]
        estado_destino = next((estado for estado, faixas in sudeste_faixas.items() if faixa_destino in faixas), None)
        if not estado_destino:
            return None

        preco_base = precos_por_estado[estado_destino]
        preco_total = preco_base * max(1, qtd_caixas)
        margem = 0.30
        return round(preco_total * (1 + margem), 2)


    # ---------------------------------------------------------------------

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

    @app.route("/atualizar_endereco", methods=["POST"])
    def atualizar_endereco():
        dados = request.form
        cep = dados.get("cep")
        numero = dados.get("rua")
        rua = dados.get("numero")
        bairro = dados.get("bairro")
        cidade = dados.get("cidade")
        estado = dados.get("estado")
        complemento = dados.get("complemento")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE usuarios SET cep = %s, numero = %s , rua = %s, bairro = %s, cidade = %s, estado = %s, complemento = %s WHERE email = %s",
                (cep,numero,rua,bairro,cidade,estado,complemento, session.get("usuario")))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao inserir usuário: {e}")
            return jsonify({"erro": "Erro ao cadastrar usuário. Email pode estar duplicado."}),400
        finally:
            cursor.close()
            conn.close()

        return jsonify({"message": "Sucesso!"})
    @app.after_request
    def aplicar_cors_em_todas_respostas(response):
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS,PUT,DELETE")
        return response
    
    return app
