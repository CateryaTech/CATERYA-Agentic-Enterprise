# CATERYA Agentic Enterprise — Dockerfile
# Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>
# Multi-stage build for minimal, secure image

FROM python:3.12-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy dependency files first (layer cache optimization)
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir \
    langchain>=0.3.0 \
    langchain-community>=0.3.0 \
    langchain-ollama>=0.2.0 \
    langgraph>=0.2.0 \
    streamlit>=1.40.0 \
    redis>=5.0.0 \
    psycopg2-binary>=2.9.9 \
    sqlalchemy>=2.0.0 \
    cryptography>=43.0.0 \
    web3>=7.0.0 \
    httpx>=0.27.0 \
    pydantic>=2.8.0 \
    python-dotenv>=1.0.0 \
    rich>=13.8.0 \
    argon2-cffi>=23.1.0 \
    chromadb>=0.5.0

# Copy source
COPY src/ ./src/
COPY data/ ./data/
COPY .env.example ./.env.example

# Create data directories
RUN mkdir -p /app/data /app/logs

# Non-root user for security
RUN useradd -m -u 1000 caterya && chown -R caterya:caterya /app
USER caterya

# Streamlit config
RUN mkdir -p ~/.streamlit
RUN echo '[server]\nheadless = true\naddress = "0.0.0.0"\nport = 8501\nenableCORS = false\nenableXsrfProtection = false\n[browser]\ngatherUsageStats = false\n' > ~/.streamlit/config.toml

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
