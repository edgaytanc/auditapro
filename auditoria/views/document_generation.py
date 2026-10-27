"""Generación opcional de documentos con datos Auditor/Jefe, sobre el sistema actualizado."""
import os
import logging
from io import BytesIO
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponse, Http404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from audits.access import get_audit_for_user_or_404, allowed_audit_type_codes
from auditoria.views.utils import get_template_path
from auditoria.utils.replacements_utils import get_replacements_config, build_replacements_dict
from docx import Document
from openpyxl import load_workbook
logger = logging.getLogger(__name__)


def _get_requested_audit_type(request, audit):
    """Respeta el tipo elegido y los enlaces heredados sin parámetro tipo."""
    authorized = allowed_audit_type_codes(request.user, audit)
    explicit_type = request.GET.get('tipo')
    audit_type = explicit_type or (audit.tipoAuditoria if audit.tipoAuditoria in authorized
                                    else (authorized[0] if authorized else None))
    if audit_type not in authorized:
        raise Http404('Este tipo de auditoría no está habilitado.')
    return audit_type


def _safe_folder_path(base_dir, folder):
    """Rechaza rutas fuera de static/templates_base_* y segmentos ascendentes."""
    base = Path(base_dir).resolve()
    path = (base / (folder or "")).resolve()
    return str(path) if path == base or base in path.parents else None


def _safe_template_path(audit, folder, filename, audit_type=None):
    if not filename or filename != os.path.basename(filename) or filename in (".", ".."):
        return None
    base_dirs = {"F": "templates_base_financiera", "I": "templates_base_interna", "R": "templates_base_revisoria"}
    selected_type = audit_type or audit.tipoAuditoria
    base = Path(settings.BASE_DIR) / "static" / base_dirs.get(selected_type, "templates_base_financiera")
    requested_dir = _safe_folder_path(base, folder)
    if requested_dir is None:
        return None
    # No permitir que una búsqueda flexible salte a otra carpeta/plantilla.
    path = get_template_path(folder, filename, audit_type=selected_type)
    if not path:
        return None
    resolved = Path(path).resolve()
    allowed = Path(requested_dir)
    return str(resolved) if allowed == resolved.parent and base.resolve() in resolved.parents else None

def nombres_auditor_y_jefe(audit, usuario=None):
    """
    Nombres que se escriben en 'Elaboró' (auditor) y 'Revisó' (jefe/supervisor).

    Los datos salen del acceso al sistema, como pidió el cliente:
      · En grupo: el auditor son los usuarios asignados y el jefe es quien creó
        la auditoría.
      · Individual: no hay usuarios asignados, así que el auditor es el propio
        usuario que entró al sistema (antes se escribía 'Sin asignar').
    """
    def _nombre(usuario_modelo):
        if not usuario_modelo:
            return ""
        return (usuario_modelo.get_full_name() or usuario_modelo.username or "").strip()

    auditores_qs = getattr(audit, "assigned_users", None)
    auditores = list(auditores_qs.all()) if auditores_qs else []
    auditor_nombre = ", ".join(n for n in (_nombre(u) for u in auditores) if n)

    jefe_nombre = _nombre(audit.audit_manager)

    if not auditor_nombre:
        # Auditor individual: sus datos vienen de su propio acceso
        auditor_nombre = _nombre(usuario) or jefe_nombre

    return auditor_nombre or "Sin asignar", jefe_nombre or "Sin asignar"


@login_required
@require_GET
def generar_documento_modal(request, audit_id):
    audit = get_audit_for_user_or_404(
        request.user, audit_id, action="view", module="workpapers"
    )

    _get_requested_audit_type(request, audit)

    # Datos tomados del acceso del usuario (auditor individual o en grupo)
    auditor_nombre, supervisor_nombre = nombres_auditor_y_jefe(
        audit, getattr(request, "user", None))

    html = render_to_string(
        "auditoria/modals/generar_documento_modal.html",
        {
            "audit": audit,
            "auditor_nombre": auditor_nombre,
            "supervisor_nombre": supervisor_nombre,
        },
        request=request,
    )
    return JsonResponse({"html": html})


@login_required
@require_GET
def obtener_carpetas_auditoria(request, audit_id):
    """
    Devuelve todas las carpetas y subcarpetas del tipo de auditoría (Financiera o Interna),
    leyendo desde static/templates_base_financiera o static/templates_base_interna.
    Se devuelven en orden descendente según su número inicial.
    """

    audit = get_audit_for_user_or_404(
        request.user, audit_id, action="view", module="workpapers"
    )

    # Selecciona la carpeta base según el tipo de auditoría
    audit_type = _get_requested_audit_type(request, audit)
    if audit_type == 'I':
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')
    elif audit_type == 'R':
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_revisoria')
    else:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')

    if not os.path.exists(base_path):
        return JsonResponse({"error": "Carpeta de plantillas no encontrada"}, status=404)

    carpetas = []

    # Recorrer carpetas y subcarpetas recursivamente
    for root, dirs, files in os.walk(base_path):
        # Obtener el nombre de la carpeta actual relativa a la base
        for d in dirs:
            relative_path = os.path.relpath(os.path.join(root, d), base_path)
            carpetas.append(relative_path.replace("\\", "/"))  # formato limpio compatible

    # Función auxiliar para extraer número de carpeta
    def extraer_numero(nombre):
        partes = nombre.split(" ", 1)
        try:
            return int(partes[0])
        except (ValueError, IndexError):
            return 0

    # Ordenar por número (descendente), luego alfabéticamente
    carpetas.sort(key=lambda x: (extraer_numero(x), x.lower()), reverse=False)

    return JsonResponse({"carpetas": carpetas})

@login_required
@require_GET
def obtener_documentos_auditoria(request, audit_id, carpeta_nombre):
    """
    Devuelve los documentos (.docx y .xlsx) dentro de una carpeta seleccionada,
    ordenados numéricamente por nombre.
    """
    from urllib.parse import unquote
    import re

    audit = get_audit_for_user_or_404(
        request.user, audit_id, action="view", module="workpapers"
    )

    carpeta_nombre = unquote(carpeta_nombre)

    audit_type = _get_requested_audit_type(request, audit)
    if audit_type == 'I':
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')
    elif audit_type == 'R':
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_revisoria')
    else:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')

    carpeta_path = _safe_folder_path(base_path, carpeta_nombre)
    if not carpeta_path or not os.path.isdir(carpeta_path):
        return JsonResponse({"error": f"No se encontró la carpeta: {carpeta_nombre}"}, status=404)

    archivos = [
        f for f in os.listdir(carpeta_path)
        if os.path.isfile(os.path.join(carpeta_path, f)) and f.lower().endswith(('.docx', '.xlsx', '.xlsm'))
    ]

    # 🔢 Ordenar numéricamente por prefijo
    def num_key(nombre):
        match = re.match(r'^(\d+(?:\.\d+)?)', nombre)
        return float(match.group(1)) if match else float('inf')

    archivos.sort(key=num_key)

    return JsonResponse({"documentos": archivos})


# ==========================================================
# 🔸 Sub-funciones auxiliares
# ==========================================================


def _inyectar_datos_auditor_jefe(wb, auditor_nombre, supervisor_nombre,
                                 fecha_elaboracion, fecha_aprobacion):
    """
    Plantillas 2026: los papeles nuevos no traen etiquetas [NOMBRE_AUDITOR] /
    [FECHA_ELABORACION]; en su lugar tienen un bloque de encabezado con las
    celdas "Elaboro"/"Reviso" (y "Fecha" debajo). Esta función localiza esas
    celdas ancla y escribe el dato en la celda contigua derecha, solo si está
    vacía (no pisa datos existentes).

    Cada plantilla rotula ese bloque a su manera —"Elaboro"/"Reviso" en unas y
    "Hecho por"/"Revisado por" en las nuevas cédulas sumarias—, así que se
    reconocen todas las variantes para que los datos peguen en TODAS las
    plantillas, como pidió el cliente.
    """
    import unicodedata

    def _norm(v):
        s = unicodedata.normalize("NFD", str(v))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.strip().rstrip(":").strip().lower()

    # etiqueta del papel -> (nombre a escribir, fecha del bloque)
    datos_auditor = (auditor_nombre, fecha_elaboracion)
    datos_jefe = (supervisor_nombre, fecha_aprobacion)
    objetivos = {
        # variantes del bloque del auditor
        "elaboro": datos_auditor,
        "elaborado por": datos_auditor,
        "hecho por": datos_auditor,
        "preparado por": datos_auditor,
        # variantes del bloque del jefe / supervisor
        "reviso": datos_jefe,
        "revisado por": datos_jefe,
        "aprobado por": datos_jefe,
    }
    # Etiquetas sueltas: las hojas de Revisoría (K-1, K-2...) rotulan el recuadro
    # como "Auditor" y "Supervisor". Se aceptan SOLO cuando forman parte de un
    # recuadro de identificación (hay una etiqueta 'Fecha ...' a un par de filas),
    # porque esas mismas palabras aparecen dentro del texto de los cuestionarios.
    sueltas = {"auditor": datos_auditor, "supervisor": datos_jefe}
    # Fechas con nombre propio dentro del recuadro
    fechas_sueltas = {
        "fecha elaboracion": fecha_elaboracion,
        "fecha de elaboracion": fecha_elaboracion,
        "fecha aprobacion": fecha_aprobacion,
        "fecha de aprobacion": fecha_aprobacion,
        "fecha revision": fecha_aprobacion,
        "fecha de revision": fecha_aprobacion,
    }

    def _celda_escribible(sh, fila, columna, origen=None):
        """
        Celda donde SÍ se puede escribir en (fila, columna).

        Si la celda pertenece a un rango combinado se devuelve su ancla, que es
        la que Excel muestra; escribir en cualquier otra reventaba con
        «'MergedCell' object attribute 'value' is read-only» y la descarga
        devolvía error 500. Devuelve None si el ancla es la propia etiqueta
        (`origen`) o no hay dónde escribir.
        """
        from openpyxl.cell.cell import MergedCell

        celda = sh.cell(row=fila, column=columna)
        if not isinstance(celda, MergedCell):
            return celda

        for rango in sh.merged_cells.ranges:
            if (rango.min_row <= fila <= rango.max_row
                    and rango.min_col <= columna <= rango.max_col):
                ancla = sh.cell(row=rango.min_row, column=rango.min_col)
                if origen is not None and ancla.coordinate == origen.coordinate:
                    return None
                return ancla
        return None

    def _es_recuadro(sh, cell):
        """True si alrededor de la celda hay una etiqueta de fecha del recuadro."""
        for delta in (-3, -2, -1, 1, 2, 3):
            fila = cell.row + delta
            if fila < 1:
                continue
            vecino = sh.cell(row=fila, column=cell.column).value
            if isinstance(vecino, str) and _norm(vecino).startswith("fecha"):
                return True
        return False
    # Cada hoja del libro es un papel de trabajo por sí misma (ÍNDICE, K-1,
    # K-2...), así que se recorren TODAS y la que no tenga recuadro recibe uno.
    for sh in wb.worksheets:
        if _hoja_sin_contenido(sh):
            continue
        escrito = False
        max_row = min(sh.max_row or 1, 40)
        max_col = min(sh.max_column or 1, 24)
        for row in sh.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                clave = _norm(cell.value)

                # Etiqueta de fecha con nombre propio ('Fecha Elaboración')
                if clave in fechas_sueltas:
                    destino = _celda_escribible(sh, cell.row, cell.column + 1, cell)
                    valor = fechas_sueltas[clave]
                    if valor and destino is not None and destino.value in (None, ""):
                        destino.value = valor
                        escrito = True
                    continue

                if clave in sueltas:
                    if not _es_recuadro(sh, cell):
                        continue
                    nombre, fecha = sueltas[clave]
                elif clave in objetivos:
                    nombre, fecha = objetivos[clave]
                else:
                    continue

                destino = _celda_escribible(sh, cell.row, cell.column + 1, cell)
                if destino is not None and destino.value in (None, ""):
                    destino.value = nombre
                    escrito = True
                # "Fecha" en la fila siguiente del mismo bloque
                abajo = sh.cell(row=cell.row + 1, column=cell.column)
                if isinstance(abajo.value, str) and _norm(abajo.value) == "fecha":
                    destino_fecha = _celda_escribible(
                        sh, cell.row + 1, cell.column + 1, abajo)
                    if fecha and destino_fecha is not None and destino_fecha.value in (None, ""):
                        destino_fecha.value = fecha

        if not escrito:
            _crear_bloque_auditor_jefe(sh, auditor_nombre, supervisor_nombre,
                                       fecha_elaboracion, fecha_aprobacion)


def _hoja_sin_contenido(sh):
    """True si la hoja está vacía (no se le agrega el recuadro)."""
    if (sh.max_row or 0) <= 1 and (sh.max_column or 0) <= 1:
        return sh.cell(row=1, column=1).value in (None, "")
    return False


def _crear_bloque_auditor_jefe(hoja, auditor_nombre, supervisor_nombre,
                               fecha_elaboracion, fecha_aprobacion):
    """
    Crea el bloque Elaboró / Revisó en una hoja que no lo trae.

    Varias plantillas (sobre todo las de Revisoría Fiscal) no tienen todavía el
    recuadro de identificación, así que sin esto los datos del auditor no
    llegaban a esas cédulas. Se escribe en columnas libres a la derecha del
    contenido, sin pisar nada de la plantilla.
    """
    from openpyxl.styles import Font

    filas = [
        ("Elaboro:", auditor_nombre),
        ("Fecha:", fecha_elaboracion),
        ("Reviso:", supervisor_nombre),
        ("Fecha:", fecha_aprobacion),
    ]
    columna = _columna_libre_para_bloque(hoja, primera_fila=2,
                                         alto=len(filas), ancho=2)
    if not columna:
        return

    for desplazamiento, (etiqueta, valor) in enumerate(filas):
        fila = 2 + desplazamiento
        celda_etiqueta = hoja.cell(row=fila, column=columna)
        celda_valor = hoja.cell(row=fila, column=columna + 1)
        celda_etiqueta.value = etiqueta
        celda_etiqueta.font = Font(bold=True)
        celda_valor.value = valor or ""
    hoja.column_dimensions[hoja.cell(row=2, column=columna).column_letter].width = 14
    hoja.column_dimensions[hoja.cell(row=2, column=columna + 1).column_letter].width = 26


def _columna_libre_para_bloque(hoja, primera_fila, alto, ancho):
    """
    Primera columna a la derecha del contenido donde caben `alto` x `ancho`
    celdas libres, o None si no la hay.

    Antes se usaba `min(max_column + 2, 24)` a ciegas: ese tope caía dentro de
    un rango combinado en varias plantillas y la descarga reventaba con
    «'MergedCell' object attribute 'value' is read-only», así que el botón
    «Datos Auditor y Jefe» devolvía error 500 y no bajaba nada.
    """
    from openpyxl.cell.cell import MergedCell

    inicio = (hoja.max_column or 1) + 2
    for columna in range(inicio, inicio + 12):
        if columna + ancho - 1 > 16384:          # límite de columnas de Excel
            return None
        libre = True
        for fila in range(primera_fila, primera_fila + alto):
            for desplazamiento in range(ancho):
                celda = hoja.cell(row=fila, column=columna + desplazamiento)
                if isinstance(celda, MergedCell) or celda.value not in (None, ""):
                    libre = False
                    break
            if not libre:
                break
        if libre:
            return columna
    return None


def _apply_word_replacements(file_path, replacements):
    """Abre el archivo Word, aplica los reemplazos y devuelve un buffer."""
    doc = Document(file_path)

    # Reemplazo en párrafos
    for p in doc.paragraphs:
        for key, value in replacements.items():
            if key in p.text:
                p.text = p.text.replace(key, value)

    # Reemplazo en tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in replacements.items():
                    if key in cell.text:
                        cell.text = cell.text.replace(key, value)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer



# ==========================================================
# 🔸 FUNCIÓN PRINCIPAL
# ==========================================================
@login_required
@require_GET
def descargar_documento_auditoria(request, audit_id):
    """Descarga el documento ya automatizado con reemplazos, datos importados y etiquetas personalizadas."""

    from auditoria.word_utils import modify_document_word  # ✅ usamos su automatización oficial

    # -------------------- helpers SOLO para fechas --------------------
    # (no tocan lo que ya funciona; actúan después como “pasada extra”)
    from docx.oxml.ns import qn

    def _replace_wt_spanning_tokens(container, token: str, value: str):
        """
        Reemplaza `token` aunque esté dividido en varios <w:t>.
        Conserva el formato fuera del token. El texto resultante del token
        quedará con el formato del primer <w:t> del grupo (lo típico en firmas).
        """
        t_nodes = container._element.xpath('.//w:t')
        if not t_nodes:
            return

        # 1) Reemplazos directos dentro de un solo w:t
        for t in t_nodes:
            if t.text and token in t.text:
                t.text = t.text.replace(token, value)

        # 2) Si aún queda el token, probar en ventanas de 2 y 3 nodos contiguos
        #    (suele ser el caso más común en estas plantillas)
        def replace_in_window(win_size: int):
            i = 0
            while i <= len(t_nodes) - win_size:
                parts = [(t_nodes[i+k].text or '') for k in range(win_size)]
                joined = ''.join(parts)
                if token in joined:
                    new_joined = joined.replace(token, value)

                    # Redistribuir el nuevo texto en los mismos nodos (manteniendo estructura)
                    remaining = new_joined
                    for k in range(win_size):
                        original = parts[k]
                        take = min(len(original), len(remaining))
                        t_nodes[i+k].text = remaining[:take]
                        remaining = remaining[take:]
                    if remaining:
                        # si sobró (pasa cuando value es más largo que el token original),
                        # lo añadimos al último nodo de la ventana
                        t_nodes[i+win_size-1].text = (t_nodes[i+win_size-1].text or '') + remaining
                i += 1

        # ventanas de 2 y 3 nodos
        replace_in_window(2)
        replace_in_window(3)



    # -----------------------------------------------------------------

    # Obtener la auditoría
    audit = get_audit_for_user_or_404(
        request.user, audit_id, action="view", module="workpapers"
    )

    carpeta = request.GET.get("carpeta")
    documento = request.GET.get("documento")

    if not carpeta or not documento:
        return JsonResponse({"error": "Faltan parámetros."}, status=400)

    # Determinar ruta
    audit_type = _get_requested_audit_type(request, audit)
    file_path = _safe_template_path(audit, carpeta, documento, audit_type=audit_type)
    if not file_path or not os.path.isfile(file_path):
        return JsonResponse({"error": "El archivo no existe."}, status=404)

    # --- Fechas ---
    def _fmt_ddmmyyyy(date_str):
        if not date_str:
            return ""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
        except Exception:
            return date_str

    fecha_elaboracion = _fmt_ddmmyyyy(request.GET.get("fecha_elaboracion"))
    fecha_aprobacion  = _fmt_ddmmyyyy(request.GET.get("fecha_aprobacion"))

    # --- Reemplazos base ---
    replacements_config = get_replacements_config()
    fecha_inicio = audit.fechaInit.strftime("%d-%m-%Y") if audit.fechaInit else ""
    fecha_fin    = audit.fechaEnd.strftime("%d-%m-%Y") if audit.fechaEnd else ""
    replacements = build_replacements_dict(replacements_config, audit, fecha_inicio, fecha_fin)

    # --- Reemplazos personalizados tuyos ---
    auditor_nombre, supervisor_nombre = nombres_auditor_y_jefe(
        audit, getattr(request, "user", None))

    replacements["[NOMBRE_AUDITOR]"]    = auditor_nombre
    replacements["[NOMBRE_SUPERVISOR]"] = supervisor_nombre
    replacements["[FECHA_ELABORACION]"] = fecha_elaboracion or ""
    replacements["[FECHA_APROBACION]"]  = fecha_aprobacion or ""

    # --- Detectar tipo de archivo ---
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".docx":
        try:
            # 🧩 Paso 1: automatización oficial (tu lógica actual)
            doc = modify_document_word(file_path, audit)

            # 🧩 Paso 2: aplicar tus reemplazos (igual que tenías, preservando formato)
            # EXCEPTO los que ahora haremos robustos: fechas Y nombres
            ROBUST_TAGS = ["[FECHA_ELABORACION]", "[FECHA_APROBACION]", "[NOMBRE_AUDITOR]", "[NOMBRE_SUPERVISOR]"]
            
            replacements_filtrados = {
                k: v for k, v in replacements.items()
                if (not any(header in k for header in ["Entidad:", "Auditoría:", "Período:"]))
                and (k not in ROBUST_TAGS)
            }

            # Reemplazo por run (lo que ya tienes y funciona para el resto)
            for p in doc.paragraphs:
                for run in p.runs:
                    for key, value in replacements_filtrados.items():
                        if key in run.text:
                            run.text = run.text.replace(key, value)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            for run in p.runs:
                                for key, value in replacements_filtrados.items():
                                    if key in run.text:
                                        run.text = run.text.replace(key, value)

            # 🧩 Paso 3: **pasada robusta PARA TODOS LOS TAGS CRÍTICOS** (cubre tokens partidos en varios w:t)
            def _replace_tags_everywhere(doc, tags_map: dict):
                """
                Aplica _replace_wt_spanning_tokens a todo el documento para las etiquetas dadas.
                """
                # Párrafos
                for p in doc.paragraphs:
                    for tag, val in tags_map.items():
                        # Chequeo rápido antes de procesar XML
                        if tag in ''.join(run.text or '' for run in p.runs) or any(tag in (t.text or '') for t in p._element.xpath('.//w:t')):
                            _replace_wt_spanning_tokens(p, tag, val)

                # Tablas
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                for tag, val in tags_map.items():
                                    if tag in ''.join(run.text or '' for run in p.runs) or any(tag in (t.text or '') for t in p._element.xpath('.//w:t')):
                                        _replace_wt_spanning_tokens(p, tag, val)

            _replace_tags_everywhere(doc, {
                "[FECHA_ELABORACION]": replacements.get("[FECHA_ELABORACION]", ""),
                "[FECHA_APROBACION]":  replacements.get("[FECHA_APROBACION]",  ""),
                "[NOMBRE_AUDITOR]":    replacements.get("[NOMBRE_AUDITOR]",    ""),
                "[NOMBRE_SUPERVISOR]": replacements.get("[NOMBRE_SUPERVISOR]", ""),
            })

            # 🧩 Paso 3c: MARCAS DE AUDITORÍA.
            # Sin esto, al generar el documento con los datos del auditor se
            # perdían las marcas que ya se habían cargado y verificadas en la
            # cédula: los datos llegaban pero la marca desaparecía.
            try:
                from auditoria.services.audit_mark_processor import AuditMarkProcessor
                doc = AuditMarkProcessor(audit.id, documento).process_word_document(doc)
            except Exception as e:
                print(f"Aviso: no se pudieron aplicar las marcas en {documento}: {e}")

            # 🧩 Referencia al final: ningún procesador posterior debe
            # restaurar el código de ejemplo de la plantilla.
            try:
                from auditoria.services.referencias import obtener_ref, inyectar_ref_propia_word
                ref_propia = obtener_ref(audit_type, carpeta, documento, audit_id=audit.id)
                if ref_propia:
                    doc = inyectar_ref_propia_word(doc, ref_propia)
            except Exception as e:
                print(f"Aviso: no se pudo inyectar la referencia en {documento}: {e}")

            # 🧩 Paso 4: guardar en buffer
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"Error procesando el documento Word: {str(e)}"}, status=500)

    elif ext in [".xlsx", ".xlsm"]:
        # ✅ Excel: lo de siempre (sin cambios)
        from auditoria.views.download_views import modify_document_excel, modify_document_excel_with_macros

        if ext == ".xlsm":
            processed_path = modify_document_excel_with_macros(file_path, audit)
            wb = load_workbook(processed_path, keep_vba=True)

            for sh in wb.worksheets:
                for row in sh.iter_rows():
                    for cell in row:
                        if isinstance(cell.value, str):
                            v = cell.value
                            for k, val in replacements.items():
                                if k in v:
                                    v = v.replace(k, val)
                            cell.value = v

            bio = BytesIO()
            wb.save(bio)
            bio.seek(0)
            buffer = bio
            content_type = "application/vnd.ms-excel.sheet.macroEnabled.12"

        else:
            wb = modify_document_excel(file_path, audit)
            # Preservar el procesamiento dinámico propio de Revisoría del
            # sistema actualizado (también cuando se usa el nuevo modal).
            from auditoria.views.download_views import _apply_revisoria_dynamic_content
            wb = _apply_revisoria_dynamic_content(wb, audit, documento)
            for sh in wb.worksheets:
                for row in sh.iter_rows():
                    for cell in row:
                        if isinstance(cell.value, str):
                            v = cell.value
                            for k, val in replacements.items():
                                if k in v:
                                    v = v.replace(k, val)
                            cell.value = v

            # Plantillas 2026 sin etiquetas: escribir Auditor/Jefe y fechas
            # junto a las celdas ancla "Elaboro"/"Reviso".
            _inyectar_datos_auditor_jefe(
                wb, auditor_nombre, supervisor_nombre,
                fecha_elaboracion, fecha_aprobacion,
            )

            # MARCAS DE AUDITORÍA: se aplican también aquí para que el papel
            # descargado traiga JUNTOS los datos del auditor y sus marcas.
            try:
                from auditoria.services.audit_mark_processor import AuditMarkProcessor
                wb = AuditMarkProcessor(audit.id, documento).process_excel_document(wb)
            except Exception as e:
                print(f"Aviso: no se pudieron aplicar las marcas en {documento}: {e}")

            # Insertar la Ref. del encabezado después de marcas y cambios dinámicos.
            try:
                from auditoria.services.referencias import obtener_ref, inyectar_ref_propia
                # audit_id es necesario para respetar la referencia que el
                # auditor fijó a mano; sin él siempre ganaba la automática.
                ref_propia = obtener_ref(audit_type, carpeta, documento, audit_id=audit.id)
                if ref_propia:
                    wb = inyectar_ref_propia(wb, ref_propia)
            except Exception:
                logger.exception(
                    "No se pudo inyectar la referencia en Excel %s de auditoría %s",
                    documento, audit.id,
                )

            bio = BytesIO()
            wb.save(bio)
            bio.seek(0)
            buffer = bio
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    else:
        return JsonResponse({"error": "Formato de archivo no soportado."}, status=400)

    # --- Respuesta final ---
    response = HttpResponse(buffer, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{documento}"'
    return response
