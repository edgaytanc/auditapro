import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction  # ✅ nuevo

from audits.models import Audit  # 👈 IMPORTANTE: traemos Audit

from auditoria.imports.estados_financieros_importer import (
    EstadosFinancierosImporter,
    RevisoriaEstadosFinancierosImporter,  # 👈 tu nuevo importador para revisoria
)


def _wipe_import_data_for_revisoria(audit_id: int) -> None:
    """
    ✅ SOLO REVISORÍA:
    Borra TODO lo importado para esta auditoría antes de cargar un nuevo archivo.
    Incluye también subcuentas.
    """
    from auditoria.models import (
        BalanceCuentas,
        RegistroAuxiliar,
        SaldoInicial,
        AjustesReclasificaciones,
        RevisoriaSubcuenta,
    )

    BalanceCuentas.objects.filter(audit_id=audit_id).delete()
    RegistroAuxiliar.objects.filter(audit_id=audit_id).delete()
    SaldoInicial.objects.filter(audit_id=audit_id).delete()
    AjustesReclasificaciones.objects.filter(audit_id=audit_id).delete()
    RevisoriaSubcuenta.objects.filter(audit_id=audit_id).delete()


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
        tipo = getattr(audit, "tipoAuditoria", None)

        if tipo == 'R':
            # 🧾 Auditoría de Revisoría Fiscal → usamos el importador especial
            importer = RevisoriaEstadosFinancierosImporter(uploaded_file, audit_id)
        else:
            # 📊 Auditorías Financiera / Interna → importador general (NO BORRAMOS NADA)
            importer = EstadosFinancierosImporter(uploaded_file, audit_id)

        # 3️⃣ Validar archivo
        if not importer.validate_file():
            return JsonResponse(
                {
                    "success": False,
                    "message": "El archivo no contiene hojas válidas de estados financieros."
                },
                status=400
            )

        # ✅ 4) Procesar (con wipe SOLO si es Revisoría)
        try:
            if tipo == 'R':
                # Revisoría: wipe + import dentro de una transacción
                with transaction.atomic():
                    _wipe_import_data_for_revisoria(audit_id)

                    # Si validate_file() leyó el archivo, reiniciamos el puntero
                    try:
                        uploaded_file.seek(0)
                    except Exception:
                        pass

                    success, message = importer.process_file()
            else:
                # Financiera/Interna: solo import (no se toca nada existente)
                success, message = importer.process_file()

            return JsonResponse(
                {"success": success, "message": message},
                status=200 if success else 500
            )
        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"Error importando: {str(e)}"},
                status=500
            )

    # GET → render del formulario
    return render(request, "auditoria/importar_cuentas.html")
