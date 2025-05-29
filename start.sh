#!/bin/bash
set -e

# Ejecutar migraciones
echo "Aplicando migraciones..."
python manage.py migrate

# Recopilar archivos estáticos
echo "Recopilando archivos estáticos..."
python manage.py collectstatic --no-input --clear

# Iniciar el servidor de desarrollo
echo "Iniciando servidor de desarrollo..."
python manage.py runserver 0.0.0.0:8000
