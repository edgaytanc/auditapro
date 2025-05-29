import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from auditoria.imports.estados_financieros_importer import EstadosFinancierosImporter
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def importar_cuentas_contables(request, audit_id):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('archivo_excel')

        if not uploaded_file:
            return JsonResponse({"success": False, "message": "No se ha subido ningún archivo."}, status=400)

        # Utilizamos el nuevo importador unificado pasando directamente el objeto de archivo
        importer = EstadosFinancierosImporter(uploaded_file, audit_id)
        
        if importer.validate_file():
            success, message = importer.process_file()
            return JsonResponse({"success": success, "message": message}, status=200 if success else 500)
        else:
            return JsonResponse({
                "success": False, 
                "message": "El archivo no contiene hojas válidas de estados financieros."
            }, status=400)

    return render(request, "auditoria/importar_cuentas.html")