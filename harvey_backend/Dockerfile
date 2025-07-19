# Harvey Backend - Dockerfile para Produção
# Multi-stage build para otimizar tamanho e segurança

# Estágio 1: Build e instalação de dependências
FROM python:3.11-slim as builder

# Metadados da imagem
LABEL maintainer="Harvey Backend Team"
LABEL version="1.0"
LABEL description="Harvey Backend - AI-Powered Legal Document Generation"

# Variáveis de ambiente para o build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala dependências do sistema necessárias para o build
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc \
    g++ \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY requirements.txt requirements-dev.txt ./

# Instala dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Estágio 2: Imagem final otimizada
FROM python:3.11-slim as production

# Variáveis de ambiente para produção
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV APP_ENV=production

# Instala apenas dependências runtime essenciais
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Cria usuário não-root para segurança
RUN groupadd -r harvey && useradd -r -g harvey harvey

# Cria diretórios necessários
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R harvey:harvey /app

# Copia dependências Python do estágio builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Define diretório de trabalho
WORKDIR /app

# Copia código da aplicação
COPY --chown=harvey:harvey ./app ./app
COPY --chown=harvey:harvey ./alembic.ini ./
COPY --chown=harvey:harvey ./scripts ./scripts

# Cria arquivo de versão
RUN echo "$(date +%Y%m%d_%H%M%S)" > /app/version.txt

# Muda para usuário não-root
USER harvey

# Expõe porta da aplicação
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão para iniciar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Estágio 3: Imagem para desenvolvimento (opcional)
FROM production as development

# Volta para root para instalar dependências de desenvolvimento
USER root

# Instala dependências de desenvolvimento
RUN pip install --no-cache-dir -r requirements-dev.txt

# Instala ferramentas de desenvolvimento
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Volta para usuário harvey
USER harvey

# Comando para desenvolvimento (com reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
