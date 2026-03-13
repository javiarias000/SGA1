# Usa Python 3.12-slim
FROM python:3.12-slim

# Directorio de trabajo
WORKDIR /usr/src/app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ACTUALIZACIÓN CRÍTICA: Instalamos setuptools para evitar el error de 'pkg_resources'
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copiamos requerimientos
COPY requirements.txt .

# INSTALACIÓN: Instalamos setuptools nuevamente por si acaso y luego el resto
RUN pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir -r requirements.txt psycopg2-binary

# Copia el resto del proyecto
COPY . .

# Puerto de Django
EXPOSE 8000

# Comando de arranque
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]# Usa la imagen oficial de Python 3.12 como base
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /usr/src/app

# Variables de entorno corregidas (formato KEY=VALUE)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependencias del sistema necesarias
# Añadimos build-essential para asegurar que pip pueda compilar cualquier librería
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Actualiza herramientas de instalación
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copia solo los requerimientos primero (optimiza el tiempo de construcción)
COPY requirements.txt .

# Instala las dependencias. 
# Nota: He unido psycopg2-binary aquí para evitar conflictos de instalación doble.
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

# Copia toda la aplicación
COPY . .

# Expone el puerto que usará Django
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
