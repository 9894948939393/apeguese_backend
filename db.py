import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432),
        cursor_factory=RealDictCursor
    )
    return conn

def criar_tabelas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            telefone TEXT,
            cpf TEXT,
            data_nascimento DATE,
            codigo_usuario TEXT UNIQUE NOT NULL,
            historico TEXT,
            favoritos TEXT,
            carrinho TEXT,
            cep TEXT,
            numero TEXT,
            rua TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            complemento TEXT
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            marca TEXT,
            valor NUMERIC(10, 2),
            codigo TEXT UNIQUE,
            descricao TEXT,
            cor TEXT,
            genero TEXT,
            numeracao TEXT,
            imagem TEXT
        );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pedidos (
        id SERIAL PRIMARY KEY,
        usuario TEXT,
        comprador TEXT,
        produtos TEXT,
        valor TEXT,
        status TEXT, 
        telefone TEXT,
        endereco TEXT   
    );
''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS estoque (
        id SERIAL PRIMARY KEY,
        produto TEXT,
        tamanho TEXT,
        cor TEXT,
        quantidade TEXT
    );
''')
    conn.commit()
    cursor.close()
    conn.close()
