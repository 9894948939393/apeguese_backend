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
from decimal import Decimal
# [cite_start]import psycopg2 # REMOVER [cite: 1]
# [cite_start]from psycopg2.extras import RealDictCursor # REMOVER (se estiver importando separadamente) [cite: 1]

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

    def verificar_estoque(cor, tamanho, produto):
        try:
            _conn = get_db_connection()
            print(f"conn: {_conn}")
            if _conn is None:
                return False
            # [cite_start]Não é mais necessário especificar cursor_factory aqui, pois a conexão já retorna dicionários [cite: 1]
            _cursor = _conn.cursor()
            close_resources = True
            _cursor.execute("""
                SELECT quantidade FROM estoque
                WHERE produto = %s AND cor = %s AND tamanho = %s
            """, (produto, cor, tamanho,))
            row = _cursor.fetchone()
            print(f"row: {row}")
            if row and row['quantidade'] > 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"Erro ao verificar estoque: {e}")
            return False
        finally:
            if close_resources:
                if _cursor:
                    _cursor.close()
                if _conn:
                    _conn.close()

    def generate_token(email):
        payload = {
            'email': email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

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
    def optional_token(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            request.decoded_token = None
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                    request.decoded_token = decoded_token
                except jwt.ExpiredSignatureError:
                    pass
                except jwt.InvalidTokenError:
                    pass
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

    @app.route('/token', methods=['GET'])
    @optional_token
    def listar_sessao():
        email = request.decoded_token.get('email') if request.decoded_token else None
        if email:
            return jsonify({"message": "Sucesso","mail": email})
        else:
            return jsonify({"message": ""})


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
        produto_codigo = request.form.get("produto")
        produto_nome = request.form.get("produto_nome")
        cor = request.form.get("cor")
        tamanho = request.form.get("tamanho")
        usuario_email = request.decoded_token.get('email')
        print(f"Produto: {produto_codigo},Produto nome{produto_nome} Cor: {cor}, Tamanho: {tamanho}, Usuário: {usuario_email}")
        conn = get_db_connection()
        if conn is None:
            return jsonify({"message": "Erro de conexão com o banco de dados."})

        try:
            with conn:
                # [cite_start]Não é mais necessário especificar cursor_factory aqui [cite: 1]
                with conn.cursor() as cursor:
                    if not verificar_estoque(cor, tamanho, produto_nome):
                        conn.rollback()
                        return jsonify({"message": "Ah, esse produto na numeração e cor que você escolheu está em falta no estoque!"})
                    cursor.execute("""
                        UPDATE estoque
                        SET quantidade = quantidade - 1
                        WHERE produto = %s AND cor = %s AND tamanho = %s AND quantidade > 0
                        RETURNING quantidade;
                    """, (produto_nome, cor, tamanho,))

                    updated_row = cursor.fetchone()
                    if not updated_row:
                        conn.rollback()
                        return jsonify({"message": "Falha ao atualizar estoque, tente novamente."})

                    cursor.execute("SELECT carrinho FROM usuarios WHERE email = %s", (usuario_email,))
                    resultado = cursor.fetchone()

                    carrinho = json.loads(resultado['carrinho']) if resultado and resultado['carrinho'] else []

                    novo_item = {
                        "produto": produto_codigo,
                        "cor": cor,
                        "tamanho": tamanho
                    }
                    carrinho.append(novo_item)

                    cursor.execute("UPDATE usuarios SET carrinho = %s WHERE email = %s", (json.dumps(carrinho), usuario_email))

                    conn.commit()
                    return jsonify({"message": "Produto adicionado ao carrinho com sucesso!"})

        except json.JSONDecodeError:
            conn.rollback()
            return jsonify({"message": "Erro ao processar dados do carrinho do usuário."}), 500
        except Exception as e:
            conn.rollback()
            print(f"Erro em adicionar_carrinho: {e}")
            return jsonify({"message": "Erro interno do servidor ao adicionar ao carrinho."}), 500
        finally:
            if conn:
                conn.close()



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

        for item in carrinho:
            pid = item.get("produto")
            cursor.execute("SELECT * FROM produtos WHERE codigo = %s", (pid,))
            produto = cursor.fetchone()
            if produto:
                produto_info = dict(produto)
                produto_info["cor"] = item.get("cor")
                produto_info["tamanho"] = item.get("tamanho")
                produtos_carrinho.append(produto_info)
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


        carrinho = [
        item for item in carrinho
        if not (item.get("produto") == produto_id )
    ]
        produto_carrinho = []
        valor_total = 0
        for item in carrinho:
            pid = item.get("produto")
            cursor.execute("SELECT * FROM produtos WHERE codigo = %s", (pid,))
            produto = cursor.fetchone()
            if produto:
                produto_info = dict(produto)
                produto_info["cor"] = item.get("cor")
                produto_info["tamanho"] = item.get("tamanho")
                produto_carrinho.append(produto_info)
                valor_total += float(produto['valor'])
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
        for item in carrinho_produtos_codigos:
            pid = item.get("produto")
            cursor.execute("SELECT * FROM produtos WHERE codigo = %s", (pid,))
            produto = cursor.fetchone()
            if produto:
                produto_info = dict(produto)
                produto_info["cor"] = item.get("cor")
                produto_info["tamanho"] = item.get("tamanho")
                produtos_carrinho_detalhes.append(produto_info)
                valor_total += float(produto['valor'])


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
            "endereco": f"{rua},{numero}",
            "telefone": telefone
        })

    @app.route('/finalizar_pedido', methods=['POST'])
    @token_required
    def finalizar_pedido():
        dados = request.form
        comprador= dados.get("comprador")
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
        for item in carrinho_produtos_codigos:
            pid = item.get("produto")
            cursor.execute("SELECT valor FROM produtos WHERE codigo = %s", (pid,))
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
        ''', (comprador_email, comprador, json.dumps(carrinho_produtos_codigos), total_final_pedido, json.dumps(endereco), user['telefone'], status,))

        cursor.execute("UPDATE usuarios SET historico = %s, carrinho = %s WHERE email = %s",
                    (json.dumps(carrinho_produtos_codigos), json.dumps([]), comprador_email,))

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
        try:
            conn = get_db_connection()
            # [cite_start]Não é mais necessário especificar cursor_factory aqui [cite: 1]
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM pedidos WHERE usuario = %s", (usuario_email,))
            pedidos = cursor.fetchall()
            app.logger.info(f"Pedidos:{pedidos}")
            codigos_produtos = []
            for pedido in pedidos:
                try:
                    carrinho = json.loads(pedido.get('produtos') or '[]')
                    status = pedido.get('status')
                    app.logger.info(f"Carrinho{carrinho}")
                    for c in carrinho:
                        if isinstance(c, dict) and 'produto' in c:
                            codigos_produtos.append(str(c['produto']))
                except Exception as e:
                    app.logger.warning(f"Erro ao interpretar carrinho: {e}")
                    continue

            produtos_detalhes = {}
            if codigos_produtos:
                placeholders = ','.join(['%s'] * len(codigos_produtos))
                query = f"SELECT codigo, nome, valor, imagem FROM produtos WHERE codigo IN ({placeholders})"
                cursor.execute(query, tuple(codigos_produtos))
                produtos_detalhes = {p['codigo']: p for p in cursor.fetchall()}
                app.logger.info(f"Produtos detalhes:{produtos_detalhes}")

            valor_total_geral = Decimal('0.00')
            for pedido in pedidos:
                try:
                    carrinho = json.loads(pedido.get('produtos') or '[]')
                except json.JSONDecodeError as e:

                    carrinho = []
                except Exception as e:
                    carrinho = []

                produtos_do_pedido = []
                valor_pedido = Decimal('0.00')

                for item_carrinho in carrinho:
                    if isinstance(item_carrinho, dict) and 'produto' in item_carrinho:
                        codigo_produto = str(item_carrinho['produto'])
                        produto = produtos_detalhes.get(codigo_produto)
                        if produto:
                            valor_item = Decimal(str(produto.get('valor', '0.00')))
                            valor_pedido += valor_item
                            produtos_do_pedido.append({
                                'codigo': produto['codigo'],
                                'nome': produto['nome'],
                                'valor': str(valor_item),
                                'status': status,
                                'imagem': produto['imagem']
                            })
                            app.logger.info(f"Produtos do pedido:{produtos_do_pedido}")

            pedido['produtos_detalhes'] = produtos_do_pedido
            pedido['valor_produtos_total_recalculado'] = str(valor_pedido)

            valor_pedido_original = Decimal(str(pedido.get('valor', '0.00')))
            valor_total_geral += valor_pedido_original

            pedido['valor'] = str(pedido.get('valor', '0.00'))
            valor_total_geral += Decimal(pedido['valor'])
            app.logger.info(f"Pedidos:{pedidos}")
            return jsonify({
                "message": "Sucesso",
                "pedidos": pedidos,
                "valor_total_todos_pedidos": str(valor_total_geral)
            }), 200

        except Exception as e:
            print(f"Erro ao mostrar pedidos: {e}")
            return jsonify({"message": "Erro interno do servidor", "error": str(e)}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

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
            "MG": 14.00,
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
        cor_offwhite = request.form.get("off-white")
        cor_preta = request.form.get("preta")
        cor_xadrez = request.form.get("xadrez")
        cor_listrada = request.form.get("listrada")
        cor_camel = request.form.get("camel")
        cor_estampa = request.form.get("estampa")
        cor_outra1 = request.form.get("outra1")
        cor_outra2 = request.form.get("outra2")
        tam_36 = request.form.get("36")
        tam_38 = request.form.get("38")
        tam_40 = request.form.get("40")
        tam_42 = request.form.get("42")
        genero = request.form.get("genero")
        descricao = request.form.get("descricao")
        valor = request.form.get("valor")
        imagem = request.files.get("imagem")

        cor = []
        if cor_offwhite: cor.append("off-white")
        if cor_preta: cor.append("preta")
        if cor_xadrez: cor.append("xadrez")
        if cor_listrada: cor.append("listrada")
        if cor_camel: cor.append("camel")
        if cor_estampa: cor.append("estampa")
        if cor_outra1: cor.append(cor_outra1)
        if cor_outra2: cor.append(cor_outra2)

        numeracao = []
        if tam_36: numeracao.append("36")
        if tam_38: numeracao.append("38")
        if tam_40: numeracao.append("40")
        if tam_42: numeracao.append("42")

        codigo = gerar_codigo_produto()
        nome_imagem = salvar_imagem(imagem, codigo, nome)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO produtos (nome, marca, cor, numeracao, genero, valor, descricao, imagem, codigo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nome, marca, json.dumps(cor), json.dumps(numeracao), genero, valor, descricao, nome_imagem, codigo))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Produto adicionado com sucesso!"})
        except Exception as e: # Adicionado tratamento de erro para depuração
            logging.error(f"Erro ao adicionar produto: {e}")
            return jsonify({"message": f"Erro ao adicionar produto: {e}"}), 500 # Retornar erro detalhado

    @app.route('/novo_estoque', methods=['POST'])
    def adicionar_estoque():
        produto = request.form.get('produto')
        cor = request.form.get("cor")
        numeracao = request.form.get("numeracao")
        quantidade = request.form.get("quantidade")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO estoque (produto,quantidade, cor, tamanho)
                VALUES (%s, %s, %s, %s)
            ''', (produto,quantidade,cor, numeracao,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Estoque criado com sucesso!"})
        except Exception as e: # Adicionado tratamento de erro para depuração
            logging.error(f"Erro ao criar estoque: {e}")
            return jsonify({"message": f"Erro ao criar estoque: {e}"}), 500

    @app.route('/atualizar_preco', methods=['POST'])
    def atualizar_preco():
        produto = request.form.get("produto")
        preco = request.form.get("preco")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE produtos SET valor = %s WHERE nome = %s", (preco, produto,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Valor atualizado com sucesso!"})

    @app.route('/atualizar_estoque', methods=['POST'])
    def atualizar_estoque():
        produto = request.form.get("produto")
        quantidade = request.form.get("quantidade")
        cor = request.form.get("cor")
        tamanho = request.form.get("tamanho")
        conn = get_db_connection()
        cursor = conn.cursor()
        [cite_start]cursor.execute("UPDATE estoque SET quantidade = %s WHERE produto = %s AND cor=%s AND tamanho=%s", (quantidade, produto,cor,tamanho,)) # Corrigido operador AND [cite: 1]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Estoque atualizado com sucesso!"})

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

    @app.route('/atualizar_status', methods=['POST'])
    def atualizar_status():
        status = request.form.get("status")
        produto = request.form.get("produto")
        usuario = request.form.get("usuario")
        conn = get_db_connection()
        cursor = conn.cursor()
        [cite_start]cursor.execute("UPDATE pedidos SET status = %s WHERE usuario = %s AND produtos = %s ", (status,usuario ,produto,)) # Corrigido operador AND [cite: 1]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Valor atualizado com sucesso!"})

    @app.route("/alterar_endereco", methods=["POST"])
    @token_required
    def atualizar_endereco():
        dados = request.form
        cep = dados.get("cep")
        print(f"Cep: {cep}")
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