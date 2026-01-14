FROM python:3.11-slim

# Instalar FFmpeg y dependencias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias Python
RUN pip install --no-cache-dir \
    flask \
    requests \
    gunicorn

# Copiar aplicación
COPY app.py .

# Crear directorio temporal
RUN mkdir -p /tmp/ffmpeg-service

# Puerto
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Ejecutar con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "--keep-alive", "5", "app:app"]
