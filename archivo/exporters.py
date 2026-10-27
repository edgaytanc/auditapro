"""
Exportaciones dinámicas del Archivo Permanente.

Genera Word y PDF usando únicamente los registros activos de la
auditoría seleccionada. No modifica la base de datos.
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import Iterable
from urllib.parse import quote

from django.http import FileResponse, HttpResponse
from django.utils.text import slugify


EMPTY_VALUE = "Sin registrar"


def _text(value) -> str:
    """Convierte cualquier valor a texto visible y seguro."""

    if value is None:
        return ""

    return str(value).strip()


def _display_value(value) -> str:
    """Devuelve el valor o una marca clara cuando está vacío."""

    normalized = _text(value)
    return normalized or EMPTY_VALUE


def _build_filename(audit, section_cards, extension: str) -> str:
    """Construye un nombre de archivo estable y sin caracteres problemáticos."""

    entity_name = (
        _text(getattr(audit, "identidad", ""))
        or _text(getattr(audit, "title", ""))
        or "auditoria"
    )

    if len(section_cards) == 1:
        export_scope = section_cards[0]["label"]
    else:
        export_scope = "archivo permanente completo"

    base_name = slugify(
        f"{export_scope} {entity_name}",
        allow_unicode=False,
    ).replace("-", "_")

    return f"{base_name or 'archivo_permanente'}.{extension}"


def _set_content_disposition(response, filename: str) -> None:
    """Agrega un nombre compatible con navegadores y caracteres UTF-8."""

    encoded_filename = quote(filename)

    response["Content-Disposition"] = (
        f"attachment; filename=\"{filename}\"; "
        f"filename*=UTF-8''{encoded_filename}"
    )


def _audit_period(audit) -> str:
    """Obtiene el período configurado o lo calcula desde las fechas."""

    configured_period = _text(
        getattr(audit, "periodo_auditado", "")
    )

    if configured_period:
        return configured_period

    start_date = getattr(audit, "fechaInit", None)
    end_date = getattr(audit, "fechaEnd", None)

    if start_date and end_date:
        return (
            f"{start_date.strftime('%d/%m/%Y')} - "
            f"{end_date.strftime('%d/%m/%Y')}"
        )

    return EMPTY_VALUE


def _field_lines(row) -> list[str]:
    """Convierte los campos dinámicos de una fila en líneas legibles."""

    fields = row.get("fields") or []

    if not fields:
        return [EMPTY_VALUE]

    return [
        f"{_text(field.get('label')) if _text(field.get('label')).lower() != 'valor' else 'Dato'}: "
        f"{_display_value(field.get('value'))}"
        for field in fields
    ]


def _add_word_document_header(document, audit) -> None:
    """Agrega encabezado general al documento Word."""

    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    title_run = title.add_run("ARCHIVO PERMANENTE")
    title_run.bold = True
    title_run.font.size = Pt(17)

    entity = document.add_paragraph()
    entity.alignment = WD_ALIGN_PARAGRAPH.CENTER

    entity_run = entity.add_run(
        _display_value(getattr(audit, "identidad", ""))
    )
    entity_run.bold = True
    entity_run.font.size = Pt(11)

    details = document.add_paragraph()
    details.alignment = WD_ALIGN_PARAGRAPH.CENTER
    details.add_run(
        "Auditoría: "
        f"{_display_value(getattr(audit, 'title', ''))} | "
        "Período: "
        f"{_audit_period(audit)} | "
        "Moneda: "
        f"{_display_value(getattr(audit, 'moneda', ''))}"
    )

    generated = document.add_paragraph()
    generated.alignment = WD_ALIGN_PARAGRAPH.CENTER
    generated.add_run(
        "Generado el "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ).italic = True


def _configure_word_document(document) -> None:
    """Configura márgenes y estilos básicos del Word."""

    from docx.shared import Inches, Pt

    section = document.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    normal_style = document.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(9)

    document.styles["Title"].font.name = "Arial"
    document.styles["Heading 1"].font.name = "Arial"
    document.styles["Heading 2"].font.name = "Arial"


def _write_word_section(document, section_card) -> None:
    """Escribe una sección completa en el documento Word."""

    document.add_heading(
        _text(section_card.get("label")),
        level=1,
    )

    summary = document.add_paragraph()
    summary.add_run("Registros activos: ").bold = True
    summary.add_run(str(section_card.get("total", 0)))
    summary.add_run(" | Automáticos: ").bold = True
    summary.add_run(str(section_card.get("automatic", 0)))
    summary.add_run(" | Manuales: ").bold = True
    summary.add_run(str(section_card.get("manual", 0)))

    for group in section_card.get("groups") or []:
        document.add_heading(
            _text(group.get("label")),
            level=2,
        )

        table = document.add_table(
            rows=1,
            cols=3,
        )
        table.style = "Table Grid"

        header_cells = table.rows[0].cells
        header_cells[0].text = "Registro"
        header_cells[1].text = "Información"
        header_cells[2].text = "Guía"

        for cell in header_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True

        for row in group.get("entries") or []:
            entry = row["entry"]
            cells = table.add_row().cells

            cells[0].text = _display_value(entry.title)
            cells[1].text = "\n".join(_field_lines(row))
            cells[2].text = _display_value(entry.guide)

        document.add_paragraph()


def build_word_response(audit, section_cards):
    """Genera una respuesta .docx con una o todas las secciones."""

    try:
        from docx import Document
    except ImportError:
        return HttpResponse(
            (
                "La exportación Word no está disponible. "
                "Instala python-docx en el entorno del proyecto."
            ),
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    document = Document()
    _configure_word_document(document)
    _add_word_document_header(document, audit)

    for index, section_card in enumerate(section_cards):
        if index:
            document.add_page_break()

        _write_word_section(
            document,
            section_card,
        )

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)

    filename = _build_filename(
        audit,
        section_cards,
        "docx",
    )

    response = FileResponse(
        buffer,
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )
    _set_content_disposition(response, filename)

    return response


def _pdf_field_html(row) -> str:
    """Construye la celda de datos para el PDF."""

    lines = []

    for field in row.get("fields") or []:
        label = escape(
            _text(field.get("label"))
        )
        value = escape(
            _display_value(field.get("value"))
        )

        lines.append(
            f"<div><strong>{'Dato' if label.lower() == 'valor' else label}:</strong> {value}</div>"
        )

    return "".join(lines) or escape(EMPTY_VALUE)


def _build_pdf_html(audit, section_cards) -> str:
    """Construye el HTML autocontenido utilizado por WeasyPrint."""

    section_blocks = []

    for section_card in section_cards:
        group_blocks = []

        for group in section_card.get("groups") or []:
            rows = []

            for row in group.get("entries") or []:
                entry = row["entry"]

                rows.append(
                    "<tr>"
                    f"<td class='record'>{escape(_display_value(entry.title))}</td>"
                    f"<td>{_pdf_field_html(row)}</td>"
                    f"<td>{escape(_display_value(entry.guide))}</td>"
                    "</tr>"
                )

            group_blocks.append(
                "<div class='group'>"
                f"<h2>{escape(_text(group.get('label')))}</h2>"
                "<table>"
                "<thead><tr>"
                "<th>Registro</th>"
                "<th>Información</th>"
                "<th>Guía</th>"
                "</tr></thead>"
                f"<tbody>{''.join(rows)}</tbody>"
                "</table>"
                "</div>"
            )

        section_blocks.append(
            "<section class='archive-section'>"
            f"<h1>{escape(_text(section_card.get('label')))}</h1>"
            "<p class='section-summary'>"
            f"Registros activos: {section_card.get('total', 0)} | "
            f"Automáticos: {section_card.get('automatic', 0)} | "
            f"Manuales: {section_card.get('manual', 0)}"
            "</p>"
            f"{''.join(group_blocks)}"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Archivo Permanente</title>
  <style>
    @page {{
      size: A4;
      margin: 14mm 12mm 15mm;
      @bottom-left {{
        content: "AuditaPro - Archivo Permanente";
        color: #64748b;
        font-size: 7pt;
      }}
      @bottom-right {{
        content: "Página " counter(page) " de " counter(pages);
        color: #64748b;
        font-size: 7pt;
      }}
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      color: #0f172a;
      font-family: Arial, sans-serif;
      font-size: 8.5pt;
      line-height: 1.35;
    }}

    .document-header {{
      margin-bottom: 16px;
      padding: 14px;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      background: #eff6ff;
      text-align: center;
    }}

    .document-header h1 {{
      margin: 0 0 4px;
      color: #1d4ed8;
      font-size: 18pt;
    }}

    .document-header h2 {{
      margin: 0 0 5px;
      font-size: 12pt;
    }}

    .document-header p {{
      margin: 2px 0;
      color: #475569;
    }}

    .archive-section {{
      break-before: page;
    }}

    .archive-section:first-of-type {{
      break-before: auto;
    }}

    .archive-section > h1 {{
      margin: 0 0 4px;
      color: #1d4ed8;
      font-size: 14pt;
    }}

    .section-summary {{
      margin: 0 0 11px;
      color: #64748b;
      font-size: 8pt;
    }}

    .group {{
      margin: 0 0 13px;
      break-inside: avoid;
    }}

    .group h2 {{
      margin: 0;
      padding: 7px 8px;
      border: 1px solid #dbe4f0;
      border-bottom: 0;
      background: #f8fafc;
      font-size: 10pt;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}

    thead {{ display: table-header-group; }}

    tr {{ break-inside: avoid; }}

    th,
    td {{
      border: 1px solid #dbe4f0;
      padding: 6px;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}

    th {{
      background: #eff6ff;
      color: #1e3a8a;
      font-size: 7.5pt;
      text-align: left;
    }}

    th:nth-child(1), td:nth-child(1) {{ width: 19%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 31%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 12%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 38%; }}

    td.record {{ font-weight: bold; }}

    td div + div {{ margin-top: 3px; }}
  </style>
</head>
<body>
  <header class="document-header">
    <h1>ARCHIVO PERMANENTE</h1>
    <h2>{escape(_display_value(getattr(audit, 'identidad', '')))}</h2>
    <p><strong>Auditoría:</strong> {escape(_display_value(getattr(audit, 'title', '')))}</p>
    <p>
      <strong>Período:</strong> {escape(_audit_period(audit))}
      &nbsp; | &nbsp;
      <strong>Moneda:</strong> {escape(_display_value(getattr(audit, 'moneda', '')))}
    </p>
    <p>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
  </header>

  {''.join(section_blocks)}
</body>
</html>"""


def build_pdf_response(request, audit, section_cards):
    """Genera una respuesta PDF con una o todas las secciones."""

    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse(
            (
                "La exportación PDF no está disponible. "
                "WeasyPrint no está instalado en el entorno."
            ),
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    try:
        html_content = _build_pdf_html(
            audit,
            section_cards,
        )

        pdf_content = HTML(
            string=html_content,
            base_url=request.build_absolute_uri("/"),
        ).write_pdf()

    except Exception as error:
        return HttpResponse(
            f"No fue posible generar el PDF: {error}",
            status=500,
            content_type="text/plain; charset=utf-8",
        )

    filename = _build_filename(
        audit,
        section_cards,
        "pdf",
    )

    response = HttpResponse(
        pdf_content,
        content_type="application/pdf",
    )
    _set_content_disposition(response, filename)

    return response


def build_export_response(
    request,
    audit,
    section_cards: Iterable[dict],
    export_format: str,
):
    """Punto único para seleccionar el generador solicitado."""

    normalized_cards = list(section_cards)

    if export_format == "word":
        return build_word_response(
            audit,
            normalized_cards,
        )

    if export_format == "pdf":
        return build_pdf_response(
            request,
            audit,
            normalized_cards,
        )

    return HttpResponse(
        "El formato solicitado no es válido.",
        status=400,
        content_type="text/plain; charset=utf-8",
    )
