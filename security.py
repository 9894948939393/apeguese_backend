import os
from cryptography.fernet import Fernet

KEY_PATH = "chave_protecao.key"


key = os.getenv("FERNET_KEY").encode()
cipher_suite = Fernet(key)

def encriptar_dados(dado: str) -> str:
    dado_bytes = dado.encode()
    dado_encriptado = cipher_suite.encrypt(dado_bytes)
    return dado_encriptado.decode()

def decriptar_dados(dado_encriptado: str) -> str:
    dado_bytes = dado_encriptado.encode()
    dado_decriptado = cipher_suite.decrypt(dado_bytes)
    return dado_decriptado.decode()