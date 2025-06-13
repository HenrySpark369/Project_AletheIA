FROM python:3.10-slim

# 1) Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# 2) Instala dependencias C y Python (capa cacheable)
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev git && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 3) Precarga el modelo
RUN python - << 'PYCODE'
from sentence_transformers import SentenceTransformer
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
PYCODE

# 4) Quita deps de compilación y limpia cache de apt
RUN apt-get purge -y --auto-remove build-essential gcc git && \
    rm -rf /var/lib/apt/lists/*

# 3) Copia resto del código
COPY . .

# 4) Expón y arranca en $PORT
EXPOSE $PORT
CMD ["sh", "-c", "gunicorn -w 4 -b 0.0.0.0:$PORT app:create_app() --timeout 300"]