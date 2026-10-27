import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
)
from django.shortcuts import (
    redirect,
    render,
)

from audits.decorators import (
    selected_audit_required,
)
from tools.access import (
    get_tool_record_for_user_or_404,
)
from users.permissions import (
    has_module_permission,
    is_team_manager,
)

from .catalog import build_default_entries
from .models import PermanentFileEntry
from .exporters import build_export_response


DOCUMENTS = [
    {
        "id": "1",
        "section": "general",
        "nombre": "1. Información General",
        "archivo": (
            "1 INFORMACION GENERAL.docx"
        ),
    },
    {
        "id": "2",
        "section": "organization",
        "nombre": (
            "2. Estructura Organizacional"
        ),
        "archivo": (
            "2 ESTRUCTURA ORGANIZACIONAL.docx"
        ),
    },
    {
        "id": "3",
        "section": "regulations",
        "nombre": (
            "3. Leyes y Regulaciones"
        ),
        "archivo": (
            "3 LEYES Y REGULACIONES.docx"
        ),
    },
    {
        "id": "4",
        "section": "operations",
        "nombre": (
            "4. Planificación de Operaciones"
        ),
        "archivo": (
            "4 PLANIFICACIÓN DE OPERACIONES.docx"
        ),
    },
    {
        "id": "5",
        "section": "administrative",
        "nombre": (
            "5 INFORMACIÓN ADMINISTRATIVA"
        ),
        "archivo": (
            "5 INFORMACIÓN ADMINISTRATIVA.docx"
        ),
    },
    {
        "id": "6",
        "section": "financial",
        "nombre": (
            "6. Información Contable, "
            "Presupuestaria y Financiera"
        ),
        "archivo": (
            "6 INFORMACIÓN CONTABLE, "
            "PRESUPUESTARIA Y FINANCIERA.docx"
        ),
    },
]


ALLOWED_DOCUMENTS = {
    document["archivo"]
    for document in DOCUMENTS
}


FIELD_LABELS = {
    "value": "Valor",
    "name": "Nombre",
    "application": "Aplicación",
    "responsible": "Responsable",
    "cycle": "Ciclo",
    "status": "Estado",
    "bank": "Banco",
    "account_number": "No. Cuenta",
    "account_type": "Tipo de Cuenta",
    "balance": "Saldo",
    "currency": "Moneda",
    "actual": "Real",
    "budgeted": "Presupuestado",
    "reference": "Referencia",
    "evaluation": "Evaluación",
}


GROUP_LABELS = {
    "entity_data": (
        "Datos generales de la entidad"
    ),
    "key_positions": (
        "Organigrama clave"
    ),
    "legal_framework": (
        "Marco normativo aplicable"
    ),
    "operating_cycles": (
        "Ciclos operativos clave"
    ),
    "legal_documents": (
        "Documentos legales vigentes"
    ),
    "general_financial_data": (
        "Información financiera general"
    ),
    "bank_accounts": (
        "Cuentas bancarias registradas"
    ),
    "income_statement": (
        "Estado de resultados vs. presupuesto"
    ),
    "financial_ratios": (
        "Ratios financieros clave"
    ),
}


def _user_can_archive_action(
    user,
    action,
):
    """
    Determina si el usuario puede ver una acción
    del Archivo Permanente.
    """

    return (
        user.is_superuser
        or user.is_staff
        or is_team_manager(
            user
        )
        or has_module_permission(
            user,
            "workpapers",
            action,
        )
    )


def _ensure_permanent_file_entries(
    request: HttpRequest,
    audit,
):
    """
    Crea solamente los registros iniciales
    que todavía no existen.

    Los registros eliminados lógicamente no
    se generan nuevamente.
    """

    existing_keys = set(
        PermanentFileEntry.objects
        .filter(
            audit=audit,
        )
        .values_list(
            "section",
            "row_key",
        )
    )

    entries_to_create = []

    for default_entry in (
        build_default_entries(
            audit
        )
    ):
        entry_key = (
            default_entry["section"],
            default_entry["row_key"],
        )

        if entry_key in existing_keys:
            continue

        entries_to_create.append(
            PermanentFileEntry(
                audit=audit,
                created_by=request.user,
                updated_by=request.user,
                **default_entry,
            )
        )

    if not entries_to_create:
        return 0

    with transaction.atomic():
        PermanentFileEntry.objects.bulk_create(
            entries_to_create,
            ignore_conflicts=True,
        )

    return len(
        entries_to_create
    )


def _build_entry_fields(
    entry,
):
    """
    Convierte el JSON del registro en campos
    editables para la plantilla.
    """

    fields = []

    for key, value in (
        entry.data.items()
    ):
        fields.append({
            "key": key,
            "label": FIELD_LABELS.get(
                key,
                key.replace(
                    "_",
                    " ",
                ).title(),
            ),
            "value": (
                value
                if value is not None
                else ""
            ),
        })

    return fields


def _build_section_cards(
    audit,
):
    """
    Organiza los registros por sección y grupo.
    """

    entries = list(
        PermanentFileEntry.objects
        .filter(
            audit=audit,
            is_active=True,
        )
        .order_by(
            "section",
            "group_key",
            "sort_order",
            "id",
        )
    )

    entries_by_section = {
        section_key: {}
        for section_key, _label
        in PermanentFileEntry.SECTION_CHOICES
    }

    for entry in entries:
        section_groups = (
            entries_by_section.setdefault(
                entry.section,
                {},
            )
        )

        group_entries = (
            section_groups.setdefault(
                entry.group_key,
                [],
            )
        )

        group_entries.append({
            "entry": entry,
            "fields": (
                _build_entry_fields(
                    entry
                )
            ),
        })

    section_cards = []

    for number, (
        section_key,
        section_label,
    ) in enumerate(
        PermanentFileEntry.SECTION_CHOICES,
        start=1,
    ):
        section_groups = (
            entries_by_section.get(
                section_key,
                {},
            )
        )

        groups = []

        section_total = 0
        automatic_total = 0
        manual_total = 0

        for group_key, group_entries in (
            section_groups.items()
        ):
            groups.append({
                "key": group_key,
                "label": GROUP_LABELS.get(
                    group_key,
                    group_key.replace(
                        "_",
                        " ",
                    ).title(),
                ),
                "entries": group_entries,
            })

            section_total += len(
                group_entries
            )

            automatic_total += sum(
                1
                for row in group_entries
                if (
                    row["entry"].origin
                    == "automatic"
                )
            )

            manual_total += sum(
                1
                for row in group_entries
                if (
                    row["entry"].origin
                    == "manual"
                )
            )

        section_cards.append({
            "number": number,
            "key": section_key,
            "label": section_label,
            "groups": groups,
            "total": section_total,
            "automatic": automatic_total,
            "manual": manual_total,
        })

    return section_cards


def _update_entry(
    request,
    entry,
):
    """
    Actualiza solamente las claves JSON que ya
    pertenecen al registro.
    """

    updated_data = {}

    for field_key in entry.data.keys():
        posted_value = request.POST.get(
            f"field_{field_key}",
            "",
        )

        updated_data[field_key] = (
            posted_value.strip()
        )

    entry.data = updated_data
    entry.updated_by = request.user

    entry.full_clean()

    entry.save(
        update_fields=[
            "data",
            "updated_by",
            "updated_at",
        ]
    )


@login_required
@selected_audit_required(
    module="workpapers",
    action="view",
)
def archivo(
    request: HttpRequest,
):
    """
    Archivo Permanente editable de la auditoría
    seleccionada.
    """

    audit = request.selected_audit

    created_count = (
        _ensure_permanent_file_entries(
            request,
            audit,
        )
    )

    if created_count:
        messages.success(
            request,
            (
                "Se generaron "
                f"{created_count} registros "
                "iniciales del Archivo Permanente."
            ),
        )

    entry_action = (
        request.POST.get(
            "entry_action",
            "",
        )
        .strip()
        .lower()
    )

    # El POST utilizado para seleccionar la auditoría
    # no contiene entry_action y debe continuar normalmente.
    if (
        request.method == "POST"
        and entry_action
    ):
        record_id = request.POST.get(
            "record_id"
        )

        if entry_action == "update":
            entry = (
                get_tool_record_for_user_or_404(
                    request=request,
                    model=PermanentFileEntry,
                    record_id=record_id,
                    action="edit",
                    queryset=(
                        PermanentFileEntry.objects
                        .filter(
                            is_active=True,
                        )
                    ),
                )
            )

            try:
                _update_entry(
                    request,
                    entry,
                )

                messages.success(
                    request,
                    (
                        f"{entry.title} fue "
                        "guardado correctamente."
                    ),
                )

            except Exception as error:
                messages.error(
                    request,
                    (
                        "No fue posible guardar "
                        f"{entry.title}: {error}"
                    ),
                )

        elif entry_action == "delete":
            entry = (
                get_tool_record_for_user_or_404(
                    request=request,
                    model=PermanentFileEntry,
                    record_id=record_id,
                    action="delete",
                    queryset=(
                        PermanentFileEntry.objects
                        .filter(
                            is_active=True,
                        )
                    ),
                )
            )

            entry.is_active = False
            entry.updated_by = request.user

            entry.save(
                update_fields=[
                    "is_active",
                    "updated_by",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                (
                    f"{entry.title} fue "
                    "eliminado correctamente."
                ),
            )

        else:
            messages.error(
                request,
                (
                    "La operación solicitada "
                    "no es válida."
                ),
            )

        return redirect(
            "archivo_permanente"
        )

    section_cards = (
        _build_section_cards(
            audit
        )
    )

    context = {
        "selected_audit": (
            request.session.get(
                "selected_audit"
            )
            or {}
        ),

        "section_cards": (
            section_cards
        ),

        "total_sections": len(
            section_cards
        ),

        "total_entries": sum(
            section["total"]
            for section in section_cards
        ),

        "can_edit_entries": (
            _user_can_archive_action(
                request.user,
                "edit",
            )
        ),

        "can_delete_entries": (
            _user_can_archive_action(
                request.user,
                "delete",
            )
        ),

        # Se mantienen mientras construimos
        # las exportaciones dinámicas.
        "documentos": DOCUMENTS,
    }

    return render(
        request,
        "archivo.html",
        context,
    )


@login_required
@selected_audit_required(
    module="workpapers",
    action="view",
)
def exportar_archivo_permanente(
    request: HttpRequest,
    formato: str,
    seccion: str,
):
    """
    Exporta una sección o el expediente completo
    usando la información guardada en la auditoría.
    """

    audit = request.selected_audit

    formato = (
        formato
        or ""
    ).strip().lower()

    seccion = (
        seccion
        or ""
    ).strip().lower()

    formatos_validos = {
        "word",
        "pdf",
    }

    secciones_validas = {
        section_key
        for section_key, _label
        in PermanentFileEntry.SECTION_CHOICES
    }

    if formato not in formatos_validos:
        raise Http404(
            "El formato solicitado no es válido."
        )

    if (
        seccion != "all"
        and seccion not in secciones_validas
    ):
        raise Http404(
            "La sección solicitada no es válida."
        )

    _ensure_permanent_file_entries(
        request,
        audit,
    )

    section_cards = (
        _build_section_cards(
            audit
        )
    )

    if seccion != "all":
        section_cards = [
            section
            for section in section_cards
            if section["key"] == seccion
        ]

    if not section_cards:
        raise Http404(
            "No existe información para exportar."
        )

    return build_export_response(
        request=request,
        audit=audit,
        section_cards=section_cards,
        export_format=formato,
    )

@login_required
def descargar_archivo(
    request: HttpRequest,
    nombre_archivo: str,
):
    """
    Descarga únicamente una de las seis
    plantillas permitidas.
    """

    if (
        nombre_archivo
        not in ALLOWED_DOCUMENTS
    ):
        raise Http404(
            (
                "El archivo solicitado "
                "no está disponible."
            )
        )

    ruta_archivo = os.path.join(
        settings.BASE_DIR,
        "static",
        (
            "template-modulo-"
            "archivo-permanente"
        ),
        (
            "MODULO ARCHIVO "
            "PERMANENTE"
        ),
        nombre_archivo,
    )

    if not os.path.isfile(
        ruta_archivo
    ):
        raise Http404(
            (
                "El archivo solicitado "
                "no existe."
            )
        )

    return FileResponse(
        open(
            ruta_archivo,
            "rb",
        ),
        as_attachment=True,
        filename=nombre_archivo,
    )