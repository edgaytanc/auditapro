"""Exportaciones de Herramientas desde registros guardados en Django.

No utiliza datos de muestra del mockup ni almacenamiento local del navegador.
Los modelos, permisos y flujos de edición existentes se conservan sin cambios.
"""
from datetime import timedelta
from html import escape
from io import BytesIO

from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from audits.decorators import selected_audit_required

from .models import (
    Activity,
    AuditTimeDistribution,
    AuditTimeSummary,
    SummaryHoursWorked,
    WorkingPapersStatus,
)


def _safe_text(value):
    """La hoja Excel no debe ejecutar fórmulas provenientes de campos libres."""
    if value is None:
        return ""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _hours(duration):
    return round(duration.total_seconds() / 3600, 2) if duration else 0


def _days(duration):
    return round(duration.total_seconds() / 86400, 2) if duration else 0


def _date(value):
    if not value:
        return ""
    return value.date().isoformat() if hasattr(value, "date") else str(value)


def _full_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


def _export_data(audit, section):
    """Las consultas SIEMPRE se filtran por el encargo autorizado."""
    if section == "tiempo":
        staff = AuditTimeSummary.objects.filter(audit=audit).select_related("assigned_auditor").order_by("appointment_number", "id")
        hours = SummaryHoursWorked.objects.filter(audit=audit).select_related("month").order_by("month__id", "id")
        groups = AuditTimeDistribution.objects.filter(audit=audit).select_related("assigned_auditor").order_by("distribution_type", "name")
        tables = [
            (
                "Personal y tiempo",
                ["Nombramiento", "Auditor", "Días programados", "Días reales", "Variación", "Observaciones"],
                [
                    [r.appointment_number, _full_name(r.assigned_auditor), _days(r.scheduled_days), _days(r.worked_days), round(_days(r.worked_days) - _days(r.scheduled_days), 2), r.observations or ""]
                    for r in staff
                ],
            ),
            (
                "Horas mensuales",
                ["Mes", "Horas planificadas", "Horas trabajadas", "Variación", "Observaciones"],
                [
                    [r.month.name, _hours(r.total_scheduled_hours), _hours(r.total_hours_worked), round(_hours(r.total_hours_worked) - _hours(r.total_scheduled_hours), 2), r.observations or ""]
                    for r in hours
                ],
            ),
            (
                "Etapas y componentes",
                ["Tipo", "Etapa o componente", "Auditor", "Horas planificadas", "Horas reales", "Variación", "Materialidad", "Riesgo", "Estado", "Observaciones"],
                [
                    [r.get_distribution_type_display(), r.name, _full_name(r.assigned_auditor), float(r.planned_hours), float(r.actual_hours), float(r.difference), r.get_materiality_display(), r.get_risk_level_display(), r.get_status_display(), r.observations or ""]
                    for r in groups
                ],
            ),
        ]
        return "Resumen de Tiempo", tables
    if section == "papeles":
        papers = WorkingPapersStatus.objects.filter(audit=audit).select_related("auditor", "current_status").order_by("reference", "id")
        return "Estado de Papeles de Trabajo", [(
            "Papeles de trabajo",
            ["Referencia", "Papel de trabajo", "Estado", "Auditor", "Inicio", "Fin", "Observaciones"],
            [[r.reference or "", r.working_papers, r.current_status.verbose_name, _full_name(r.auditor), _date(r.start_date), _date(r.end_date), r.observations or ""] for r in papers],
        )]
    if section == "cronograma":
        from .views import _cronograma_months, _days_in_month, _cronograma_status
        activities = list(Activity.objects.filter(audit=audit).select_related("created_by", "current_status").order_by("start_date", "id"))
        months = _cronograma_months(audit.fechaInit, audit.fechaEnd)
        rows = [
            [i, r.activity, r.reference or "", _full_name(r.created_by), _date(r.start_date), _date(r.end_date), _cronograma_status(r)[1], max((r.end_date - r.start_date).days, 1)]
            for i, r in enumerate(activities, start=1)
        ]
        gantt_rows = [
            [r.activity, r.reference or ""] + [_days_in_month(r, m["year"], m["month"]) for m in months]
            for r in activities
        ]
        return "Cronograma de Actividades", [
            ("Actividades", ["N°", "Actividad", "Ref.", "Auditor", "Inicio", "Fin", "Estado", "Días"], rows),
            ("Vista mensual", ["Actividad", "Ref."] + [f'{m["label"]} {m["year"]}' for m in months], gantt_rows),
        ]
    raise Http404("Submódulo de Herramientas no reconocido")


def _response_xlsx(title, audit, tables, filename):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        return HttpResponse("Falta openpyxl para exportar Excel.", status=503)
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, headings, rows in tables:
        sheet = workbook.create_sheet(sheet_name[:31])
        sheet.append([title])
        sheet.append([f'Auditoría: {audit.title}'])
        sheet.append([])
        sheet.append(headings)
        for cell in sheet[4]:
            cell.fill = PatternFill("solid", fgColor="EAF1FE")
            cell.font = Font(bold=True, color="214CA0")
        sheet.freeze_panes = "A5"
        sheet.auto_filter.ref = f"A4:{get_column_letter(len(headings))}{max(4, 4 + len(rows))}"
        for row in rows:
            sheet.append([_safe_text(value) if isinstance(value, str) else value for value in row])
        for column_idx, heading in enumerate(headings, start=1):
            width = min(max(len(str(heading)) + 3, 15), 48)
            sheet.column_dimensions[get_column_letter(column_idx)].width = width
        for row in sheet.iter_rows(min_row=5):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
    data = BytesIO()
    workbook.save(data)
    response = HttpResponse(data.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    return response


def _response_docx(title, audit, tables, filename):
    try:
        from docx import Document
        from docx.shared import Inches
        from docx.enum.section import WD_ORIENT
    except ImportError:
        return HttpResponse("Falta python-docx para exportar Word.", status=503)
    doc = Document()
    section = doc.sections[0]
    if max(len(headings) for _name, headings, _rows in tables) >= 7:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    doc.add_heading(title, 0)
    doc.add_paragraph(f'Auditoría: {audit.title}')
    for name, headings, rows in tables:
        doc.add_heading(name, level=2)
        table = doc.add_table(rows=1, cols=len(headings))
        table.style = "Table Grid"
        for cell, heading in zip(table.rows[0].cells, headings):
            cell.text = str(heading)
        for values in rows:
            cells = table.add_row().cells
            for cell, value in zip(cells, values):
                cell.text = str(value) if value is not None else ""
        doc.add_paragraph("")
    contents = BytesIO()
    doc.save(contents)
    response = HttpResponse(contents.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    response["Content-Disposition"] = f'attachment; filename="{filename}.docx"'
    return response


def _response_pdf(title, audit, tables, filename):
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        return HttpResponse("WeasyPrint o sus dependencias no están disponibles para PDF.", status=503)
    blocks = []
    for name, headings, rows in tables:
        head = "".join(f"<th>{escape(str(h))}</th>" for h in headings)
        body = "".join(
            "<tr>" + "".join(f"<td>{escape(str(v) if v is not None else '')}</td>" for v in values) + "</tr>"
            for values in rows
        )
        blocks.append(f"<h2>{escape(name)}</h2><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
    @page {{size:A4 landscape; margin:12mm}}body{{font-family:Arial,sans-serif;color:#172439;font-size:9px}}h1{{font-size:20px}}h2{{font-size:13px;margin-top:22px}}
    table{{width:100%;border-collapse:collapse;table-layout:fixed}}th,td{{border:1px solid #d8e1ec;padding:5px;overflow-wrap:anywhere;vertical-align:top}}th{{background:#eaf1fe;color:#2056c7;text-align:left}}tr{{break-inside:avoid}}
    </style></head><body><h1>{escape(title)}</h1><p>Auditoría: {escape(str(audit.title))}</p>{''.join(blocks)}</body></html>'''
    try:
        pdf = HTML(string=html).write_pdf()
    except Exception:
        return HttpResponse("Error al generar PDF. Revisa las dependencias de WeasyPrint en Windows.", status=503)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response


@login_required
@selected_audit_required("audit_time_summary_index", module="workpapers", action="view")
def exportar_herramientas(request, seccion, formato):
    """Exporta únicamente lo que el usuario puede consultar de su auditoría seleccionada."""
    if seccion not in {"tiempo", "papeles", "cronograma"} or formato not in {"xlsx", "docx", "pdf"}:
        raise Http404("Formato o sección no disponible")
    audit = request.selected_audit
    title, tables = _export_data(audit, seccion)
    filename = f"auditapro_{seccion}_{audit.pk}"
    if formato == "xlsx":
        return _response_xlsx(title, audit, tables, filename)
    if formato == "docx":
        return _response_docx(title, audit, tables, filename)
    return _response_pdf(title, audit, tables, filename)


@login_required
def herramientas_inicio(request):
    """Muestra directamente el primer submódulo si ya hay auditoría;
    si falta selección, conserva la pantalla de entrada anterior.
    """
    selected = request.session.get("selected_audit") or {}
    if isinstance(selected, dict) and selected.get("id"):
        return redirect("audit_time_summary_index")
    from .views import tools_page
    return tools_page(request)
