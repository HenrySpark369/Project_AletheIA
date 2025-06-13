FROM python:3.10-slim

# 1) Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# 2) Instala deps C/Python, pip y requirements
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev git && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    # 3) Precarga el modelo
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')" && \
    # 4) Limpia deps de compilación
    apt-get purge -y --auto-remove build-essential gcc git && \
    rm -rf /var/lib/apt/lists/*

# 5) Copia el resto y expone puerto
COPY . .
EXPOSE $PORT
CMD ["sh","-c","gunicorn -w 4 -b 0.0.0.0:$PORT app:create_app() --timeout 300"]