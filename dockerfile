FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl build-essential libssl-dev pkg-config

# Instalar rustup e Rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

# Configurar toolchain padrão stable do Rust
RUN /root/.cargo/bin/rustup default stable

ENV PATH="/root/.cargo/bin:${PATH}"

RUN python -m venv /venv
ENV PATH="/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
