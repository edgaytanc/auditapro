import os
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Obtiene la ruta absoluta del directorio donde se encuentra este script
dir_path = os.path.dirname(os.path.realpath(__file__))

# Construye la ruta al archivo urls.json
urls_file_path = os.path.join(dir_path, "urls.json")

with open(urls_file_path) as f:
    urls = json.load(f)


@login_required
def archivo(request):
    context = urls["archivo"]
    return render(request, "archivo.html", context)
