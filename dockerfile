FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl build-essential libssl-dev pkg-config

# Instala rustup (Rust toolchain installer)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

# Define variáveis de ambiente para rustup e cargo
ENV RUSTUP_HOME=/root/.rustup
ENV CARGO_HOME=/root/.cargo
ENV PATH="/root/.cargo/bin:${PATH}"

# Configura toolchain padrão stable
RUN rustup default stable

# Cria ambiente virtual
RUN python -m venv /venv
ENV PATH="/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
