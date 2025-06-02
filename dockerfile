# Imagem base oficial do Python
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema (libpq para PostgreSQL + limpeza)
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia arquivos do projeto
COPY . .

# Instala dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Define variável de ambiente para produção
ENV FLASK_ENV=production

# Expõe a porta usada pelo Flask
EXPOSE 5000

# Comando de execução
CMD ["python", "wsgi.py"]
