FROM python:3.10-slim


# METADATOS
LABEL maintainer="ayelenleiva.f@gmail.com"
LABEL description="FIAQ - Modelo de IA capaz de predecir la capacidad antioxidante de moléculas"
LABEL version="1.0"

# VARIABLES DE ENTORNO
# PYTHONDONTWRITEBYTECODE → no genera .pyc; ahorra espacio
# PYTHONUNBUFFERED        → logs en tiempo real en el servidor
# PORT=7860               → puerto que usa Hugging Face Spaces
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# DEPENDENCIAS DEL SISTEMA
# RDKit necesita estas librerías de sistema para funcionar.
# --no-install-recommends → imagen más liviana
# rm -rf /var/lib/apt/lists/* → limpia caché de apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# DIRECTORIO DE TRABAJO
# Todo el código de la app vive en /app dentro del contenedor.
WORKDIR /app

# DEPENDENCIAS PYTHON
# Se copian e instalan ANTES que el código fuente.
# Así Docker cachea esta capa y no reinstala todo si solo cambia el código
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# CÓDIGO FUENTE
# Se copia todo el proyecto. El .dockerignore excluye
# lo que no debe entrar (data/, scripts/, notebooks, etc.)
COPY . .

# USUARIO NO-ROOT; seguridad
# Hugging Face Spaces requiere UID 1000.
# Nunca correr como root dentro del contenedor.
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# PUERTO
# Solo documentación — informa qué puerto expone el contenedor.
EXPOSE 7860

# COMANDO DE INICIO
# Gunicorn: servidor WSGI de producción (reemplaza flask run).
#   -w 1            → 1 worker (el modelo ocupa RAM, más workers
#                     significaría más copias del modelo en memoria)
#   -b 0.0.0.0:7860 → escucha en todas las interfaces, puerto 7860
#   --timeout 120   → 120 seg de timeout (RDKit puede tardar)
#   main:app        → archivo main.py, objeto Flask llamado "app"
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:7860", "--timeout", "120", "main:app"]