import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required

from audits.models import Audit  # 👈 IMPORTANTE: traemos Audit

from auditoria.imports.estados_financieros_importer import (
    EstadosFinancierosImporter,
    RevisoriaEstadosFinancierosImporter,  # 👈 tu nuevo importador para revisoria
)


@login_required
def importar_cuentas_contables(request, audit_id):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('archivo_excel')

        if not uploaded_file:
            return JsonResponse(
                {"success": False, "message": "No se ha subido ningún archivo."},
                status=400
            )

        # 1️⃣ Traer la auditoría
        try:
            audit = Audit.objects.get(pk=audit_id)
        except Audit.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Auditoría no encontrada."},
                status=404
            )

        # 2️⃣ Detectar si es Revisoría Fiscal
        #    En tus vistas ya se ve claro:
        #    tipoAuditoria = 'F' (financiera), 'I' (interna), 'R' (revisoria)
        if getattr(audit, "tipoAuditoria", None) == 'R':
            # 🧾 Auditoría de Revisoría Fiscal → usamos el importador especial
            importer = RevisoriaEstadosFinancierosImporter(uploaded_file, audit_id)
        else:
            # 📊 Auditorías Financiera / Interna → importador general
            importer = EstadosFinancierosImporter(uploaded_file, audit_id)

        # 3️⃣ Validar y procesar archivo
        if importer.validate_file():
            success, message = importer.process_file()
            return JsonResponse(
                {"success": success, "message": message},
                status=200 if success else 500
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El archivo no contiene hojas válidas de estados financieros."
                },
                status=400
            )

    # GET → render del formulario
    return render(request, "auditoria/importar_cuentas.html")