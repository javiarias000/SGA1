# Usa la imagen oficial de Python 3.12 como base
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /usr/src/app

# Establece variables de entorno para evitar mensajes de pip y forzar la salida a la terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala dependencias del sistema necesarias
# En este caso, solo necesitas libpq-dev para el conector de PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo requirements.txt (o los listados en el prompt) y los instala
# Reemplaza 'requirements.txt' con el nombre de tu archivo si es diferente
# NOTA: Los requerimientos proporcionados serán instalados
COPY requirements.txt .
RUN pip install --upgrade pip
# Instala las dependencias. Utiliza 'psycopg2-binary' para la conexión a PostgreSQL.
# Se asume que el listado de requerimientos proporcionado está en 'requirements.txt'
RUN pip install -r requirements.txt psycopg2-binary

# Copia toda la aplicación al directorio de trabajo
# ¡Asegúrate de que tu 'requirements.txt' esté en la misma carpeta que este Dockerfile!
COPY . .

# Expone el puerto que usará Django
EXPOSE 8000

# Comando para ejecutar la aplicación. 
# En un entorno de producción, usualmente usarías un servidor WSGI como Gunicorn.
# Para desarrollo simple:
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
