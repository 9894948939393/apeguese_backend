import os
import json
import ast
import logging
import random
from flask import Flask, request, jsonify, session,send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from db import get_db_connection, criar_tabelas
from security import encriptar_dados, decriptar_dados
from werkzeug.utils import secure_filename
import jwt
from flask_session import Session
from functools import wraps
import datetime
load_dotenv()

def criar_app():
    app = Flask(__name__)
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    session_dir = os.path.join(os.getcwd(), 'flask_session')
    os.makedirs(session_dir, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=session_dir,
        SESSION_PERMANENT=True,
        SESSION_USE_SIGNER=True,
        SESSION_COOKIE_SAMESITE='None',  
        SESSION_COOKIE_SECURE=True,    
        SESSION_COOKIE_HTTPONLY=True,
        UPLOAD_FOLDER=os.path.join(os.getcwd(), 'uploads')
    )

    Session(app)

    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_limpo))
            return nome_limpo
        return ''

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


    def carregar_usuarios():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios")
        dados = cursor.fetchall()
        cursor.close()
        conn.close()
        return dados
    
    def generate_token(email):
        payload = {
            'email': email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    # Decorador para proteger rotas
    def token_required(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                token = request.headers.get('Authorization')

                if not token:
                    return jsonify({'message': 'Token ausente'}), 401

                try:
                    token = token.replace("Bearer ", "")
                    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                    request.decoded_token = decoded
                except jwt.ExpiredSignatureError:
                    return jsonify({'message': 'Token expirado'}), 401
                except jwt.InvalidTokenError:
                    return jsonify({'message': 'Token inválido'}), 401

                return f(*args, **kwargs)

            return decorated

    logging.basicConfig(level=logging.INFO)

    origins = list(filter(None, [
        os.getenv("FRONTEND_URL"),
        os.getenv("FRONTEND_URL2"),
        os.getenv("FRONTEND_URL3")
        ]))
    CORS(app, origins=origins, supports_credentials=True)

    logging.basicConfig(
        level=logging.DEBUG, 
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    @app.route("/init-db")
    def init_db():
        try:
            criar_tabelas()
            return jsonify({"status": "Tabelas criadas com sucesso"})
        except Exception as e:
            return jsonify({"erro": str(e)}), 500



    def gerar_codigo():
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
            codigo = gerar_codigo()

            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO usuarios (usuario, email, senha, telefone, cpf, data_nascimento, codigo_usuario, historico, favoritos, carrinho, cep, numero, rua, bairro, cidade, estado, complemento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (usuario, email, senha_encriptada, telefone, cpf_encriptado, data_nascimento, codigo, "[]", "[]", "[]", "", "", "", "", "", "", "",))
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
            return jsonify({"erro": "Email e senha são obrigatórios"})

        if email == os.getenv("ADMIN_EMAIL") and senha == os.getenv("ADMIN_PASSWORD"):
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

        token = generate_token(email)
        return jsonify({"message": "Login realizado com sucesso", "usuario": usuario['usuario'], "codigo": usuario['email'],"sessao": token})


    @app.route('/perfil', methods=['GET'])
    @token_required
    def listar_perfil():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (request.decoded_token.get('email'),))
        perfil = cursor.fetchone()
        cursor.close()
        conn.close()
        app.logger.info(perfil)
        return jsonify({"perfil": perfil})


    @app.route('/produtos', methods=['GET'])
    def listar_produtos():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos")
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()
        app.logger.info(produtos)
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
    @token_required
    def adicionar_carrinho():
        produto = request.form.get("produto")
        usuario = request.decoded_token.get('email')

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
    @token_required
    def mostrar_carrinho():
        usuario = request.decoded_token.get('email')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario,))
        resultado = cursor.fetchone()
        carrinho = json.loads(resultado['carrinho']) if resultado and resultado['carrinho'] else []

        produtos_carrinho = []
        valor_total = 0

        for pid in carrinho:
            cursor.execute("SELECT * FROM produtos WHERE codigo = %s", (pid,))
            produto = cursor.fetchone()
            if produto:
                produtos_carrinho.append(produto)
                valor_total += float(produto['valor'])

        session['carrinho'] = carrinho
        session['valor'] = valor_total
        cursor.close()
        conn.close()
        return jsonify({"produto": produtos_carrinho, "valor": valor_total})


    @app.route('/deletar_carrinho', methods=['POST'])
    @token_required
    def deletar_carrinho():
        produto_id = request.form.get("produto")  
        usuario = request.decoded_token.get('email')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario,))
        resultado = cursor.fetchone()
        carrinho = json.loads(resultado['carrinho']) if resultado and resultado['carrinho'] else []


        carrinho = [item for item in carrinho if item != produto_id]
        produto_carrinho = []
        valor_total = 0
        for pid in carrinho:
            cursor.execute("SELECT preco FROM produtos WHERE codigo = %s", (pid,))
            prod = cursor.fetchone()
            if prod:
                valor_total += float(prod['preco'])
                produto_carrinho.append(prod)
        cursor.execute("UPDATE usuarios SET carrinho = %s WHERE email = %s", (json.dumps(carrinho), usuario))
        conn.commit()
        session['valor'] = valor_total
        session["carrinho"] = produto_carrinho
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Produto excluído do carrinho com sucesso",
            "valor": valor_total,
            "produto":produto_carrinho
        })

    @app.route('/ir_pedido', methods=['POST'])
    @token_required
    def ir_pedido():
        import ast
        usuario_email = request.decoded_token.get('email')

        if not usuario_email:
            return jsonify({"message": "Usuário não logado"})

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario_email,))
        carrinho_row = cursor.fetchone()

        if not carrinho_row or not carrinho_row["carrinho"]:
            cursor.close()
            conn.close()
            return jsonify({"message": "Carrinho vazio"})

        try:
            carrinho_produtos_codigos = json.loads(carrinho_row["carrinho"])
        except json.JSONDecodeError:
            cursor.close()
            conn.close()
            return jsonify({"message": "Erro ao interpretar o carrinho"})

        produtos_carrinho_detalhes = []
        valor_total = 0
        for codigo_produto in carrinho_produtos_codigos:
            cursor.execute("SELECT valor FROM produtos WHERE codigo = %s", (codigo_produto,))
            produto_detalhe = cursor.fetchone()
            if produto_detalhe:
                produtos_carrinho_detalhes.append(produto_detalhe)
                valor_total += float(produto_detalhe['valor'])

        session['valor'] = valor_total 
        valor = valor_total

        cursor.execute("""
            SELECT cep, telefone, rua, numero
            FROM usuarios
            WHERE email = %s
        """, (usuario_email,))
        usuario_dados = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario_dados:
            return jsonify({"message": "Usuário não encontrado"})


        cep = usuario_dados['cep']
        telefone = usuario_dados['telefone']
        rua = usuario_dados['rua']
        numero = usuario_dados['numero']

        if not cep or not rua or not numero:
            return jsonify({"message": "Endereço não encontrado"})

        frete = calcular_frete_sudeste_com_margem(cep, len(carrinho_produtos_codigos) // 2)
        logging.info(f"Frete:{frete}")
        total = float(valor) + float(frete)

        return jsonify({
            "message": "Sucesso!",
            "frete": frete,
            "total": total,
            "endereco": {
                "rua": rua,
                "numero": numero
            },
            "telefone": telefone
        })

    @app.route('/finalizar_pedido', methods=['POST'])
    @token_required
    def finalizar_pedido():
        comprador_email = request.decoded_token.get('email')

        conn = get_db_connection()
        cursor = conn.cursor()


        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (comprador_email,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            return jsonify({"message": "Usuário não encontrado"})

        carrinho_str = user['carrinho']

        if not carrinho_str:
            cursor.close()
            conn.close()
            return jsonify({"message": "Carrinho vazio. Não é possível finalizar o pedido."})

        try:
            carrinho_produtos_codigos = json.loads(carrinho_str)
        except json.JSONDecodeError:
            cursor.close()
            conn.close()
            return jsonify({"message": "Erro ao interpretar o carrinho do usuário."})

        valor_total_produtos = 0
        for codigo_produto in carrinho_produtos_codigos:
            cursor.execute("SELECT valor FROM produtos WHERE codigo = %s", (codigo_produto,))
            produto_detalhe = cursor.fetchone()
            if produto_detalhe:
                valor_total_produtos += float(produto_detalhe['valor'])

        endereco = {
            "cep": user['cep'],
            "numero": user['numero'],
            "rua": user['rua'],
            "bairro": user['bairro'],
            "cidade": user['cidade'],
            "estado": user['estado'],
            "complemento": user['complemento'],
        }

        frete = calcular_frete_sudeste_com_margem(user['cep'], len(carrinho_produtos_codigos) // 2)
        if frete is None:
            cursor.close()
            conn.close()
            return jsonify({"message": "CEP fora da região de entrega"})

        total_final_pedido = valor_total_produtos + frete
        status = "Aguardando verificação do pagamento"

        cursor.execute('''
            INSERT INTO pedidos (usuario, comprador, produtos, valor, endereco, telefone, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (user['usuario'], comprador_email, json.dumps(carrinho_produtos_codigos), total_final_pedido, json.dumps(endereco), user['telefone'], status))

        cursor.execute("UPDATE usuarios SET historico = %s, carrinho = %s WHERE email = %s",
                    (json.dumps(carrinho_produtos_codigos), json.dumps([]), comprador_email)) 

        conn.commit()
        cursor.close()
        conn.close()
        session.pop('carrinho', None) 
        session.pop('valor', None)
        return jsonify({"message": "Pedido realizado com sucesso!"})


    @app.route('/mostrar_pedidos', methods=['GET'])
    @token_required
    def mostrar_pedidos():
        usuario_email = request.decoded_token.get('email')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM pedidos WHERE usuario = %s", (usuario_email,))
        pedidos = cursor.fetchall()

        cursor.execute("SELECT codigo, nome, valor, imagem FROM produtos")
        todos_produtos_dict = {p['codigo']: p for p in cursor.fetchall()}

        pedidos_com_detalhes_produtos = []
        valor_total_todos_pedidos = 0 

        for pedido in pedidos:
            carrinho_codigos = json.loads(pedido['produtos']) if pedido['produtos'] else []
            produtos_do_pedido = []
            valor_total_deste_pedido = 0

            for codigo_produto in carrinho_codigos:
                if codigo_produto in todos_produtos_dict:
                    produto_detalhe = todos_produtos_dict[codigo_produto]
                    produtos_do_pedido.append(produto_detalhe)
                    valor_total_deste_pedido += float(produto_detalhe['valor']) 

            pedido['produtos_detalhes'] = produtos_do_pedido
            pedido['valor_produtos_total'] = valor_total_deste_pedido 

            pedidos_com_detalhes_produtos.append(pedido)
            valor_total_todos_pedidos += float(pedido['valor'])

        cursor.close()
        conn.close()
        return jsonify({"pedidos": pedidos_com_detalhes_produtos, "valor_total_pedidos": valor_total_todos_pedidos})

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
    @app.route('/novo_produto', methods=['POST'])
    def adicionar_produto():
        nome = request.form.get('nome')
        marca = request.form.get("marca")
        cor = request.form.get("cor")
        numeracao = request.form.get("numeracao")
        genero = request.form.get("genero")
        descricao = request.form.get("descricao")
        valor = request.form.get("valor")
        imagem = request.files.get("imagem")

        codigo = gerar_codigo_produto()
        nome_imagem = salvar_imagem(imagem, codigo, nome)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO produtos (nome, marca, cor, numeracao, genero, valor, descricao, imagem, codigo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nome, marca, cor, numeracao, genero, valor, descricao, nome_imagem, codigo))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Produto adicionado com sucesso!"})
        except:
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

    @app.route("/alterar_endereco", methods=["POST"])
    @token_required
    def atualizar_endereco():
        dados = request.form
        cep = dados.get("cep")
        numero = dados.get("numero")
        rua = dados.get("rua")
        bairro = dados.get("bairro")
        cidade = dados.get("cidade")
        estado = dados.get("estado")
        complemento = dados.get("complemento")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE usuarios SET cep = %s, numero = %s , rua = %s, bairro = %s, cidade = %s, estado = %s, complemento = %s WHERE email = %s",
                (cep,numero,rua,bairro,cidade,estado,complemento,request.decoded_token.get('email'), ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao inserir usuário: {e}")
            return jsonify({"erro": "Erro ao atualizar endereço"})
        finally:
            cursor.close()
            conn.close()

        return jsonify({"message": "Sucesso!"})
    @app.after_request
    def aplicar_cors_em_todas_respostas(response):
        origin = request.headers.get("Origin")
        if origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS,PUT,DELETE"
        return response
        
    return app
