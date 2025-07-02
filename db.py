import os
import mysql.connector # Alterado para mysql.connector
# from psycopg2.extras import RealDictCursor # Removido
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn = mysql.connector.connect( # Alterado para mysql.connector.connect
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"), # Alterado de 'dbname' para 'database'
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 3306), # Porta padrão do MySQL é 3306
        dictionary=True # Retorna resultados como dicionários, similar a RealDictCursor
    )
    return conn

def criar_tabelas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY, -- Alterado de SERIAL PRIMARY KEY
            usuario VARCHAR(255) NOT NULL, -- Uso de VARCHAR para textos curtos
            email VARCHAR(255) UNIQUE NOT NULL, -- Uso de VARCHAR
            senha VARCHAR(255) NOT NULL, -- Uso de VARCHAR
            telefone VARCHAR(20), -- Uso de VARCHAR
            cpf VARCHAR(14), -- Uso de VARCHAR
            data_nascimento DATE,
            codigo_usuario VARCHAR(50) UNIQUE NOT NULL, -- Uso de VARCHAR
            historico JSON, -- MySQL 5.7+ suporta tipo JSON
            favoritos JSON, -- MySQL 5.7+ suporta tipo JSON
            carrinho JSON, -- MySQL 5.7+ suporta tipo JSON
            cep VARCHAR(10), -- Uso de VARCHAR
            numero VARCHAR(10), -- Uso de VARCHAR
            rua VARCHAR(255), -- Uso de VARCHAR
            bairro VARCHAR(255), -- Uso de VARCHAR
            cidade VARCHAR(255), -- Uso de VARCHAR
            estado VARCHAR(50), -- Uso de VARCHAR
            complemento VARCHAR(255) -- Uso de VARCHAR
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INT AUTO_INCREMENT PRIMARY KEY, -- Alterado de SERIAL PRIMARY KEY
            nome VARCHAR(255) NOT NULL, -- Uso de VARCHAR
            marca VARCHAR(255), -- Uso de VARCHAR
            valor DECIMAL(10, 2), -- NUMERIC é compatível, mas DECIMAL é comum em MySQL
            codigo VARCHAR(50) UNIQUE, -- Uso de VARCHAR
            descricao TEXT,
            cor JSON, -- MySQL 5.7+ suporta tipo JSON
            genero VARCHAR(50), -- Uso de VARCHAR
            numeracao JSON, -- MySQL 5.7+ suporta tipo JSON
            imagem VARCHAR(255) -- Uso de VARCHAR
        );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pedidos (
        id INT AUTO_INCREMENT PRIMARY KEY, -- Alterado de SERIAL PRIMARY KEY
        usuario VARCHAR(255), -- Uso de VARCHAR
        comprador VARCHAR(255), -- Uso de VARCHAR
        produtos JSON, -- MySQL 5.7+ suporta tipo JSON
        valor VARCHAR(255), -- Mantido como TEXT/VARCHAR, pois pode ser um JSON string
        status VARCHAR(50), -- Uso de VARCHAR
        telefone VARCHAR(20), -- Uso de VARCHAR
        endereco JSON -- MySQL 5.7+ suporta tipo JSON
    );
''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS estoque (
        id INT AUTO_INCREMENT PRIMARY KEY, -- Alterado de SERIAL PRIMARY KEY
        produto VARCHAR(255), -- Uso de VARCHAR para o nome do produto
        tamanho VARCHAR(20), -- Uso de VARCHAR
        cor VARCHAR(50), -- Uso de VARCHAR
        quantidade INT -- INTEGER é compatível, mas INT é comum
    );
''')
    conn.commit()
    cursor.close()
    conn.close()