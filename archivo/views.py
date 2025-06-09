import os
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.conf import settings

# Obtiene la ruta absoluta del directorio donde se encuentra este script
dir_path = os.path.dirname(os.path.realpath(__file__))

# Construye la ruta al archivo urls.json
urls_file_path = os.path.join(dir_path, "urls.json")

with open(urls_file_path) as f:
    urls = json.load(f)


@login_required
def archivo(request):
    # Crear un diccionario con los nombres de los archivos para la plantilla
    context = {
        'documentos': [
            {'id': '1', 'nombre': '1 Información General', 'archivo': '1 INFORMACION GENERAL.docx'},
            {'id': '2', 'nombre': '2 Estructura Organizacional', 'archivo': '2 ESTRUCTURA ORGANIZACIONAL.docx'},
            {'id': '3', 'nombre': '3 Leyes y Regulaciones', 'archivo': '3 LEYES Y REGULACIONES.docx'},
            {'id': '4', 'nombre': '4 Planificación de Operaciones', 'archivo': '4 PLANIFICACIÓN DE OPERACIONES.docx'},
            {'id': '5', 'nombre': '5 Información Administrativa', 'archivo': '5 INFORMACIÓN ADMINISTRATIVA.docx'},
            {'id': '6', 'nombre': '6 Información Contable, Presupuestaria y Financiera', 'archivo': '6 INFORMACIÓN CONTABLE, PRESUPUESTARIA Y FINANCIERA.docx'},
        ]
    }
    return render(request, "archivo.html", context)


@login_required
def descargar_archivo(request, nombre_archivo):
    # Construir la ruta completa al archivo
    ruta_archivo = os.path.join(
        settings.BASE_DIR, 
        'static', 
        'template-modulo-archivo-permanente',
        'MODULO ARCHIVO PERMANENTE',
        nombre_archivo
    )
    
    # Verificar si el archivo existe
    if os.path.exists(ruta_archivo):
        # Abrir el archivo en modo binario y devolverlo como respuesta
        archivo = open(ruta_archivo, 'rb')
        response = FileResponse(archivo)
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        return response
    else:
        # Si el archivo no existe, devolver un error 404
        raise Http404("El archivo solicitado no existe.")
