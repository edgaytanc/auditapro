"""
Generadores de archivos (Excel, Word y PDF) para el papel de trabajo de
Muestreo NIA 530.

Reciben el diccionario producido por auditoria.services.muestreo_nia530 y un
diccionario con la información de la auditoría:

    info_auditoria = {
        'entidad': str,      # audit.identidad
        'titulo': str,       # audit.title
        'periodo': str,      # rango de fechas de la auditoría
        'audit_id': int,
        'moneda': str,
    }

Todos devuelven bytes listos para servir como descarga. El PDF depende de
weasyprint (disponible en el contenedor de producción); si la librería no está
instalada, generar_pdf devuelve None y la vista debe ofrecer el Excel como
alternativa.
"""

import html as html_utils
import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

# Colores institucionales (azul consistente con las pantallas del sistema)
COLOR_AZUL = "2F6FED"
COLOR_AZUL_OSCURO = "1E4FBF"
COLOR_GRIS_CLARO = "F4F6F9"


def nombre_archivo(resultado, audit_id, extension):
    """Nombre estándar del archivo: Muestreo_NIA530_<metodo>_<auditid>.<ext>"""
    return f"Muestreo_NIA530_{resultado['metodo']}_{audit_id}.{extension}"


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def _estilo_encabezado(celda):
    """Aplica el estilo de encabezado azul con letra blanca."""
    celda.font = Font(bold=True, color="FFFFFF")
    celda.fill = PatternFill(start_color=COLOR_AZUL, end_color=COLOR_AZUL, fill_type="solid")
    celda.alignment = Alignment(horizontal="left", vertical="center")


def _borde_fino():
    lado = Side(style="thin", color="B7C1D1")
    return Border(left=lado, right=lado, top=lado, bottom=lado)


def _escribir_tabla(hoja, fila_inicial, titulo, encabezados, filas, anchos=None):
    """Escribe una tabla sencilla con título, encabezados en azul y bordes finos."""
    borde = _borde_fino()

    celda_titulo = hoja.cell(row=fila_inicial, column=1, value=titulo)
    celda_titulo.font = Font(bold=True, size=12, color=COLOR_AZUL_OSCURO)
    fila = fila_inicial + 1

    for columna, encabezado in enumerate(encabezados, start=1):
        celda = hoja.cell(row=fila, column=columna, value=encabezado)
        _estilo_encabezado(celda)
        celda.border = borde
    fila += 1

    for datos_fila in filas:
        for columna, valor in enumerate(datos_fila, start=1):
            celda = hoja.cell(row=fila, column=columna, value=valor)
            # ⚠️ Textos que empiezan con '=' (p. ej. partidas capturadas por el
            # auditor) se fuerzan como texto para que Excel no los interprete
            # como fórmulas.
            if isinstance(valor, str) and valor.startswith('='):
                celda.data_type = 's'
            celda.border = borde
            if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                celda.number_format = '#,##0' if isinstance(valor, int) else '#,##0.00'
        fila += 1

    if anchos:
        for columna, ancho in enumerate(anchos, start=1):
            hoja.column_dimensions[get_column_letter(columna)].width = ancho
    return fila + 1  # siguiente fila libre (deja una en blanco)


def generar_excel(info_auditoria, resultado):
    """Genera el papel de trabajo en Excel con hojas Parámetros / Resultados / Selección."""
    libro = Workbook()

    # --- Hoja Parámetros ---
    hoja = libro.active
    hoja.title = "Parámetros"
    filas_generales = [
        ("Entidad", info_auditoria.get('entidad', '')),
        ("Auditoría", info_auditoria.get('titulo', '')),
        ("Período", info_auditoria.get('periodo', '')),
        ("Método de muestreo", resultado['metodo_nombre']),
        ("Referencia normativa", resultado['nia_ref']),
        ("Fecha de generación", date.today().strftime("%d/%m/%Y")),
    ]
    if resultado.get('semilla') is not None:
        filas_generales.append(("Semilla de selección (reproducibilidad)", resultado['semilla']))
    fila = _escribir_tabla(
        hoja, 1, "Papel de Trabajo — Muestreo NIA 530",
        ["Dato", "Valor"], filas_generales, anchos=[42, 45],
    )
    _escribir_tabla(
        hoja, fila, "Parámetros del método",
        ["Parámetro", "Valor"], list(resultado['parametros'].items()),
    )

    # --- Hoja Resultados ---
    hoja_resultados = libro.create_sheet("Resultados")
    fila = _escribir_tabla(
        hoja_resultados, 1, "Resultados del cálculo",
        ["Resultado", "Valor"], list(resultado['resultados'].items()), anchos=[42, 45],
    )
    celda_formula = hoja_resultados.cell(row=fila, column=1, value="Fórmula aplicada")
    celda_formula.font = Font(bold=True, color=COLOR_AZUL_OSCURO)
    celda_texto = hoja_resultados.cell(row=fila + 1, column=1, value=resultado['formula_texto'])
    celda_texto.alignment = Alignment(wrap_text=True, vertical="top")
    hoja_resultados.merge_cells(start_row=fila + 1, start_column=1, end_row=fila + 1, end_column=2)
    hoja_resultados.row_dimensions[fila + 1].height = 60

    # --- Hoja Selección ---
    # Cuando la muestra se generó desde el Excel de datos importado, se
    # detallan las partidas reales (documento, descripción, fecha y monto);
    # si el auditor trabajó solo con parámetros, se listan los números.
    hoja_seleccion = libro.create_sheet("Selección")
    detalle = resultado.get('detalle_partidas')

    if detalle:
        filas_seleccion = [
            (item['no'], item['documento'], item['descripcion'],
             item['fecha'], item['monto'], '')
            for item in detalle
        ]
        _escribir_tabla(
            hoja_seleccion, 1, "Partidas seleccionadas",
            ["Nº", "N.º Documento", "Descripción", "Fecha", "Monto", "Marca"],
            filas_seleccion, anchos=[8, 20, 46, 14, 18, 12],
        )
    else:
        filas_seleccion = [
            (item['numero'], item['elemento'], '')
            for item in resultado['seleccion']
        ]
        _escribir_tabla(
            hoja_seleccion, 1, "Elementos seleccionados",
            ["Nº", "Elemento seleccionado", "Marca"], filas_seleccion, anchos=[8, 70, 14],
        )

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

def _tabla_word(documento, encabezados, filas):
    """Crea una tabla con estilo de cuadrícula y encabezados en negrita."""
    tabla = documento.add_table(rows=1, cols=len(encabezados))
    tabla.style = 'Table Grid'
    for indice, encabezado in enumerate(encabezados):
        celda = tabla.rows[0].cells[indice]
        celda.text = ''
        ejecucion = celda.paragraphs[0].add_run(encabezado)
        ejecucion.bold = True
    for datos_fila in filas:
        celdas = tabla.add_row().cells
        for indice, valor in enumerate(datos_fila):
            celdas[indice].text = str(valor)
    return tabla


def generar_word(info_auditoria, resultado):
    """Genera el papel de trabajo en Word (python-docx)."""
    documento = Document()

    titulo = documento.add_heading("Papel de Trabajo — Muestreo NIA 530", level=1)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    encabezado = documento.add_paragraph()
    encabezado.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ejecucion = encabezado.add_run(
        f"{info_auditoria.get('entidad', '')} · {info_auditoria.get('titulo', '')}\n"
        f"Período: {info_auditoria.get('periodo', '')} · "
        f"Fecha de generación: {date.today().strftime('%d/%m/%Y')}"
    )
    ejecucion.font.size = Pt(10)

    documento.add_heading(f"Método: {resultado['metodo_nombre']} ({resultado['nia_ref']})", level=2)

    documento.add_heading("Parámetros", level=3)
    filas_parametros = list(resultado['parametros'].items())
    if resultado.get('semilla') is not None:
        filas_parametros.append(("Semilla de selección (reproducibilidad)", resultado['semilla']))
    _tabla_word(documento, ["Parámetro", "Valor"], filas_parametros)

    documento.add_heading("Resultados", level=3)
    _tabla_word(documento, ["Resultado", "Valor"], list(resultado['resultados'].items()))

    parrafo_formula = documento.add_paragraph()
    parrafo_formula.add_run("Fórmula aplicada: ").bold = True
    parrafo_formula.add_run(resultado['formula_texto'])

    documento.add_heading("Elementos seleccionados", level=3)
    _tabla_word(
        documento, ["Nº", "Elemento seleccionado", "Marca"],
        [(item['numero'], item['elemento'], '') for item in resultado['seleccion']],
    )

    # Bloque de firmas
    documento.add_paragraph()
    tabla_firmas = documento.add_table(rows=2, cols=2)
    tabla_firmas.style = 'Table Grid'
    tabla_firmas.rows[0].cells[0].paragraphs[0].add_run("Elaboró").bold = True
    tabla_firmas.rows[0].cells[1].paragraphs[0].add_run("Revisó").bold = True
    tabla_firmas.rows[1].cells[0].text = "Nombre / Firma / Fecha:"
    tabla_firmas.rows[1].cells[1].text = "Nombre / Firma / Fecha:"

    buffer = io.BytesIO()
    documento.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# PDF (weasyprint — disponible solo en el contenedor de producción)
# ---------------------------------------------------------------------------

def _esc(valor):
    """Escapa texto para HTML (los datos pueden incluir texto libre del auditor)."""
    return html_utils.escape(str(valor))


def _tabla_html(encabezados, filas):
    """Arma una tabla HTML sencilla para el PDF (valores escapados)."""
    encabezado_html = "".join(f"<th>{_esc(encabezado)}</th>" for encabezado in encabezados)
    filas_html = "".join(
        "<tr>" + "".join(f"<td>{_esc(valor)}</td>" for valor in datos_fila) + "</tr>"
        for datos_fila in filas
    )
    return f"<table><thead><tr>{encabezado_html}</tr></thead><tbody>{filas_html}</tbody></table>"


def generar_html_pdf(info_auditoria, resultado):
    """HTML autocontenido (CSS en línea) que sirve de plantilla para el PDF."""
    filas_parametros = list(resultado['parametros'].items())
    if resultado.get('semilla') is not None:
        filas_parametros.append(("Semilla de selección (reproducibilidad)", resultado['semilla']))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #1c2430; margin: 28px; }}
  h1 {{ font-size: 17px; color: #{COLOR_AZUL_OSCURO}; text-align: center; margin-bottom: 2px; }}
  .subtitulo {{ text-align: center; color: #6b7482; margin-bottom: 18px; }}
  h2 {{ font-size: 13px; color: #{COLOR_AZUL_OSCURO}; border-bottom: 2px solid #{COLOR_AZUL}; padding-bottom: 3px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 14px; }}
  th {{ background: #{COLOR_AZUL}; color: #fff; text-align: left; padding: 5px 7px; font-size: 10.5px; }}
  td {{ border: 1px solid #cdd5e1; padding: 4px 7px; }}
  tr:nth-child(even) td {{ background: #{COLOR_GRIS_CLARO}; }}
  .formula {{ background: #eaf0ff; border-left: 3px solid #{COLOR_AZUL}; padding: 8px 10px; margin-bottom: 14px; }}
  .firmas {{ width: 100%; margin-top: 30px; }}
  .firmas td {{ width: 50%; height: 55px; vertical-align: bottom; }}
</style>
</head>
<body>
  <h1>Papel de Trabajo — Muestreo NIA 530</h1>
  <div class="subtitulo">
    {_esc(info_auditoria.get('entidad', ''))} · {_esc(info_auditoria.get('titulo', ''))}<br>
    Período: {_esc(info_auditoria.get('periodo', ''))} · Fecha de generación: {date.today().strftime('%d/%m/%Y')}
  </div>

  <h2>Método: {_esc(resultado['metodo_nombre'])} ({_esc(resultado['nia_ref'])})</h2>

  <h2>Parámetros</h2>
  {_tabla_html(["Parámetro", "Valor"], filas_parametros)}

  <h2>Resultados</h2>
  {_tabla_html(["Resultado", "Valor"], list(resultado['resultados'].items()))}

  <div class="formula"><b>Fórmula aplicada:</b> {_esc(resultado['formula_texto'])}</div>

  <h2>Elementos seleccionados</h2>
  {_tabla_html(["Nº", "Elemento seleccionado", "Marca"],
               [(item['numero'], item['elemento'], '') for item in resultado['seleccion']])}

  <table class="firmas">
    <tr><th>Elaboró</th><th>Revisó</th></tr>
    <tr><td>Nombre / Firma / Fecha:</td><td>Nombre / Firma / Fecha:</td></tr>
  </table>
</body>
</html>"""


def generar_pdf(info_auditoria, resultado):
    """
    Genera el PDF con weasyprint. Devuelve None si la librería no está
    instalada (entorno local): la vista debe ofrecer el Excel como alternativa.
    """
    try:
        from weasyprint import HTML
    except Exception:
        return None
    html = generar_html_pdf(info_auditoria, resultado)
    return HTML(string=html).write_pdf()
