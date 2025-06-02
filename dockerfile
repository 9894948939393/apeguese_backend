# Usa imagem base com Python
FROM python:3.10-slim

# Instala dependências do sistema + Rust
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libssl-dev \
    libffi-dev \
    pkg-config \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y \
    && . "$HOME/.cargo/env"

# Adiciona Rust ao PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Cria diretório da aplicação
WORKDIR /app

# Copia os arquivos da aplicação
COPY . .

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expõe a porta
EXPOSE 5000

# Comando para rodar o app (ajuste conforme necessário)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
