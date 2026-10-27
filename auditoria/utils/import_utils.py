import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import render

from audits.access import (
    get_audit_for_user_or_404,
)

from auditoria.imports.estados_financieros_importer import (
    EstadosFinancierosImporter,
    RevisoriaEstadosFinancierosImporter,
)


def _wipe_import_data_for_revisoria(
    audit_id: int,
) -> None:
    """
    Borra exclusivamente la información importada
    para una auditoría de Revisoría Fiscal.

    Esta limpieza se ejecuta antes de cargar un nuevo
    archivo y dentro de una transacción atómica.
    """

    from auditoria.models import (
        AjustesReclasificaciones,
        BalanceCuentas,
        RegistroAuxiliar,
        RevisoriaSubcuenta,
        SaldoInicial,
    )

    BalanceCuentas.objects.filter(
        audit_id=audit_id,
    ).delete()

    RegistroAuxiliar.objects.filter(
        audit_id=audit_id,
    ).delete()

    SaldoInicial.objects.filter(
        audit_id=audit_id,
    ).delete()

    AjustesReclasificaciones.objects.filter(
        audit_id=audit_id,
    ).delete()

    RevisoriaSubcuenta.objects.filter(
        audit_id=audit_id,
    ).delete()


def _wipe_import_data_for_subcuentas(audit_id):
    """Nueva importación de subcuentas; misma limpieza atómica usada en Revisoría."""
    _wipe_import_data_for_revisoria(audit_id)


def _limpiar_parametros_excel_financiero(audit_id):
    from auditoria.models import ParametrosAuditoria

    ParametrosAuditoria.objects.filter(audit_id=audit_id).update(
        fecha_corte1_excel=None, fecha_corte2_excel=None,
        fecha_corte3_excel=None, fecha_corte_actual_excel=None,
        ingresos_totales_excel=None, utilidad_antes_impuestos_excel=None,
    )


def _reset_uploaded_file(
    uploaded_file,
) -> None:
    """
    Intenta devolver el archivo cargado al inicio.

    Algunos importadores leen el archivo durante
    validate_file(), por lo que es necesario reiniciar
    el puntero antes de procesarlo.
    """

    try:
        uploaded_file.seek(0)

    except Exception:
        pass


@login_required
def importar_cuentas_contables(
    request,
    audit_id,
):
    """
    Importa estados financieros para una auditoría.

    Reglas de acceso:
    - GET: Papeles de Trabajo → Ver.
    - POST: Papeles de Trabajo → Editar.
    - La auditoría debe pertenecer al mismo equipo.
    - El integrante debe estar asignado a la auditoría.
    """

    if request.method not in {
        "GET",
        "POST",
    }:
        return HttpResponseNotAllowed(
            [
                "GET",
                "POST",
            ]
        )

    required_action = (
        "edit"
        if request.method == "POST"
        else "view"
    )

    audit = get_audit_for_user_or_404(
        request.user,
        audit_id,
        action=required_action,
        module="workpapers",
    )

    if request.method == "GET":
        return render(
            request,
            "auditoria/importar_cuentas.html",
            {
                "audit": audit,
            },
        )

    uploaded_file = request.FILES.get(
        "archivo_excel"
    )

    if not uploaded_file:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "No se ha subido ningún archivo."
                ),
            },
            status=400,
        )

    tipo_auditoria = getattr(
        audit,
        "tipoAuditoria",
        None,
    )

    if tipo_auditoria == "R":
        importer = (
            RevisoriaEstadosFinancierosImporter(
                uploaded_file,
                audit.id,
            )
        )

    else:
        importer = EstadosFinancierosImporter(
            uploaded_file,
            audit.id,
        )

    try:
        valid_file = importer.validate_file()

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "No fue posible validar el archivo: "
                    f"{str(error)}"
                ),
            },
            status=400,
        )

    if not valid_file:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "El archivo no contiene hojas válidas "
                    "de estados financieros."
                ),
            },
            status=400,
        )

    # validate_file() puede dejar el puntero
    # al final del archivo.
    _reset_uploaded_file(
        uploaded_file
    )

    try:
        if tipo_auditoria == "R":
            with transaction.atomic():
                _wipe_import_data_for_revisoria(
                    audit.id
                )

                _reset_uploaded_file(
                    uploaded_file
                )

                success, message = (
                    importer.process_file()
                )

                # Si el importador reporta fallo,
                # se fuerza rollback de la limpieza.
                if not success:
                    transaction.set_rollback(
                        True
                    )

        elif importer.es_formato_subcuentas():
            # El formato 2026 se reimporta sin duplicados ni datos residuales.
            with transaction.atomic():
                _wipe_import_data_for_subcuentas(audit.id)
                _reset_uploaded_file(uploaded_file)
                success, message = importer.process_file()
                if not success:
                    transaction.set_rollback(True)
        else:
            # Formato clásico: preservar datos importados existentes.
            success, message = importer.process_file()
            if success:
                _limpiar_parametros_excel_financiero(audit.id)

        return JsonResponse(
            {
                "success": success,
                "message": message,
            },
            status=200 if success else 500,
        )

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Error importando: "
                    f"{str(error)}"
                ),
            },
            status=500,
        )