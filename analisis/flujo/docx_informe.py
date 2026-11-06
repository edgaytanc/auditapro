"""Hallazgos aprobados → informes Word (guías del cliente, etapa 5 de Financiera y etapa 3 de Auditoría Interna).

Reglas de las guías:
* se inserta en un marcador (bookmark ``HALLAZGOS_AUDITA``) y no buscando texto; la primera vez el marcador se crea
  a partir de la frase fija del informe y desde entonces se reconoce por su nombre;
* estilos de Word, tablas reales y párrafos normales (sin saltos manuales que deformen el justificado);
* el archivo base nunca se modifica: quien llama guarda el resultado como versión nueva (v1, v2…);
* sin hallazgos aprobados se inserta la frase indicada por la guía.
"""
from __future__ import annotations

import copy
import re
from datetime import date

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from . import config

MARCADOR = "HALLAZGOS_AUDITA"
FRASE_FIN = "A continuación se detallan los hallazgos identificados"
SIN_HALLAZGOS_FIN = "No se identificaron hallazgos que requieran comunicación a la administración."
SIN_HALLAZGOS_AI = "No se identificaron hallazgos para esta área."
COLOR_SEV = {"Crítica": "C00000", "Alta": "FF4500", "Media": "B8860B", "Baja": "2E7D32"}
GRUPO_AI = {"Crítica": ("HALLAZGOS CRÍTICOS", "CRÍTICO"), "Alta": ("HALLAZGOS ALTOS", "ALTO"),
            "Media": ("HALLAZGOS MEDIOS", "MEDIO"), "Baja": ("HALLAZGOS BAJOS", "BAJO")}


class InformeError(Exception):
    pass


# ----------------------------------------------------------------------------- bajo nivel
def _estilo(doc, *nombres):
    for n in nombres:
        try:
            return doc.styles[n]
        except KeyError:
            continue
    return None


def _texto_parrafo(p) -> str:
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def _es_heading(p_el, nivel: int | None = None) -> bool:
    ppr = p_el.find(qn("w:pPr"))
    if ppr is None:
        return False
    st = ppr.find(qn("w:pStyle"))
    if st is None:
        return False
    val = st.get(qn("w:val")) or ""
    return bool(re.match(r"^(Heading|T[ií]tulo|Ttulo)\s*(\d)$", val)) and (nivel is None or val.endswith(str(nivel)))


def _bookmark(p_el, nombre: str, ident: int = 9001) -> None:
    ini, fin = OxmlElement("w:bookmarkStart"), OxmlElement("w:bookmarkEnd")
    ini.set(qn("w:id"), str(ident)); ini.set(qn("w:name"), nombre); fin.set(qn("w:id"), str(ident))
    ppr = p_el.find(qn("w:pPr"))
    if ppr is not None:
        ppr.addnext(ini)
    else:
        p_el.insert(0, ini)
    p_el.append(fin)


def _bookmark_parrafo(doc, nombre: str):
    for b in doc.element.body.iter(qn("w:bookmarkStart")):
        if b.get(qn("w:name")) == nombre:
            return b.getparent()
    return None


def _actualizar_campos(doc) -> None:
    """Word pide actualizar la tabla de contenido y los números de página al abrir el archivo."""
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        settings.append(uf)


class _Cursor:
    """Inserta elementos nuevos justo antes de ``ancla`` (el siguiente encabezado o el final del documento)."""

    def __init__(self, doc, ancla):
        self.doc, self.ancla = doc, ancla

    def _colocar(self, el):
        if self.ancla is not None:
            self.ancla.addprevious(el)
        else:
            sect = self.doc.element.body.find(qn("w:sectPr"))
            (sect.addprevious(el) if sect is not None else self.doc.element.body.append(el))
        return el

    def parrafo(self, texto: str = "", *, estilo=None, negrita=False, color: str | None = None, tam: float | None = None,
                alinear=WD_ALIGN_PARAGRAPH.LEFT, espacio_despues: float | None = 6, mantener_siguiente=False):
        p = self.doc.add_paragraph(style=estilo)
        if texto:
            r = p.add_run(texto)
            r.bold = negrita or None
            if color:
                r.font.color.rgb = RGBColor.from_string(color)
            if tam:
                r.font.size = Pt(tam)
        p.alignment = alinear
        if espacio_despues is not None:
            p.paragraph_format.space_after = Pt(espacio_despues)
        if mantener_siguiente:
            p.paragraph_format.keep_with_next = True
        self._colocar(p._p)
        return p

    def etiqueta(self, etiqueta: str, texto: str, *, color_etiqueta: str | None = None, tam: float | None = None):
        """«Etiqueta: texto» con la etiqueta en negrita (formato de los informes de ejemplo)."""
        p = self.doc.add_paragraph()
        r = p.add_run(etiqueta + " ")
        r.bold = True
        if color_etiqueta:
            r.font.color.rgb = RGBColor.from_string(color_etiqueta)
        if tam:
            r.font.size = Pt(tam)
        cuerpo = [x for x in re.split(r"\n{1,}", texto or "") if x.strip()] or [""]
        r2 = p.add_run(cuerpo[0])
        if tam:
            r2.font.size = Pt(tam)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(4)
        self._colocar(p._p)
        for extra in cuerpo[1:]:
            q = self.doc.add_paragraph(extra)
            q.alignment = WD_ALIGN_PARAGRAPH.LEFT
            q.paragraph_format.space_after = Pt(4)
            if tam:
                for run in q.runs:
                    run.font.size = Pt(tam)
            self._colocar(q._p)
        return p

    def tabla(self, cabecera: list[str], filas: list[list[str]], anchos: list[float] | None = None):
        t = self.doc.add_table(rows=1, cols=len(cabecera))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        estilo = _estilo(self.doc, "Table Grid", "Tablaconcuadrcula")
        if estilo is not None:
            t.style = estilo
        _bordes(t)
        for j, h in enumerate(cabecera):
            c = t.rows[0].cells[j]
            c.text = ""
            run = c.paragraphs[0].add_run(h)
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            _sombra(c, "1F3864")
        _repetir_encabezado(t.rows[0])
        for fila in filas:
            cells = t.add_row().cells
            for j, v in enumerate(fila):
                cells[j].text = ""
                run = cells[j].paragraphs[0].add_run(str(v))
                run.font.size = Pt(9)
        if anchos:
            for row in t.rows:
                for j, w in enumerate(anchos):
                    row.cells[j].width = Pt(w)
        self._colocar(t._tbl)
        self.parrafo("", espacio_despues=4)
        return t


def _bordes(tabla) -> None:
    tblPr = tabla._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "808080")
        b.append(e)
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    tblPr.append(b)


def _sombra(celda, color: str) -> None:
    tcPr = celda._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def _repetir_encabezado(fila) -> None:
    trPr = fila._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


# ----------------------------------------------------------------------------- Financiera (5.6.1, sección 5)
def _region_seccion5(doc):
    """(párrafo de la frase fija o del marcador, siguiente encabezado nivel 1). Crea el marcador si aún no existe."""
    cuerpo = list(doc.element.body)
    p_mark = _bookmark_parrafo(doc, MARCADOR)
    if p_mark is None:
        enc = next((el for el in cuerpo if el.tag == qn("w:p") and _es_heading(el, 1)
                    and re.match(r"^\s*5\.\s*HALLAZGOS", _texto_parrafo(el), re.I)), None)
        if enc is None:
            raise InformeError("El informe no tiene la sección «5. HALLAZGOS Y RECOMENDACIONES DE AUDITORÍA».")
        i0 = cuerpo.index(enc)
        p_mark = next((el for el in cuerpo[i0 + 1:] if el.tag == qn("w:p") and FRASE_FIN.lower() in _texto_parrafo(el).lower()), None)
        if p_mark is None:
            # la frase no está: el marcador queda en el propio encabezado
            p_mark = enc
        _bookmark(p_mark, MARCADOR)
    sig = None
    for el in cuerpo[cuerpo.index(p_mark) + 1:]:
        if el.tag == qn("w:p") and _es_heading(el, 1):
            sig = el
            break
    return p_mark, sig


def _quitar_entre(inicio, fin) -> None:
    """Borra todo lo que hay entre ``inicio`` y ``fin`` (exclusivos), salvo el último ``sectPr``."""
    el = inicio.getnext()
    while el is not None and el is not fin:
        sig = el.getnext()
        if el.tag != qn("w:sectPr"):
            el.getparent().remove(el)
        el = sig


def generar_seccion5(base: str, destino: str, hallazgos: list, *, cuenta_nombre, evidencias_de, ctx: dict | None = None) -> dict:
    """Reemplaza la sección 5 del informe de Auditoría Financiera con los hallazgos finales (``hallazgos`` ya ordenados HF-01…)."""
    doc = Document(base)
    p_mark, sig = _region_seccion5(doc)
    _quitar_entre(p_mark, sig)
    cur = _Cursor(doc, sig)
    if not hallazgos:
        cur.parrafo("")
        cur.parrafo(SIN_HALLAZGOS_FIN)
    else:
        cur.parrafo("")
        cur.parrafo("Resumen de hallazgos", negrita=True, color="003366", tam=11, mantener_siguiente=True)
        cur.tabla(["N.º", "Hallazgo", "Cuenta / Área", "Clasificación", "Severidad"],
                  [[h.hf_numero or i, h.titulo, cuenta_nombre(h), h.clasificacion or "—", h.severidad]
                   for i, h in enumerate(hallazgos, start=1)], anchos=[28, 190, 100, 100, 55])
        h2 = _estilo(doc, "Heading 2", "Título 2", "Ttulo2")
        for i, h in enumerate(hallazgos, start=1):
            n = h.hf_numero or i
            cur.parrafo(f"HALLAZGO No. {n}: {h.titulo.upper()}", estilo=h2, mantener_siguiente=True, alinear=WD_ALIGN_PARAGRAPH.LEFT)
            p = cur.doc.add_paragraph()
            r1 = p.add_run(f"CLASIFICACIÓN: {(h.clasificacion or '—').upper()}    SEVERIDAD: ")
            r1.bold, r1.font.size = True, Pt(10)
            r2 = p.add_run(h.severidad.upper())
            r2.bold, r2.font.size = True, Pt(10)
            r2.font.color.rgb = RGBColor.from_string(COLOR_SEV.get(h.severidad, "000000"))
            p.paragraph_format.space_after = Pt(6)
            cur._colocar(p._p)
            cur.etiqueta("CONDICIÓN (Lo que encontramos):", h.condicion, color_etiqueta="C00000")
            d = h.detalle or {}
            if d.get("head") and d.get("rows"):
                cur.tabla([str(x) for x in d["head"]], [[("" if v is None else v) for v in row] for row in d["rows"][:25]])
            cur.etiqueta("CRITERIO (Normativa aplicable):", h.criterio, color_etiqueta="003366")
            cur.etiqueta("CAUSA (Por qué ocurrió):", h.causa, color_etiqueta="FF8C00")
            cur.etiqueta("EFECTO (Consecuencias e impacto):", h.efecto, color_etiqueta="C00000")
            cur.etiqueta("RECOMENDACIÓN (Acciones correctivas):", h.recomendacion, color_etiqueta="008000")
            evs = evidencias_de(h)
            cur.parrafo("Evidencia de auditoría obtenida:", negrita=True, espacio_despues=2)
            if evs:
                for e in evs:
                    cur.parrafo("• " + e, espacio_despues=2)
            else:
                cur.parrafo("• Sin evidencia vinculada.", espacio_despues=2)
            cur.etiqueta("Respuesta de la Administración:", h.respuesta_administracion or "Pendiente de respuesta")
            cur.parrafo("")
    _actualizar_campos(doc)
    doc.save(destino)
    return {"hallazgos": len(hallazgos), "marcador": MARCADOR}


# ----------------------------------------------------------------------------- Auditoría Interna (5.1.x)
def _region_hallazgos_ai(doc):
    """(primer encabezado «HALLAZGOS …» o marcador, encabezado de la opinión). El informe de cada área los trae en este orden."""
    cuerpo = list(doc.element.body)
    opinion = next((el for el in cuerpo if el.tag == qn("w:p") and _es_heading(el, 1)
                    and re.match(r"^\s*VI+\.?:?\s*OPINI", _texto_parrafo(el), re.I)), None)
    ini = _bookmark_parrafo(doc, MARCADOR)
    if ini is None:
        ini = next((el for el in cuerpo if el.tag == qn("w:p") and _es_heading(el, 1)
                    and re.match(r"^\s*HALLAZGOS\s+(CR[IÍ]TICOS|ALTOS|MEDIOS|BAJOS)", _texto_parrafo(el), re.I)), None)
        if ini is not None:
            _bookmark(ini, MARCADOR)
    return ini, opinion


def generar_hallazgos_area(base: str, destino: str, hallazgos: list, *, fecha_aprobacion: date, area_nombre: str) -> dict:
    """Agrega los hallazgos aprobados al informe del área: «HALLAZGOS CRÍTICOS» y «CRÍTICO 1: título» con Condición, Criterio,
    Causa, Efecto, Recomendación, Responsable y Plazo (días desde la aprobación)."""
    doc = Document(base)
    ini, opinion = _region_hallazgos_ai(doc)
    h1 = _estilo(doc, "Heading 1", "Título 1", "Ttulo1")
    if ini is None:
        # el informe no traía la sección: va justo antes de la opinión (o al final)
        cur = _Cursor(doc, opinion)
        ini = cur.parrafo("", estilo=h1, espacio_despues=0)._p
        _bookmark(ini, MARCADOR)
    else:
        _quitar_entre(ini, opinion)
        # el primer encabezado (marcado) se reutiliza: se borra su texto y se vuelve a escribir abajo
        for t in list(ini.iter(qn("w:t"))):
            t.text = ""
    cur = _Cursor(doc, opinion)
    grupos: dict[str, list] = {}
    for h in hallazgos:
        grupos.setdefault(h.severidad, []).append(h)
    if not hallazgos:
        _poner_texto(ini, "HALLAZGOS")
        cur.parrafo(SIN_HALLAZGOS_AI)
    else:
        primero = True
        for sev in config.SEVERIDADES:
            if sev not in grupos:
                continue
            titulo, etiqueta = GRUPO_AI[sev]
            if primero:
                _poner_texto(ini, titulo)
                primero = False
            else:
                cur.parrafo(titulo, estilo=h1, mantener_siguiente=True)
            for n, h in enumerate(grupos[sev], start=1):
                p = cur.doc.add_paragraph()
                r = p.add_run(f"{etiqueta} {n}: {h.titulo.upper()}")
                r.bold, r.font.size = True, Pt(13)
                r.font.color.rgb = RGBColor.from_string(COLOR_SEV[sev])
                p.paragraph_format.keep_with_next = True
                cur._colocar(p._p)
                plazo = "Por definir"
                if h.fecha_seguimiento:
                    dias = (h.fecha_seguimiento - fecha_aprobacion).days
                    plazo = f"{dias} días" if dias >= 0 else "Vencido"
                for et, val in (("Condición:", h.condicion), ("Criterio:", h.criterio), ("Causa:", h.causa), ("Efecto:", h.efecto),
                                ("Recomendación:", h.recomendacion), ("Responsable:", h.responsable or "Por asignar"), ("Plazo:", plazo)):
                    cur.etiqueta(et, val, tam=12)
                cur.parrafo("")
    _actualizar_campos(doc)
    doc.save(destino)
    return {"hallazgos": len(hallazgos), "area": area_nombre, "marcador": MARCADOR}


def _poner_texto(p_el, texto: str) -> None:
    ts = list(p_el.iter(qn("w:t")))
    if ts:
        ts[0].text = texto
        for t in ts[1:]:
            t.text = ""
    else:
        r = OxmlElement("w:r"); t = OxmlElement("w:t"); t.text = texto; r.append(t); p_el.append(r)


def documento_base_area(destino: str, area_nombre: str, ctx: dict) -> None:
    """Informe mínimo para un área sin plantilla Word (p. ej. proyectos con otra numeración): encabezado + sección de hallazgos."""
    doc = Document()
    doc.add_heading(f"Informe de Auditoría Interna — {area_nombre}", level=0)
    doc.add_paragraph(f"Entidad: {ctx.get('entidad', '')}")
    doc.add_paragraph(ctx.get("periodo", ""))
    doc.add_heading("HALLAZGOS", level=1)
    doc.add_heading("VII. OPINIÓN DE AUDITORÍA", level=1)
    doc.save(destino)
