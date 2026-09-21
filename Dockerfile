FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libgirepository1.0-dev \
    pkg-config \
    # Dependencias adicionales para pycairo y otras bibliotecas
    python3-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    # Paquetes específicos para PyGObject y pycairo
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias
COPY requirements.txt .
# Instalar todas las dependencias directamente
RUN pip install --no-cache-dir -r requirements.txt
# Instalar dependencias adicionales necesarias
RUN pip install --no-cache-dir python-docx openpyxl html5lib whitenoise
# Intentar instalar tinyhtml5 (puede no existir en PyPI)
RUN pip install --no-cache-dir tinycss2 cssselect2 cffi
# Solución alternativa para WeasyPrint
RUN pip uninstall -y weasyprint && pip install weasyprint==52.5
# Instalar Django debug toolbar para desarrollo
RUN pip install --no-cache-dir django-debug-toolbar

# Crear directorio de logs
RUN mkdir -p logs

# Crear directorio para la base de datos SQLite
RUN mkdir -p db
VOLUME /app/db

# Copiar el proyecto
COPY . /app/

# Puerto de exposición
EXPOSE 8000
