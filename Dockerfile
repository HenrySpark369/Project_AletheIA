# Imagen base ligera de Python 3.8
FROM python:3.10-slim

# Variables de entorno para mejorar comportamiento de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo
WORKDIR /app

# Copia todos los archivos del proyecto al contenedor
COPY . .

# Instala Git y compiladores necesarios para ciertas librerías (como backports.zoneinfo)
RUN apt-get update && \
    apt-get install -y git build-essential gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Instala las dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Precarga del modelo para evitar timeout de descarga en runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Comando por defecto para ejecutar el servidor web
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()", "--timeout", "300"]