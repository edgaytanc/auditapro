"""Archivos derivados del flujo: 5.5.3 Revision_Hallazgos, 5.5.4 Hallazgos_Finales, borrador del informe de Auditoría Interna
y la sección 7 de la hoja R-3 de Revisoría Fiscal. Se regeneran desde el estado del sistema (idempotente)."""
from __future__ import annotations

import re
from copy import copy
from datetime import date

from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

from ..engine import sheet_rows
from . import config
from .xl import _copy_style, _get, _set, _validacion, norm

NOMBRE_SEV_AI = {"Crítica": "Crítico", "Alta": "Alto", "Media": "Medio", "Baja": "Bajo"}
RIESGO_FINAL = {"Crítica": "Alto", "Alta": "Alto", "Media": "Medio", "Baja": "Bajo"}
COLOR_SEV = {"Crítica": "C00000", "Alta": "FF4500", "Media": "B8860B", "Baja": "2E7D32"}


def _filas_tabla(ws, hdr: int, key_col: int = 1, fin_marker: str = "Firma:") -> tuple[int, int]:
    """Primera y última fila de datos de una tabla simple que termina antes de la fila «Firma:»."""
    fin = next((r for r in range(hdr + 1, ws.max_row + 1) if str(_get(ws, r, 1) or "").strip() == fin_marker), ws.max_row + 1)
    return hdr + 1, fin - 1


def _hoja(wb, fragmento: str):
    for ws in wb.worksheets:
        if fragmento in norm(ws.title):
            return ws
    raise LookupError(f"No se encontró la hoja «{fragmento}».")


def _asegurar_filas(wb, ws, first: int, last: int, n: int, ancho: int) -> int:
    """Garantiza ``n`` filas de datos entre ``first`` y ``last`` insertando antes de la última (el formato se copia)."""
    cap = last - first + 1
    if n > cap:
        extra = n - cap
        sheet_rows.insert_rows(wb, ws, last, extra)
        for k in range(extra):
            sheet_rows.copy_row_format(ws, last + extra, last + k, ancho, formulas=False)
        last += extra
    return last


def _limpiar(ws, first: int, last: int, cols: range) -> None:
    for r in range(first, last + 1):
        for c in cols:
            cell = ws.cell(r, c)
            if not isinstance(cell, MergedCell):
                cell.value = None


def _wrap(ws, row: int, col: int) -> None:
    ws.cell(row, col).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)


def _altura(ws, row: int, textos: dict[int, str], minimo: float = 30) -> None:
    mejor = minimo
    for col, t in textos.items():
        ancho = ws.column_dimensions[get_column_letter(col)].width or 16
        lineas = sum(max(1, -(-len(p) // max(int(ancho * 1.05), 6))) for p in str(t or "").split("\n"))
        mejor = max(mejor, min(lineas * 12.5 + 6, 400))
    ws.row_dimensions[row].height = mejor


def _monto(h) -> str:
    return f"{h.monto:,.2f}" if h.monto is not None else ""


# ----------------------------------------------------------------------------- 5.5.3 Revisión de hallazgos (Financiera)
def llenar_revision(wb, items: list, *, cuenta_nombre, evidencias_de, ref_origen, decision_de, ctx) -> int:
    """Hoja «Registro de Hallazgos» (+ «Plan de Acción»). Agrega las columnas de revisión que pide la guía (sección 6)."""
    ws = _hoja(wb, "registro de hallazgos")
    hdr = 4
    first, last = _filas_tabla(ws, hdr)
    last = _asegurar_filas(wb, ws, first, last, len(items), 21)
    nuevas = ["Ref. origen", "Clasificación", "Monto asociado", "Evidencias", "Decisión del Jefe", "Comentario del Jefe", "Revisó / Fecha"]
    for j, t in enumerate(nuevas):
        col = 15 + j  # O..U (L queda libre; M:N es el bloque «Revisado por»)
        _copy_style(ws.cell(hdr, 11), ws.cell(hdr, col))
        ws.cell(hdr, col).value = t
        ws.column_dimensions[get_column_letter(col)].width = 28 if j in (3, 5) else 18
        for r in range(first, last + 1):
            _copy_style(ws.cell(r, 2), ws.cell(r, col))
    _limpiar(ws, first, last, range(1, 22))
    for i, h in enumerate(items):
        r = first + i
        dec, coment, quien = decision_de(h)
        vals = {
            1: h.ref_local or f"H-{i + 1:02d}", 2: h.condicion, 3: h.criterio, 4: h.causa, 5: h.efecto, 6: h.recomendacion,
            7: cuenta_nombre(h), 8: h.responsable, 9: h.creado_en.date(), 10: h.severidad if h.severidad != "Crítica" else "Alta",
            11: config.ETIQUETA_ESTADO.get(h.estado, h.estado),
            15: ref_origen(h), 16: h.clasificacion, 17: float(h.monto) if h.monto is not None else None,
            18: "; ".join(evidencias_de(h)), 19: dec, 20: coment, 21: quien,
        }
        for col, v in vals.items():
            _set(ws, r, col, v)
        ws.cell(r, 9).number_format = "dd/mm/yyyy"
        ws.cell(r, 17).number_format = "#,##0.00"
        if h.severidad == "Crítica":
            ws.cell(r, 12).value = None
        for col in (2, 3, 4, 5, 6, 18, 20):
            _wrap(ws, r, col)
        _altura(ws, r, {2: h.condicion, 3: h.criterio, 4: h.causa, 5: h.efecto, 6: h.recomendacion}, 45)
    _validacion(ws, f"J{first}:J{last}", ",".join(config.SEVERIDADES))
    _validacion(ws, f"K{first}:K{last}", config.ESTADOS_PLANTILLA)
    _validacion(ws, f"S{first}:S{last}", "Aprobado,Devuelto,Rechazado")
    _plan_accion(wb, items)
    _corner(wb, ctx)
    return last


def _plan_accion(wb, items: list) -> None:
    try:
        ws = _hoja(wb, "plan de accion")
    except LookupError:
        return
    first, last = _filas_tabla(ws, 4)
    last = _asegurar_filas(wb, ws, first, last, len(items), 8)
    _limpiar(ws, first, last, range(1, 6))
    for i, h in enumerate(items):
        r = first + i
        for col, v in {1: h.ref_local or f"H-{i + 1:02d}", 2: h.recomendacion, 3: h.responsable, 4: h.fecha_seguimiento, 5: "Pendiente"}.items():
            _set(ws, r, col, v)
        ws.cell(r, 4).number_format = "dd/mm/yyyy"
        _wrap(ws, r, 2)
        _altura(ws, r, {2: h.recomendacion}, 30)


def _corner(wb, ctx: dict) -> None:
    """«Hecho por / Revisado por» de cada hoja: usuario y fecha del sistema."""
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=1, max_row=8):
            for c in row:
                v = str(c.value or "")
                if v.startswith("Hecho por") and ctx.get("elaboro"):
                    nxt = ws.cell(c.row, c.column + 1)
                    if not isinstance(nxt, MergedCell):
                        nxt.value = ctx["elaboro"]
                elif v.startswith("Revisado por") and ctx.get("reviso"):
                    nxt = ws.cell(c.row, c.column + 1)
                    if not isinstance(nxt, MergedCell):
                        nxt.value = ctx["reviso"]
                elif v.startswith("Fecha") and ctx.get("fecha"):
                    nxt = ws.cell(c.row, c.column + 1)
                    if not isinstance(nxt, MergedCell) and nxt.value in (None, ""):
                        nxt.value = ctx["fecha"]


# ----------------------------------------------------------------------------- 5.5.4 Hallazgos finales (Financiera)
def llenar_finales(wb, items: list, *, cuenta_nombre, ctx) -> None:
    """Solo los aprobados, con numeración HF-nn ya asignada (por severidad y luego por cuenta)."""
    ws = _hoja(wb, "registro hallazgos finales")
    first, last = _filas_tabla(ws, 4)
    last = _asegurar_filas(wb, ws, first, last, len(items), 13)
    _limpiar(ws, first, last, range(1, 14))
    for i, h in enumerate(items):
        r = first + i
        vals = {1: h.ref_hf, 2: h.titulo, 3: cuenta_nombre(h), 4: h.criterio, 5: h.condicion, 6: h.causa, 7: h.efecto,
                8: RIESGO_FINAL.get(h.severidad, "Medio"), 9: h.recomendacion, 10: h.respuesta_administracion or None,
                11: h.responsable or None, 12: h.fecha_seguimiento, 13: "Abierto"}
        for col, v in vals.items():
            _set(ws, r, col, v)
        ws.cell(r, 12).number_format = "dd/mm/yyyy"
        for col in (2, 4, 5, 6, 7, 9, 10):
            _wrap(ws, r, col)
        _altura(ws, r, {2: h.titulo, 4: h.criterio, 5: h.condicion, 6: h.causa, 7: h.efecto, 9: h.recomendacion}, 45)
    _validacion(ws, f"H{first}:H{last}", "Alto,Medio,Bajo")
    _validacion(ws, f"M{first}:M{last}", "Abierto,Cerrado,En Proceso")
    # Portada: nombre del auditor, supervisor, fechas
    try:
        p = _hoja(wb, "portada")
    except LookupError:
        p = None
    if p is not None:
        for r in range(1, 14):
            for c in range(1, 12):
                v = str(p.cell(r, c).value or "")
                if isinstance(p.cell(r, c), MergedCell):
                    continue
                if v.startswith("Nombre del Auditor") and ctx.get("elaboro"):
                    p.cell(r, c).value = f"Nombre del Auditor: {ctx['elaboro']}"
                elif v.startswith("Supervisor") and ctx.get("reviso"):
                    p.cell(r, c).value = f"Supervisor: {ctx['reviso']}"
                elif v.startswith("Cliente/Entidad Auditada") and ctx.get("entidad"):
                    p.cell(r, c).value = f"Cliente/Entidad Auditada: {ctx['entidad']}"
                elif v.startswith("Fecha de Revisión") and ctx.get("fecha"):
                    p.cell(r, c).value = f"Fecha de Revisión: {ctx['fecha']}"
    _corner(wb, ctx)


# ----------------------------------------------------------------------------- Borrador del informe (Auditoría Interna)
SEV_BORRADOR_FILA_INICIAL = 13


def llenar_borrador(wb, items: list, *, area_texto, ctx, usuario: str, fecha_envio: date) -> dict:
    """AI-INF-04-A Comentarios: código, título, severidad, hallazgo original, fecha de envío y responsable de cada hallazgo."""
    ws = _hoja(wb, "comentarios")
    hdr = 12
    first = 13
    ultima = next((r for r in range(first, ws.max_row + 1) if str(_get(ws, r, 1) or "").strip() == "Firma:"), ws.max_row) - 1
    # el último renglón de la tabla es el anterior a la zona de firmas (la plantilla deja filas de reserva: 13..43)
    last = 43 if ultima > 43 else ultima
    cap = last - first + 1
    if len(items) > cap:
        extra = len(items) - cap
        sheet_rows.insert_rows(wb, ws, last, extra)
        for k in range(extra):
            sheet_rows.copy_row_format(ws, last + extra, last + k, 19, formulas=True)
        last += extra
    texto_cols = [1, 2, 3, 4, 5, 6, 7, 10, 12, 13, 19]
    for r in range(first, last + 1):
        for c in (1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 15, 18, 19):
            cell = ws.cell(r, c)
            if not isinstance(cell, MergedCell):
                cell.value = None
    for i, h in enumerate(items):
        r = first + i
        _set(ws, r, 1, h.ref_local or f"H-{i + 1:02d}")
        _set(ws, r, 2, h.titulo)
        _set(ws, r, 3, NOMBRE_SEV_AI.get(h.severidad, "Medio"))
        _set(ws, r, 4, h.condicion)
        _set(ws, r, 5, fecha_envio)
        ws.cell(r, 5).number_format = "dd/mm/yyyy"
        _set(ws, r, 6, h.responsable or "Por asignar")
        _set(ws, r, 19, area_texto(h))
        for c in (2, 4, 19):
            _wrap(ws, r, c)
        _altura(ws, r, {2: h.titulo, 4: h.condicion}, 45)
    _validacion(ws, f"C{first}:C{last}", "Crítico,Alto,Medio,Bajo")
    # Control de versiones: una fila por envío
    cv = _hoja(wb, "control versiones")
    vfirst = 13
    vr = vfirst
    while _get(cv, vr, 1) not in (None, ""):
        vr += 1
    return {"hoja": ws.title, "primera": first, "ultima": first + len(items) - 1, "version_fila": vr, "control": cv}


def registrar_version_borrador(cv, fila: int, *, numero: int, descripcion: str, agregados: int, usuario: str, fecha: date) -> None:
    for col, v in {1: f"{numero}.0", 2: fecha, 3: descripcion, 4: 0, 5: 0, 6: agregados, 7: 0, 8: usuario, 9: "Jefe de Auditoría", 10: "Borrador"}.items():
        _set(cv, fila, col, v)
    cv.cell(fila, 2).number_format = "dd/mm/yyyy"
    if fila > 13:
        for c in range(1, 11):
            _copy_style(cv.cell(13, c), cv.cell(fila, c))


# ----------------------------------------------------------------------------- Revisoría: hoja R-3, sección 7
class R3Error(Exception):
    pass


def _ancho_texto(ws, c1: int = 1, c2: int = 8) -> float:
    return sum((ws.column_dimensions[get_column_letter(c)].width or 8.43) for c in range(c1, c2 + 1))


def _lineas_r3(h, rs: dict, ref_ev: str) -> list[tuple[str, str, bool]]:
    """[(texto, tipo, negrita)] de cada hallazgo en R-3 (guía, 6.2). tipo: 'titulo' | 'campo' | 'blanco' | 'sep'."""
    plazo = h.fecha_seguimiento.strftime("%d/%m/%Y") if h.fecha_seguimiento else "Por definir"
    out = [(f"HALLAZGO {rs['n']} [{h.severidad.upper()}]: {h.titulo}", "titulo", True)]
    for etiqueta, valor in (("Condición", h.condicion), ("Criterio", h.criterio), ("Causa", h.causa), ("Efecto", h.efecto),
                            ("Recomendación", h.recomendacion), ("Responsable", h.responsable or "Por asignar"), ("Plazo", plazo)):
        out.append((f"{etiqueta}: {valor}", "campo", False))
    out.append((ref_ev, "campo", False))
    out.append(("", "blanco", False))
    return out


def escribir_r3(wb, hallazgos: list, *, evidencias_texto) -> dict:
    """Reemplaza el bloque amarillo de la sección 7 por los hallazgos aprobados. No toca otras secciones ni hojas.

    * El bloque generado lleva el nombre definido ``HALLAZGOS_R3``: al regenerar se reescribe ese rango (sin duplicar).
    * Si el auditor ya escribió texto propio en la sección, no se borra: lo generado va debajo.
    * Las filas necesarias se insertan debajo del encabezado; la sección 8 y siguientes bajan con su formato.
    """
    if config.HOJA_R3 not in wb.sheetnames:
        raise R3Error("El libro no tiene la hoja R-3.")
    ws = wb[config.HOJA_R3]
    enc = next((r for r in range(1, ws.max_row + 1)
                if str(_get(ws, r, 1) or "").upper().startswith(config.ENCABEZADO_R3_SECCION7)), None)
    if enc is None:
        raise R3Error("No se encontró la sección «7. HALLAZGOS Y RECOMENDACIONES» en R-3.")
    sig = next((r for r in range(enc + 1, ws.max_row + 1)
                if re.match(r"^\d+\.\s", str(_get(ws, r, 1) or "")) and ws.cell(r, 1).font.b), ws.max_row + 1)
    nombre = wb.defined_names.get(config.NOMBRE_BLOQUE_R3)
    region = None
    if nombre is not None:
        m = re.search(r"\$A\$(\d+):\$H\$(\d+)", nombre.attr_text or "")
        if m:
            region = (int(m.group(1)), int(m.group(2)))
    propio = False
    if region is not None:
        ini_gen, avail = region[0], region[1] - region[0] + 1
    else:
        texto = str(_get(ws, enc + 1, 1) or "").strip()
        if texto and texto != "[Desarrollar contenido de la sección]":
            propio, ini_gen, avail = True, sig, 0  # texto del auditor: se conserva, lo generado va debajo
        else:
            ini_gen, avail = enc + 1, max(sig - 2 - enc, 1)  # el bloque amarillo (hasta la fila en blanco previa)
    filas: list[tuple[str, str, bool]] = []
    cuenta: dict[str, int] = {}
    for h in hallazgos:
        cuenta[h.severidad] = cuenta.get(h.severidad, 0) + 1
    if hallazgos:
        dist = ", ".join(f"{cuenta[a]} {a.lower()}" for a in config.SEVERIDADES if cuenta.get(a))
        filas.append((f"Se aprobaron {len(hallazgos)} hallazgo{'s' if len(hallazgos) != 1 else ''}: {dist}.", "campo", True))
        filas.append(("", "blanco", False))
        for n, h in enumerate(hallazgos, start=1):
            filas += _lineas_r3(h, {"n": n}, evidencias_texto(h))
    else:
        filas.append(("No se identificaron hallazgos que requieran comunicación.", "campo", False))
    need = len(filas)
    if need > avail:
        sheet_rows.insert_rows(wb, ws, ini_gen + avail, need - avail)
    total = max(need, avail)
    for rng in [m for m in list(ws.merged_cells.ranges)
                if m.min_row >= ini_gen and m.max_row <= ini_gen + total - 1 and m.min_col == 1 and m.max_col == 8]:
        ws.unmerge_cells(str(rng))
    ancho = _ancho_texto(ws)
    base = ws.cell(ini_gen, 1)
    fuente = base.font.name or "Calibri"
    for k in range(total):
        r = ini_gen + k
        for c in range(1, 9):
            ws.cell(r, c).value = None
            ws.cell(r, c).fill = PatternFill(fill_type=None)  # sin amarillo: ya no está «pendiente de desarrollar»
        if k < need:
            texto, tipo, neg = filas[k]
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
            color = "000000"
            if tipo == "titulo":
                sev = texto.split("[")[1].split("]")[0].capitalize() if "[" in texto else ""
                color = COLOR_SEV.get(sev, "000000")
            cell = ws.cell(r, 1)
            cell.value = texto or None
            cell.font = Font(name=fuente, size=10, bold=neg, color=color)
            cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            lineas = sum(max(1, -(-len(p) // max(int(ancho * 1.1), 10))) for p in texto.split(chr(10))) if texto else 1
            ws.row_dimensions[r].height = max(15, min(lineas * 13 + 3, 400))
        else:
            ws.row_dimensions[r].height = 3
    fin = ini_gen + total - 1
    if config.NOMBRE_BLOQUE_R3 in wb.defined_names:
        del wb.defined_names[config.NOMBRE_BLOQUE_R3]
    wb.defined_names[config.NOMBRE_BLOQUE_R3] = DefinedName(config.NOMBRE_BLOQUE_R3, attr_text=f"'{config.HOJA_R3}'!$A${ini_gen}:$H${fin}")
    return {"inicio": ini_gen, "fin": fin, "filas": need, "propio": propio}
