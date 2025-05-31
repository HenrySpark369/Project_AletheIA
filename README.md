# 🧠 Project AletheIA

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/HenrySpark369/Project_AletheIA)

**Simulación social + OSINT + IA generativa**  
Plataforma modular para analizar comportamiento en redes, detectar clones digitales y generar contenido automatizado con agentes virtuales.

---

## 📌 Descripción General

**Project AletheIA** es un sistema basado en Flask que permite:

- Simular agentes sociales (con personalidades como trolls, usurpadores, normales y observadores).
- Generar publicaciones automáticamente usando IA (OpenAI API).
- Detectar posibles clones digitales (usuarios con datos similares en redes públicas).
- Analizar tendencias actuales (usando Pytrends).
- Visualizar resultados en un dashboard web intuitivo.

Este proyecto puede usarse para investigación en OSINT, análisis de redes, estudios de comportamiento social automatizado o simulación de campañas.

---

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/HenrySpark369/Project_AletheIA.git
cd Project_AletheIA
```

### 2. Crear y activar entorno virtual (opcional pero recomendado)

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar API Key de OpenAI

Crea un archivo `.env` o configura en `config.py` tu clave de OpenAI:

```bash
export OPENAI_API_KEY=tu_clave_aqui  # En Linux/macOS
set OPENAI_API_KEY=tu_clave_aqui     # En Windows
```

---

## 🔐 Seguridad y Configuración de Flask

Para que ciertas funcionalidades como `flash()` funcionen correctamente (por ejemplo, en el módulo de clones OSINT o formularios), **es obligatorio definir una `SECRET_KEY`**.

### ¿Qué es?

`SECRET_KEY` protege sesiones y operaciones internas como `flash()`, autenticación, tokens CSRF, etc.

### 🔧 Formas de generarla en Python

#### Para desarrollo:
```python
import os
SECRET_KEY = os.urandom(24)
```

#### Para producción:
```python
import secrets
SECRET_KEY = secrets.token_hex(32)
```

Puedes generar una y guardarla como variable de entorno:

#### En Linux/macOS:
```bash
export FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

#### En Windows (CMD):
```cmd
set FLASK_SECRET_KEY=tu_clave_segura_aqui
```

### 🧠 Configuración sugerida en `config.py`:
```python
import os
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
```

> ⚠️ Usa una clave aleatoria y única para cada entorno. Nunca compartas tu `SECRET_KEY` pública si vas a publicar el código.

---

## 🚀 Ejecución

Una vez configurado el entorno y la base de datos:

```bash
python app.py
```

Abre tu navegador en: [http://localhost:5000](http://localhost:5000)

---

## 🐳 Dockerización y Gunicorn

Este proyecto está preparado para ejecutarse en producción usando **Docker** con dos servicios independientes:

- `web`: ejecuta el servidor Flask con Gunicorn.
- `scheduler`: ejecuta el simulador de agentes periódicamente.

### 📦 Construcción y ejecución

```bash
docker compose build
docker compose up
```

El archivo `docker-compose.yml` gestiona ambos servicios. Asegúrate de tener Docker y Docker Compose instalados.

### 🔧 Ejecución manual con Gunicorn (sin Docker)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

Este comando lanza la app con 4 workers usando el factory method `create_app()`.

### 🧠 Scheduler independiente

Para ejecutar el simulador de agentes como un proceso separado:

```bash
python scheduler_runner.py
```

Asegúrate de definir esta variable de entorno antes de correrlo:

```bash
export ENABLE_SCHEDULER=true
```

Este proceso se puede mantener activo por separado o gestionarse como servicio externo (ej. PM2, systemd, etc.).

### 🧰 Comandos útiles con Docker

**Construir la imagen:**
```bash
docker compose build
```

**Iniciar los servicios (web + scheduler):**
```bash
docker compose up
```

**Iniciar en segundo plano (modo detached):**
```bash
docker compose up -d
```

**Detener todos los servicios:**
```bash
docker compose down
```

**Ver logs de todos los servicios:**
```bash
docker compose logs -f
```

**Ver logs de un servicio específico (ej. `scheduler`):**
```bash
docker compose logs -f scheduler
```

**Reconstruir imagen desde cero:**
```bash
docker compose build --no-cache
```

**Acceder al contenedor web (para debug):**
```bash
docker exec -it aegisnet_web /bin/bash
```

> 📝 Asegúrate de tener `Docker` y `docker compose` instalados antes de usar estos comandos.

## 📊 Funcionalidades Principales

| Módulo           | Descripción                                                                 |
|------------------|-----------------------------------------------------------------------------|
| 🧬 Simulador      | Crea agentes virtuales con distintos perfiles de personalidad.             |
| 🧠 Generador IA   | Produce publicaciones automáticas personalizadas con OpenAI.                |
| 🔍 OSINT Clones   | Busca posibles clones digitales en la web y mide su similitud textual.      |
| 🔥 Tendencias     | Obtiene trending topics por tipo de agente usando Google Trends (Pytrends).|
| 🖥️ Dashboard      | Visualiza publicaciones, clones detectados y muros de agentes.              |

---

## 🧪 Base de Datos

El sistema utiliza SQLite por defecto (`database.db`). Para reiniciar o inicializar la base de datos:

```bash
python utils/init_db.py
```

> Puedes migrar fácilmente a PostgreSQL modificando `config.py` y los modelos SQLAlchemy.

---

## 🛡️ Consideraciones Legales

- Este sistema realiza búsquedas públicas (OSINT). Úsalo con responsabilidad.
- Si manejas datos reales de personas, asegúrate de cumplir con la [LFPDPPP](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf) en México u otra legislación aplicable.

---

## 📂 Estructura del Proyecto

```
.
├── app.py               # Main Flask App
├── config.py            # Configuración del entorno
├── models/              # Modelos de datos (SQLAlchemy)
├── repositories/        # Acceso a datos
├── services/            # Lógica de negocio (IA, OSINT, simulación)
├── routes/              # Endpoints Flask
├── templates/           # HTMLs (Jinja2)
├── static/              # JS y CSS
├── utils/               # Herramientas auxiliares (sherlock, similitud, generación)
├── database.db          # Base de datos SQLite (default)
└── *.txt                # Datos de prueba o referencias para simulación
```

---

## ✨ Créditos

Desarrollado por **HenrySpark369**
Contribuciones, issues y mejoras son bienvenidas vía pull request.
