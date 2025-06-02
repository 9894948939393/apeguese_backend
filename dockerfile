# Imagem base Python oficial
FROM python:3.11-slim

# Atualiza e instala dependências essenciais para compilar Rust e pacotes Python
RUN apt-get update && apt-get install -y curl build-essential libssl-dev pkg-config

# Instala Rust via rustup (instala toolchain stable e configura PATH)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Cria e ativa ambiente virtual
RUN python -m venv /venv
ENV PATH="/venv/bin:${PATH}"

# Copia o requirements.txt e instala as dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia o código do projeto
COPY . .

# Expõe a porta padrão (ajuste se precisar)
EXPOSE 5000

# Comando para rodar sua aplicação Flask
CMD ["flask", "run", "--host=0.0.0.0"]
