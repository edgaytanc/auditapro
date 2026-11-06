"""Escritura en las plantillas Excel de Hallazgos y Evidencias (guías del cliente, etapa 2).

Reglas de las guías que se cumplen aquí:
* se escribe siempre en la primera fila vacía; nunca se pisa lo que el auditor ya digitó;
* si se acaban las filas, se insertan con el mismo formato y las fórmulas se extienden (``sheet_rows.insert_rows``);
* encabezado dinámico (entidad, período, moneda, tipo de auditoría, referencias) desde el proyecto, no de texto fijo;
* se lee de vuelta lo que el auditor editó (la plantilla es la fuente de verdad desde que está en papel de trabajo).
"""
from __future__ import annotations

import re
import unicodedata
from copy import copy
from dataclasses import dataclass, field
from datetime import date, datetime

from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from ..engine import sheet_rows
from . import config

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MONEDAS = {"GTQ": "quetzales", "HNL": "lempiras", "USD": "dólares", "COP": "pesos colombianos", "MXN": "pesos mexicanos",
           "CRC": "colones", "PEN": "soles", "EUR": "euros", "SVC": "colones", "NIO": "córdobas", "PAB": "balboas"}


def norm(text) -> str:
    s = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fecha_larga(d) -> str:
    d = d.date() if isinstance(d, datetime) else d
    return f"{d.day:02d} de {MESES[d.month - 1]} de {d.year}"


# ----------------------------------------------------------------------------- encabezado dinámico
def contexto_proyecto(audit) -> dict:
    moneda = MONEDAS.get((audit.moneda or "").upper(), (audit.moneda or "").lower() or "la moneda del proyecto")
    return {
        "entidad": (audit.identidad or "").strip() or audit.title,
        "periodo": f"Del {fecha_larga(audit.fechaInit)} al {fecha_larga(audit.fechaEnd)}",
        "moneda": moneda,
        "tipo": config.NOMBRE_MODULO.get(audit.tipoAuditoria, "Auditoría"),
        "tipo_cod": audit.tipoAuditoria,
    }


_RX_ENTIDAD = re.compile(r"^\s*Entidad\b\s*(:)?", re.I)
_RX_TIPO = re.compile(r"^\s*(Auditor[ií]a|Revisor[ií]a)\s+(Financiera|Interna|Fiscal)\s*$", re.I)
_RX_PERIODO = re.compile(r"^\s*Del\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s+al\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s*$", re.I)
_RX_MONEDA = re.compile(r"cifras expresadas en [\wáéíóúñ ]+", re.I)
_RX_HERRAMIENTA = re.compile(r"Herramienta de Auditor[ií]a:.*", re.I)


def aplicar_encabezado(wb, audit, refs: dict[str, str] | None = None) -> None:
    """Entidad, período, moneda y tipo de auditoría salen del proyecto. ``refs`` = {celda: valor} por hoja «*»."""
    ctx = contexto_proyecto(audit)
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=1, max_row=12):
            for c in row:
                v = c.value
                if isinstance(c, MergedCell) or not isinstance(v, str) or v.startswith("="):
                    continue
                if _RX_ENTIDAD.match(v) and len(v) < 90 and "Entidad Auditada" not in v and "Cliente" not in v:
                    c.value = f"Entidad: {ctx['entidad']}" if ":" in v[:10] else f"Entidad {ctx['entidad']}"
                elif _RX_TIPO.match(v):
                    c.value = ctx["tipo"] + (" " if v.endswith(" ") else "")
                elif _RX_PERIODO.match(v):
                    c.value = ctx["periodo"]
                elif _RX_HERRAMIENTA.match(v):
                    c.value = re.sub(r"(Auditor[ií]a|Revisor[ií]a) (Financiera|Interna|Fiscal)( \1 \2)*", ctx["tipo"], v)
                elif _RX_MONEDA.search(v):
                    c.value = _RX_MONEDA.sub(f"cifras expresadas en {ctx['moneda']}", v)
                if ctx["tipo_cod"] == "R" and isinstance(c.value, str):
                    c.value = (c.value.replace("AUDITORÍA INTERNA", "REVISORÍA FISCAL").replace("Auditoria Interna", "Revisoría Fiscal")
                               .replace("Auditoría Interna", "Revisoría Fiscal"))
    for coord, val in (refs or {}).items():
        sheet, _, cell = coord.rpartition("!")
        targets = [wb[sheet]] if sheet and sheet in wb.sheetnames else wb.worksheets[:1]
        for ws in targets:
            ws[cell].value = val


# ----------------------------------------------------------------------------- utilidades de hoja
def _is_merged_child(ws, row: int, col: int) -> bool:
    return isinstance(ws.cell(row, col), MergedCell)


def _set(ws, row: int, col: int, value) -> None:
    c = ws.cell(row, col)
    if isinstance(c, MergedCell):
        for rng in ws.merged_cells.ranges:
            if (rng.min_row <= row <= rng.max_row) and (rng.min_col <= col <= rng.max_col):
                c = ws.cell(rng.min_row, rng.min_col)
                break
    c.value = value


def _get(ws, row: int, col: int):
    c = ws.cell(row, col)
    if isinstance(c, MergedCell):
        for rng in ws.merged_cells.ranges:
            if (rng.min_row <= row <= rng.max_row) and (rng.min_col <= col <= rng.max_col):
                return ws.cell(rng.min_row, rng.min_col).value
    return c.value


def _copy_style(src, dst) -> None:
    dst.font, dst.fill, dst.border = copy(src.font), copy(src.fill), copy(src.border)
    dst.alignment, dst.number_format, dst.protection = copy(src.alignment), src.number_format, copy(src.protection)


# columnas por nombre normalizado → clave
_COLS_H = [
    ("ref", r"^ref hallazgo$"), ("area", r"^area cuenta$"), ("signif", r"^signi ?ficativo$"), ("condicion", r"^condicion"),
    ("criterio", r"^criterio"), ("causa", r"^causa"), ("efecto", r"^efecto"), ("recom", r"^recomendacion$"),
    ("respuesta", r"^respuesta"), ("estado", r"^estado$"), ("prioridad", r"^prioridad$"), ("fecha", r"^fecha seguimiento$"),
    ("marca", r"^marca$"), ("titulo", r"^titulo"), ("clasif", r"^clasificacion$"), ("respons", r"^responsable$"),
]
_COLS_E = [
    ("ref", r"^ref evidencia$"), ("rhall", r"^ref hallazgo$"), ("tipo", r"^tipo de evidencia$"), ("desc", r"^descripcion"),
    ("fuente", r"^fuente"), ("fecha", r"^fecha obtencion$"), ("sufic", r"^sufi ?ciente$"), ("aprop", r"^apro ?piada$"),
    ("confia", r"^confia ?bilidad$"), ("obs", r"^observaciones"), ("archivo", r"^ref archivo$"), ("marca", r"^marca$"),
]


@dataclass
class Tabla:
    ws: object
    hdr: int  # fila de encabezados
    cols: dict[str, int]
    first: int  # primera fila de datos
    last: int  # última fila de datos (incluye filas vacías de la plantilla)
    key: str = "ref"

    def filas(self):
        return range(self.first, self.last + 1)


def _mapear(ws, hdr: int, patrones) -> dict[str, int]:
    cols = {}
    for c in range(1, ws.max_column + 1):
        t = norm(_get(ws, hdr, c))
        for key, rx in patrones:
            if key not in cols and t and re.search(rx, t):
                cols[key] = c
                break
    return cols


def localizar(wb, tipo: str) -> Tabla:
    """Tabla de hallazgos (``tipo='h'``) o de evidencias (``'e'``): hoja, fila de encabezados y filas de datos."""
    patrones = _COLS_H if tipo == "h" else _COLS_E
    ancla = "ref hallazgo" if tipo == "h" else "ref evidencia"
    for ws in wb.worksheets:
        for r in range(1, min(ws.max_row, 30) + 1):
            for c in range(1, min(ws.max_column, 8) + 1):
                if norm(_get(ws, r, c)) == ancla:
                    cols = _mapear(ws, r, patrones)
                    if ("condicion" if tipo == "h" else "desc") in cols:
                        col, rx = cols["ref"], re.compile(r"^(H|EV)-\d+$")
                        last = r
                        while rx.match(str(ws.cell(last + 1, col).value or "").strip()) or (
                                last + 1 <= ws.max_row and ws.cell(last + 1, col).value is None and _fila_con_datos(ws, last + 1, cols)):
                            last += 1
                        return Tabla(ws, r, cols, r + 1, last)
    raise LookupError("No se encontró la tabla de " + ("hallazgos" if tipo == "h" else "evidencias") + " en la plantilla.")


def _fila_con_datos(ws, row: int, cols: dict) -> bool:
    return any(_get(ws, row, c) not in (None, "") for k, c in cols.items() if k not in ("ref", "marca"))


def _fila_libre(t: Tabla, row: int) -> bool:
    skip = {"ref", "marca"}
    return all(_get(t.ws, row, c) in (None, "") for k, c in t.cols.items() if k not in skip)


def _ampliar(wb, t: Tabla, n: int) -> None:
    """Inserta ``n`` filas con el formato de la última fila de datos antes de ella (el rango de datos crece)."""
    idx = t.last
    sheet_rows.insert_rows(wb, t.ws, idx, n)
    for k in range(n):
        sheet_rows.copy_row_format(t.ws, idx + n, idx + k, t.ws.max_column, formulas=True)
        for c in t.cols.values():
            if not isinstance(t.ws.cell(idx + k, c), MergedCell) and k >= 0:
                pass
    t.last += n


def _renumerar_libres(t: Tabla, prefijo: str) -> None:
    """Las filas vacías llevan la etiqueta consecutiva de su posición (H-01…, EV-01…)."""
    col = t.cols["ref"]
    for i, r in enumerate(t.filas(), start=1):
        if _fila_libre(t, r):
            t.ws.cell(r, col).value = f"{prefijo}-{i:02d}"


def _asegurar_columnas_nuevas(t: Tabla, nuevas: list[tuple[str, str]]) -> None:
    """Título, Clasificación y Responsable a la derecha de «Marca» (guías, 6.1)."""
    ws, hdr = t.ws, t.hdr
    marca = t.cols.get("marca") or max(t.cols.values())
    col = marca
    for key, titulo in nuevas:
        if key in t.cols:
            continue
        col = max(col, max(t.cols.values())) + 1
        t.cols[key] = col
        for r in range(hdr, t.last + 1):
            _copy_style(ws.cell(r, marca), ws.cell(r, col))
        ws.cell(hdr, col).value = titulo
        ws.column_dimensions[get_column_letter(col)].width = 26 if key != "clasif" else 22
        for r in t.filas():
            ws.cell(r, col).alignment = copy(ws.cell(r, t.cols["condicion"] if "condicion" in t.cols else marca).alignment)


def _validacion(ws, rango: str, lista: str) -> None:
    ws.data_validations.dataValidation = [d for d in ws.data_validations.dataValidation if str(d.sqref) != rango]
    dv = DataValidation(type="list", formula1=f'"{lista}"', allow_blank=True)
    dv.add(rango)
    ws.add_data_validation(dv)


def _limpiar_validaciones(ws, columnas: set[int]) -> None:
    """Quita las validaciones de la plantilla que apuntan a filas equivocadas (las columnas se re-crean)."""
    keep = []
    for d in ws.data_validations.dataValidation:
        cols = {rng.min_col for rng in d.sqref.ranges}
        if not cols & columnas:
            keep.append(d)
    ws.data_validations.dataValidation = keep


# ----------------------------------------------------------------------------- hallazgos
@dataclass
class FilaEscrita:
    hallazgo_id: int
    ref: str
    fila: int
    hoja: str


def _texto(v) -> str:
    return "" if v is None else str(v)


def escribir_hallazgos(wb, items: list, *, modulo: str, area_nombre: str | None = None) -> list[FilaEscrita]:
    """Agrega ``items`` (objetos ``Hallazgo`` ya guardados) en la primera fila libre de la tabla de hallazgos."""
    t = localizar(wb, "h")
    _asegurar_columnas_nuevas(t, [("titulo", "TÍTULO\n(del hallazgo)"), ("clasif", "CLASIFICACIÓN"), ("respons", "RESPONSABLE")])
    libres = [r for r in t.filas() if _fila_libre(t, r)]
    if len(libres) < len(items):
        _ampliar(wb, t, len(items) - len(libres))
        libres = [r for r in t.filas() if _fila_libre(t, r)]
    usados = {str(_get(t.ws, r, t.cols["ref"])) for r in t.filas() if not _fila_libre(t, r)}
    out: list[FilaEscrita] = []
    ws, c = t.ws, t.cols
    for h, row in zip(items, libres):
        ref = str(ws.cell(row, c["ref"]).value or "")
        if ref in usados or not re.match(r"^H-\d+$", ref):
            n = 1
            while f"H-{n:02d}" in usados:
                n += 1
            ref = f"H-{n:02d}"
        usados.add(ref)
        ws.cell(row, c["ref"]).value = ref
        _set(ws, row, c["area"], area_nombre or "")
        _set(ws, row, c["signif"], h.significativo or None)
        _set(ws, row, c["condicion"], h.condicion)
        _set(ws, row, c["criterio"], h.criterio)
        _set(ws, row, c["causa"], h.causa)
        _set(ws, row, c["efecto"], h.efecto)
        _set(ws, row, c["recom"], h.recomendacion)
        _set(ws, row, c["respuesta"], h.respuesta_administracion or None)
        _set(ws, row, c["estado"], config.ETIQUETA_ESTADO[config.EN_PAPEL])
        _set(ws, row, c["prioridad"], h.severidad)
        if h.fecha_seguimiento:
            _set(ws, row, c["fecha"], h.fecha_seguimiento)
            ws.cell(row, c["fecha"]).number_format = "dd/mm/yyyy"
        _set(ws, row, c["marca"], config.MARCA_AUDITA)
        _set(ws, row, c["titulo"], h.titulo)
        _set(ws, row, c["clasif"], h.clasificacion)
        _set(ws, row, c["respons"], h.responsable or None)
        for key in ("condicion", "criterio", "causa", "efecto", "recom", "respuesta", "titulo"):
            al = copy(ws.cell(row, c[key]).alignment)
            ws.cell(row, c[key]).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True,
                                                        indent=al.indent)
        _ajustar_altura(ws, row, {c[k]: _texto(getattr(h, a)) for k, a in
                                  (("condicion", "condicion"), ("criterio", "criterio"), ("causa", "causa"),
                                   ("efecto", "efecto"), ("recom", "recomendacion"), ("titulo", "titulo"))})
        out.append(FilaEscrita(h.pk, ref, row, ws.title))
    _renumerar_libres(t, "H")
    _preparar_hoja_hallazgos(wb, t, modulo)
    return out


def _ajustar_altura(ws, row: int, textos: dict[int, str]) -> None:
    """Alto de fila según el texto más largo y el ancho de su columna (el Excel no lo ajusta solo en celdas con formato)."""
    mejor = 60.0
    for col, texto in textos.items():
        ancho = ws.column_dimensions[get_column_letter(col)].width or 16
        lineas = sum(max(1, -(-len(p) // max(int(ancho * 1.05), 6))) for p in (texto or "").split("\n"))
        mejor = max(mejor, min(lineas * 12.5 + 6, 400))
    ws.row_dimensions[row].height = mejor


def _preparar_hoja_hallazgos(wb, t: Tabla, modulo: str) -> None:
    """Validaciones de las filas reales, columna Crítica en el resumen y fórmulas que cuentan toda la tabla."""
    ws, c = t.ws, t.cols
    _limpiar_validaciones(ws, {c["signif"], c["estado"], c["prioridad"], c["clasif"]})
    r1, r2 = t.first, t.last
    letra = lambda k: get_column_letter(c[k])
    # «Incluido en informe» / «En papel de trabajo» no caben en el ancho original de Estado
    ws.column_dimensions[letra("estado")].width = max(ws.column_dimensions[letra("estado")].width or 0, 20)
    _validacion(ws, f"{letra('signif')}{r1}:{letra('signif')}{r2}", "Sí,No")
    _validacion(ws, f"{letra('estado')}{r1}:{letra('estado')}{r2}", config.ESTADOS_PLANTILLA)
    _validacion(ws, f"{letra('prioridad')}{r1}:{letra('prioridad')}{r2}", ",".join(config.SEVERIDADES))
    clas = config.CLASIFICACIONES_FIN if modulo == "F" else config.CLASIFICACIONES_AI
    _validacion(ws, f"{letra('clasif')}{r1}:{letra('clasif')}{r2}", ",".join(clas))
    _resumen_por_clasificacion(wb, t, modulo)


def _resumen_por_clasificacion(wb, t: Tabla, modulo: str) -> None:
    ws, c = t.ws, t.cols
    # fila de encabezado del resumen
    hdr = next((r for r in range(t.last + 1, ws.max_row + 1) if norm(_get(ws, r, 2)) == "clasificacion"), None)
    if hdr is None:
        return
    filas = []
    r = hdr + 1
    while _get(ws, r, 2) not in (None, ""):
        filas.append(r)
        r += 1
    # Se agrega la columna Crítica: No. | Crítica | Alta | Media | Baja | Abiertos | Cerrados | Observaciones (J:O)
    for m in [m for m in list(ws.merged_cells.ranges) if m.min_row in {hdr, *filas} and m.min_col >= 9]:
        ws.unmerge_cells(str(m))
    estilo_obs = {rr: copy(ws.cell(rr, 9)._style) for rr in [hdr, *filas]}
    estilo_num = {rr: copy(ws.cell(rr, 4)._style) for rr in [hdr, *filas]}
    titulos = ["Crítica", "Alta", "Media", "Baja", "Abiertos", "Cerrados"]
    cl, pr, es = (f"${get_column_letter(c[k])}${t.first}:${get_column_letter(c[k])}${t.last}" for k in ("clasif", "prioridad", "estado"))
    for rr in [hdr, *filas]:
        for j in range(4, 10):  # D..I
            ws.cell(rr, j)._style = copy(estilo_num[rr])
        for j in range(10, 16):  # J..O
            ws.cell(rr, j)._style = copy(estilo_obs[rr])
    observ = {rr: _get(ws, rr, 9) for rr in filas}
    ws.cell(hdr, 3).value = "No."
    for j, tt in enumerate(titulos, start=4):
        ws.cell(hdr, j).value = tt
    obs_hdr = "Observaciones Generales"
    ws.cell(hdr, 10).value = obs_hdr
    ws.merge_cells(start_row=hdr, start_column=10, end_row=hdr, end_column=15)
    for rr in filas:
        ws.cell(rr, 3).value = f'=COUNTIF({cl},$B{rr})'
        for j in range(4, 8):
            ws.cell(rr, j).value = f'=COUNTIFS({cl},$B{rr},{pr},{get_column_letter(j)}${hdr})'
        ws.cell(rr, 8).value = f'=COUNTIFS({cl},$B{rr})-COUNTIFS({cl},$B{rr},{es},"Cerrado")-COUNTIFS({cl},$B{rr},{es},"No Aplica")'
        ws.cell(rr, 9).value = f'=COUNTIFS({cl},$B{rr},{es},"Cerrado")'
        ws.cell(rr, 10).value = observ.get(rr)
        ws.merge_cells(start_row=rr, start_column=10, end_row=rr, end_column=15)
    _comunicacion(wb, t)


def _comunicacion(wb, t: Tabla) -> None:
    """COMUNICACIÓN DE HALLAZGOS (4 preguntas Sí/No): validación en su fila real (la de la plantilla apuntaba a otras filas)."""
    ws = t.ws
    filas = [r for r in range(t.last + 1, ws.max_row + 1) if str(_get(ws, r, 1) or "").startswith("¿")]
    if not filas:
        return
    cols = {rng.min_col for rng in ws.merged_cells.ranges if rng.min_row == filas[0] and rng.min_col > 1}
    col = min(cols) if cols else 12
    _limpiar_validaciones(ws, {col})
    _validacion(ws, f"{get_column_letter(col)}{filas[0]}:{get_column_letter(col)}{filas[-1]}", "Sí,No,En Proceso")


def preguntas_comunicacion(wb) -> tuple[object, list[int], int] | None:
    """(hoja, filas de las preguntas, columna de la respuesta) para marcarlas desde el sistema."""
    t = localizar(wb, "h")
    ws = t.ws
    filas = [r for r in range(t.last + 1, ws.max_row + 1) if str(_get(ws, r, 1) or "").startswith("¿")]
    if not filas:
        return None
    cols = {rng.min_col for rng in ws.merged_cells.ranges if rng.min_row == filas[0] and rng.min_col > 1}
    return ws, filas, (min(cols) if cols else 12)


def actualizar_estado(wb, refs_estados: dict[str, str]) -> None:
    """Cambia la columna Estado de los hallazgos ya colocados (por su referencia H-nn)."""
    t = localizar(wb, "h")
    for r in t.filas():
        ref = str(t.ws.cell(r, t.cols["ref"]).value or "")
        if ref in refs_estados:
            _set(t.ws, r, t.cols["estado"], refs_estados[ref])


def actualizar_campos(wb, ref: str, **campos) -> bool:
    t = localizar(wb, "h")
    mapa = {"respuesta": "respuesta", "fecha": "fecha", "marca": "marca"}
    for r in t.filas():
        if str(t.ws.cell(r, t.cols["ref"]).value or "") == ref:
            for k, v in campos.items():
                if k in t.cols:
                    _set(t.ws, r, t.cols[k], v)
            return True
    return False


def leer_hallazgos(wb) -> dict[str, dict]:
    """Lee lo que el auditor dejó en la plantilla: {H-nn: {campo: texto}} (solo filas con datos)."""
    t = localizar(wb, "h")
    out = {}
    for r in t.filas():
        if _fila_libre(t, r):
            continue
        ref = str(t.ws.cell(r, t.cols["ref"]).value or "")
        row = {k: _get(t.ws, r, col) for k, col in t.cols.items()}
        row["_fila"] = r
        out[ref] = row
    return out


# ----------------------------------------------------------------------------- evidencias
def escribir_evidencias(wb, evidencias: list, refs_hallazgo: dict[int, str]) -> list[FilaEscrita]:
    """``evidencias``: objetos ``EvidenciaHallazgo``; ``refs_hallazgo``: id de hallazgo → H-nn en la plantilla de hallazgos."""
    t = localizar(wb, "e")
    libres = [r for r in t.filas() if _fila_libre(t, r)]
    if len(libres) < len(evidencias):
        _ampliar(wb, t, len(evidencias) - len(libres))
        libres = [r for r in t.filas() if _fila_libre(t, r)]
    usados = {str(_get(t.ws, r, t.cols["ref"])) for r in t.filas() if not _fila_libre(t, r)}
    ws, c = t.ws, t.cols
    out: list[FilaEscrita] = []
    for ev, row in zip(evidencias, libres):
        ref = str(ws.cell(row, c["ref"]).value or "")
        if ref in usados or not re.match(r"^EV-\d+$", ref):
            n = 1
            while f"EV-{n:02d}" in usados:
                n += 1
            ref = f"EV-{n:02d}"
        usados.add(ref)
        ws.cell(row, c["ref"]).value = ref
        _set(ws, row, c["rhall"], refs_hallazgo.get(ev.hallazgo_id, ""))
        _set(ws, row, c["tipo"], config.TIPOS_EVIDENCIA.get(ev.tipo, "Analítica"))
        _set(ws, row, c["desc"], ev.descripcion)
        _set(ws, row, c["fuente"], ev.fuente)
        if ev.fecha_obtencion:
            _set(ws, row, c["fecha"], ev.fecha_obtencion)
            ws.cell(row, c["fecha"]).number_format = "dd/mm/yyyy"
        _set(ws, row, c["sufic"], ev.suficiente or None)
        _set(ws, row, c["aprop"], ev.apropiada or None)
        _set(ws, row, c["confia"], ev.confiabilidad or None)
        _set(ws, row, c["obs"], ev.conclusion)
        _set(ws, row, c["archivo"], ev.ref_archivo or None)
        _set(ws, row, c["marca"], config.MARCA_AUDITA)
        for k in ("desc", "fuente", "obs"):
            ws.cell(row, c[k]).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        _ajustar_altura(ws, row, {c["desc"]: ev.descripcion, c["fuente"]: ev.fuente, c["obs"]: ev.conclusion})
        ws.row_dimensions[row].height = max(ws.row_dimensions[row].height or 40, 40)
        out.append(FilaEscrita(ev.pk, ref, row, ws.title))
    _renumerar_libres(t, "EV")
    _evaluacion_global(wb, t)
    return out


def _evaluacion_global(wb, t: Tabla) -> None:
    ws, c = t.ws, t.cols
    rng = lambda k: f"${get_column_letter(c[k])}${t.first}:${get_column_letter(c[k])}${t.last}"
    _limpiar_validaciones(ws, {c["tipo"], c["sufic"], c["aprop"], c["confia"]})
    _validacion(ws, f"{get_column_letter(c['tipo'])}{t.first}:{get_column_letter(c['tipo'])}{t.last}", ",".join(config.TIPOS_EVIDENCIA.values()))
    _validacion(ws, f"{get_column_letter(c['sufic'])}{t.first}:{get_column_letter(c['aprop'])}{t.last}", "Sí,No,Parcial")
    _validacion(ws, f"{get_column_letter(c['confia'])}{t.first}:{get_column_letter(c['confia'])}{t.last}", "Alta,Media,Baja")
    ev_row = next((r for r in range(t.last + 1, ws.max_row + 1) if norm(_get(ws, r, 1)) == "evaluacion global de la evidencia"), None)
    if ev_row is None:
        return
    # respuesta en la columna combinada a la derecha (L:N)
    col_resp = next((m.min_col for m in ws.merged_cells.ranges if m.min_row == ev_row + 1 and m.min_col > 5), 12)
    fm = {
        1: f'=COUNTA({rng("desc")})', 2: f'=COUNTIF({rng("sufic")},"Sí")', 3: f'=COUNTIF({rng("aprop")},"Sí")',
        4: f'=COUNTIF({rng("confia")},"Alta")',
    }
    for i, f in fm.items():
        _set(ws, ev_row + i, col_resp, f)
    mat = next((r for r in range(ev_row, ws.max_row + 1) if norm(_get(ws, r, 1)).startswith("matriz hallazgo")), None)
    if mat is None:
        return
    hdr = mat + 1
    ultima = hdr
    while re.match(r"^H-\d+$", str(_get(ws, ultima + 1, 2) or "")):
        ultima += 1
    _set(ws, ev_row + 5, col_resp, f'=COUNTIF($I${hdr + 1}:$I${ultima},"Suficiente")')
    _set(ws, ev_row + 6, col_resp, f'=COUNTIF($I${hdr + 1}:$I${ultima},"Requiere evidencia adicional")')


def actualizar_matriz(wb, refs_hallazgo: list[str]) -> None:
    """Matriz HALLAZGO vs TIPO DE EVIDENCIA: una fila por hallazgo presente, con COUNTIFS y conclusión de suficiencia."""
    t = localizar(wb, "e")
    ws, c = t.ws, t.cols
    mat = next((r for r in range(t.last + 1, ws.max_row + 1) if norm(_get(ws, r, 1)).startswith("matriz hallazgo")), None)
    if mat is None:
        return
    hdr = mat + 1
    ultima = hdr
    while re.match(r"^H-\d+$", str(_get(ws, ultima + 1, 2) or "")):
        ultima += 1
    cap = ultima - hdr
    refs = sorted(set(refs_hallazgo), key=lambda s: int(re.sub(r"\D", "", s) or 0))
    if len(refs) > cap:
        sheet_rows.insert_rows(wb, ws, ultima, len(refs) - cap)
        for k in range(len(refs) - cap):
            sheet_rows.copy_row_format(ws, ultima + (len(refs) - cap), ultima + k, ws.max_column, formulas=False)
        ultima += len(refs) - cap
        cap = len(refs)
        t = localizar(wb, "e")
        ws, c = t.ws, t.cols
    rhall = f"${get_column_letter(c['rhall'])}${t.first}:${get_column_letter(c['rhall'])}${t.last}"
    tipo = f"${get_column_letter(c['tipo'])}${t.first}:${get_column_letter(c['tipo'])}${t.last}"
    suf = f"${get_column_letter(c['sufic'])}${t.first}:${get_column_letter(c['sufic'])}${t.last}"
    apr = f"${get_column_letter(c['aprop'])}${t.first}:${get_column_letter(c['aprop'])}${t.last}"
    for i, r in enumerate(range(hdr + 1, ultima + 1)):
        ref = refs[i] if i < len(refs) else f"H-{i + 1:02d}"
        ws.cell(r, 2).value = ref
        if i >= len(refs):
            for j in range(3, 10):
                ws.cell(r, j).value = None
            continue
        for j in range(3, 9):
            ws.cell(r, j).value = f'=COUNTIFS({rhall},$B{r},{tipo},{get_column_letter(j)}${hdr})'
        ws.cell(r, 9).value = (f'=IF(SUM(C{r}:H{r})=0,"Sin evidencia",IF(AND(COUNTIFS({rhall},$B{r},{suf},"Sí")>0,'
                               f'COUNTIFS({rhall},$B{r},{apr},"Sí")>0),"Suficiente","Requiere evidencia adicional"))')
    _evaluacion_global(wb, t)


def leer_evidencias(wb) -> dict[str, dict]:
    t = localizar(wb, "e")
    out = {}
    for r in t.filas():
        if _fila_libre(t, r):
            continue
        ref = str(t.ws.cell(r, t.cols["ref"]).value or "")
        out[ref] = {k: _get(t.ws, r, col) for k, col in t.cols.items()} | {"_fila": r}
    return out


def firmas(wb, *, elaboro: str | None = None, reviso: str | None = None, fecha_elaboro: str | None = None, fecha_reviso: str | None = None) -> None:
    """Esquina «Elaboró / Fecha / Revisó / Fecha» y pie «Elaboró: … / Revisó: …» desde el usuario del sistema (Datos Auditor y Jefe)."""
    for ws in wb.worksheets:
        orden = []
        for row in ws.iter_rows(min_row=1, max_row=8):
            for c in row:
                if isinstance(c, MergedCell) or not isinstance(c.value, str):
                    continue
                t = norm(c.value)
                if t in ("elaboro", "hecho por"):
                    orden.append(("e", c))
                elif t in ("reviso", "revisado por"):
                    orden.append(("r", c))
                elif t == "fecha":
                    orden.append(("f", c))
        ultimo = None
        for tipo, c in orden:
            if tipo in ("e", "r"):
                ultimo = tipo
            destino = ws.cell(c.row, c.column + 1)
            valor = {"e": elaboro, "r": reviso}.get(tipo) if tipo != "f" else (fecha_elaboro if ultimo == "e" else fecha_reviso)
            if valor and not isinstance(destino, MergedCell):
                destino.value = valor
            elif valor:
                _set(ws, c.row, c.column + 1, valor)
        for row in ws.iter_rows(min_row=max(ws.max_row - 20, 1)):
            for c in row:
                if isinstance(c, MergedCell) or not isinstance(c.value, str):
                    continue
                if c.value.startswith("Elaboró:") and elaboro:
                    c.value = f"Elaboró: {elaboro}"
                elif c.value.startswith("Revisó:") and reviso:
                    c.value = f"Revisó: {reviso}"


def sombrear_bloqueados(wb, refs: set[str]) -> None:
    """Hallazgo aprobado = bloqueado: la fila se marca en gris con una nota; el sistema ignora ediciones hechas ahí."""
    from openpyxl.comments import Comment
    from openpyxl.styles import PatternFill

    t = localizar(wb, "h")
    gris = PatternFill("solid", fgColor="D9D9D9")
    for r in t.filas():
        ref = str(t.ws.cell(r, t.cols["ref"]).value or "")
        if ref in refs:
            for k, col in t.cols.items():
                cell = t.ws.cell(r, col)
                if not isinstance(cell, MergedCell):
                    cell.fill = gris
            est = t.ws.cell(r, t.cols["estado"])
            if not isinstance(est, MergedCell) and est.comment is None:
                est.comment = Comment("Bloqueado: hallazgo aprobado. Solo el Jefe de Auditoría puede reabrirlo desde Audita Análisis.", "Audita Análisis")
