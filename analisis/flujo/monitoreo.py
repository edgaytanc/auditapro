"""Auditoría Interna · carpeta «8 MONITOREO CONTINUO»: recibe las excepciones de Audita Análisis y alimenta el panel.

Flujo (el del mockup del cliente): una excepción llega «Pendiente» → el auditor la confirma (se le asigna seguimiento a 7 días,
ampliable de 5 en 5) o la marca falso positivo → una excepción confirmada se convierte en hallazgo (va a las plantillas de
Hallazgos y Evidencias del flujo de la fase 2). Todo se puede descargar en Excel, Word y PDF.
"""
from __future__ import annotations

import io
import re
from collections import Counter
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from ..models import BitacoraProyecto, CorridaAnalisis, ExcepcionMonitoreo, Hallazgo, HallazgoAnalisis
from . import config, services

PLAZO_INICIAL_DIAS = 7
AMPLIACION_DIAS = 5

# proceso → (prefijo del caso, nombre, área sugerida del informe)
PROCESOS = [
    (r"concili", ("CONC", "Conciliaciones", "tesoreria")),
    (r"caja|banc|arqueo|tesor|efectivo", ("CAJ", "Tesorería / Caja", "tesoreria")),
    (r"n[oó]mina|sueldo|salari|empleado|horas? extra|planilla", ("NOM", "Nómina", "rrhh")),
    (r"inventario|existencia|bodega", ("INV", "Inventarios", "inventarios")),
    (r"venta|ingreso|cliente|cobrar|factura emitida", ("VTA", "Ingresos / Ventas", "ventas")),
    (r"proveedor|factura|pago|egreso|compra|pagar|contrato", ("CXP", "Cuentas por pagar", "compras")),
]
RIESGO_DE_ALERTA = {"Alta": "Alto", "Media": "Medio", "Baja": "Bajo"}
PROB_DE_TIPO = {"hallazgo": "Alta", "excepcion": "Media", "riesgo": "Baja"}
ORDEN_RIESGO = {"Alto": 0, "Medio": 1, "Bajo": 2}


DEFECTO_POR_TIPO_DE_PRUEBA = {"G-1": ("CXP", "Cuentas por pagar", "compras"), "P-1": ("CXP", "Cuentas por pagar", "compras"), "I-1": ("VTA", "Ingresos / Ventas", "ventas")}


def proceso_de(texto: str, tipo_prueba: str = "") -> tuple[str, str, str]:
    """Proceso de la excepción: por palabras clave del hallazgo y, si no hay, por el tipo de prueba que lo originó."""
    t = (texto or "").lower()
    for rx, val in PROCESOS:
        if re.search(rx, t):
            return val
    return DEFECTO_POR_TIPO_DE_PRUEBA.get(tipo_prueba, ("GEN", "Otros procesos", "transversal"))


def _caso(audit, pref: str, fecha: date) -> str:
    n = ExcepcionMonitoreo.objects.filter(audit=audit).count() + 1
    caso = f"#{pref}-{fecha.year}-{n:05d}"
    while ExcepcionMonitoreo.objects.filter(audit=audit, caso=caso).exists():
        n += 1
        caso = f"#{pref}-{fecha.year}-{n:05d}"
    return caso


@transaction.atomic
def recibir(corrida: CorridaAnalisis) -> list[ExcepcionMonitoreo]:
    """Entrada automática: cada hallazgo o excepción del análisis (no descartado) llega a Monitoreo Continuo. Idempotente."""
    audit = corrida.audit
    if services.modulo_de(audit) != "I":
        return []
    docs = ", ".join(d.nombre_original for d in corrida.documentos.all()[:3])
    fecha = (corrida.terminado_en or corrida.creado_en).date()
    creadas = []
    for ha in corrida.hallazgos.exclude(decision=HallazgoAnalisis.Decision.DESCARTADO).order_by("orden", "id"):
        if ExcepcionMonitoreo.objects.filter(origen=ha).exists():
            continue
        pref, proceso, _area = proceso_de(f"{ha.procedimiento} {ha.resultado} {corrida.titulo}", (corrida.plan or {}).get("kind_ref", ""))
        creadas.append(ExcepcionMonitoreo.objects.create(
            audit=audit, corrida=corrida, origen=ha, caso=_caso(audit, pref, fecha), tarea=(ha.procedimiento or "Excepción")[:300],
            proceso=proceso, responsable="Proceso automático", riesgo=RIESGO_DE_ALERTA.get(ha.alerta, "Medio"),
            probabilidad=PROB_DE_TIPO.get(ha.tipo, "Media"), fecha=fecha, resultado_ia=ha.resultado,
            evidencia=(ha.origen or docs or f"Análisis #{corrida.pk}")[:300]))
    if creadas:
        BitacoraProyecto.registrar(audit, corrida.creado_por, "monitoreo_recibe", "corrida", corrida.pk, {}, {"excepciones": [e.caso for e in creadas]})
    return creadas


def sin_excepcion(audit) -> int:
    """Registros revisados por Audita Análisis que no generaron excepción («Conformes, archivados»)."""
    from django.db.models import Sum

    leidas = CorridaAnalisis.objects.filter(audit=audit, estado=CorridaAnalisis.Estado.TERMINADO).aggregate(
        n=Sum("documentos__filas_leidas"))["n"] or 0
    return max(int(leidas) - ExcepcionMonitoreo.objects.filter(audit=audit).count(), 0)


# ----------------------------------------------------------------------------- decisiones
class MonitoreoError(Exception):
    pass


def _seguimiento_estado(ex: ExcepcionMonitoreo, hoy: date | None = None) -> dict | None:
    if not ex.fecha_limite:
        return None
    hoy = hoy or date.today()
    d = (ex.fecha_limite - hoy).days
    if d < 0:
        return {"clave": "vencido", "texto": f"Vencido hace {abs(d)} día{'s' if abs(d) != 1 else ''}", "corto": "Vencido"}
    if d <= 3:
        return {"clave": "pronto", "texto": f"Vence en {d} día{'s' if d != 1 else ''}", "corto": f"En {d} d."}
    return {"clave": "plazo", "texto": f"En plazo · {d} días restantes", "corto": "En plazo"}


def confirmar(user, ex: ExcepcionMonitoreo) -> ExcepcionMonitoreo:
    if ex.estado != ExcepcionMonitoreo.Estado.PENDIENTE:
        raise MonitoreoError("Solo se confirman las excepciones pendientes.")
    ex.estado = ExcepcionMonitoreo.Estado.CONFIRMADO
    ex.auditor_seguimiento = user
    ex.fecha_limite = date.today() + timedelta(days=PLAZO_INICIAL_DIAS)
    ex.save()
    BitacoraProyecto.registrar(ex.audit, user, "monitoreo_confirma", "excepcion", ex.caso, {}, {"fecha_limite": str(ex.fecha_limite)})
    return ex


def descartar(user, ex: ExcepcionMonitoreo) -> ExcepcionMonitoreo:
    if ex.estado != ExcepcionMonitoreo.Estado.PENDIENTE:
        raise MonitoreoError("Solo se marcan como falso positivo las excepciones pendientes.")
    ex.estado = ExcepcionMonitoreo.Estado.DESCARTADO
    ex.save()
    if ex.origen_id:
        ex.origen.decision = HallazgoAnalisis.Decision.DESCARTADO
        ex.origen.decision_nota = "Falso positivo (Monitoreo Continuo)"
        ex.origen.decidido_por, ex.origen.decidido_en = user, timezone.now()
        ex.origen.save(update_fields=["decision", "decision_nota", "decidido_por", "decidido_en"])
    BitacoraProyecto.registrar(ex.audit, user, "monitoreo_falso_positivo", "excepcion", ex.caso)
    return ex


def ampliar_plazo(user, ex: ExcepcionMonitoreo, dias: int = AMPLIACION_DIAS) -> ExcepcionMonitoreo:
    if not ex.fecha_limite or ex.estado == ExcepcionMonitoreo.Estado.HALLAZGO:
        raise MonitoreoError("La excepción no tiene un seguimiento abierto.")
    antes = ex.fecha_limite
    ex.fecha_limite = antes + timedelta(days=dias)
    ex.save(update_fields=["fecha_limite"])
    BitacoraProyecto.registrar(ex.audit, user, "monitoreo_amplia_plazo", "excepcion", ex.caso, {"fecha_limite": str(antes)}, {"fecha_limite": str(ex.fecha_limite)})
    return ex


@transaction.atomic
def convertir_en_hallazgo(user, ex: ExcepcionMonitoreo, area: str) -> Hallazgo:
    """Una excepción confirmada pasa al flujo de hallazgos (plantillas 5.2 y 5.3 del área elegida)."""
    if ex.estado != ExcepcionMonitoreo.Estado.CONFIRMADO:
        raise MonitoreoError("Primero confirme la excepción.")
    if not ex.origen_id or not ex.corrida_id:
        raise MonitoreoError("La excepción no viene de un análisis.")
    plazo = max((ex.fecha_limite - date.today()).days, 1) if ex.fecha_limite else PLAZO_INICIAL_DIAS
    r = services.enviar_a_papel(user, ex.corrida, [ex.origen_id], destino=area, plazo_dias=plazo,
                                overrides={ex.origen_id: {"responsable": ex.responsable if ex.responsable != "Proceso automático" else ""}})
    h = Hallazgo.objects.filter(audit=ex.audit, origen_id=ex.origen_id, area=area).first()
    if h is None:
        raise MonitoreoError("No se pudo crear el hallazgo.")
    ex.estado, ex.hallazgo = ExcepcionMonitoreo.Estado.HALLAZGO, h
    ex.save(update_fields=["estado", "hallazgo"])
    BitacoraProyecto.registrar(ex.audit, user, "monitoreo_convierte_en_hallazgo", "excepcion", ex.caso, {}, {"hallazgo": h.ref_local, "area": area, "duplicado": bool(r["duplicados"])})
    return h


# ----------------------------------------------------------------------------- panel
def _semana(d: date) -> date:
    return d - timedelta(days=d.weekday())


def panel(audit, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    qs = list(ExcepcionMonitoreo.objects.filter(audit=audit).exclude(estado=ExcepcionMonitoreo.Estado.DESCARTADO))
    todas = list(ExcepcionMonitoreo.objects.filter(audit=audit))
    sem_act, sem_ant = _semana(hoy), _semana(hoy) - timedelta(days=7)

    def delta(filtro):
        a = sum(1 for e in qs if filtro(e) and _semana(e.fecha) == sem_act)
        b = sum(1 for e in qs if filtro(e) and _semana(e.fecha) == sem_ant)
        return a - b

    por_proceso = Counter(e.proceso or "Otros procesos" for e in qs)
    mapa = {(p, r): 0 for p in ("Alta", "Media", "Baja") for r in ("Bajo", "Medio", "Alto")}
    for e in qs:
        mapa[(e.probabilidad, e.riesgo)] += 1
    semanas = [sem_act - timedelta(days=7 * i) for i in range(7, -1, -1)]
    tendencia = [{"semana": s.strftime("%d/%m"), "n": sum(1 for e in qs if _semana(e.fecha) == s)} for s in semanas]
    conformes = sin_excepcion(audit)
    return {
        "kpis": {
            "conformes": conformes, "observaciones": sum(1 for e in qs if e.riesgo in ("Medio", "Bajo")),
            "riesgo_alto": sum(1 for e in qs if e.riesgo == "Alto"),
            "incumplimientos": sum(1 for e in qs if e.origen and e.origen.agente in ("contratos",) or "incumpl" in (e.resultado_ia or "").lower()),
            "d_observaciones": delta(lambda e: e.riesgo in ("Medio", "Bajo")), "d_riesgo_alto": delta(lambda e: e.riesgo == "Alto"),
        },
        "total": len(qs), "por_proceso": por_proceso.most_common(),
        "max_proceso": max(por_proceso.values(), default=1),
        "calor": [{"prob": p, "celdas": [{"riesgo": r, "n": mapa[(p, r)]} for r in ("Bajo", "Medio", "Alto")]} for p in ("Alta", "Media", "Baja")],
        "tendencia": tendencia, "max_tendencia": max((t["n"] for t in tendencia), default=1) or 1,
        "pendientes": sum(1 for e in todas if e.estado == ExcepcionMonitoreo.Estado.PENDIENTE),
    }


def lista(audit, solo_pendientes: bool = False):
    qs = ExcepcionMonitoreo.objects.filter(audit=audit).select_related("auditor_seguimiento", "hallazgo", "origen")
    if solo_pendientes:
        qs = qs.filter(estado=ExcepcionMonitoreo.Estado.PENDIENTE)
    return sorted(qs, key=lambda e: (e.estado != ExcepcionMonitoreo.Estado.PENDIENTE, ORDEN_RIESGO.get(e.riesgo, 9), -e.fecha.toordinal(), -e.pk))


def area_sugerida(ex: ExcepcionMonitoreo) -> str:
    return proceso_de(f"{ex.tarea} {ex.proceso}", {"Cuentas por pagar": "P-1", "Ingresos / Ventas": "I-1"}.get(ex.proceso, ""))[2]


# ----------------------------------------------------------------------------- descargas
def _datos(ex: ExcepcionMonitoreo) -> dict:
    seg = f"Auditor: {services._nombre_usuario(ex.auditor_seguimiento)} · Fecha límite: {ex.fecha_limite.strftime('%d/%m/%Y')}" if ex.fecha_limite else "Sin seguimiento asignado"
    h = ex.hallazgo or (Hallazgo.objects.filter(origen_id=ex.origen_id).first() if ex.origen_id else None)
    return {"caso": ex.caso, "tarea": ex.tarea, "proceso": ex.proceso, "responsable": ex.responsable, "riesgo": ex.riesgo,
            "fecha": ex.fecha.strftime("%d/%m/%Y"), "estado": ex.get_estado_display(), "resultado": ex.resultado_ia,
            "evidencia": ex.evidencia, "seguimiento": seg, "hallazgo": h}


def excel_excepcion(ex: ExcepcionMonitoreo) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    d = _datos(ex)
    wb = Workbook()
    ws = wb.active
    ws.title = "Excepción"
    ws["A1"] = "MONITOREO CONTINUO — REPORTE DE EXCEPCIÓN"
    ws["A1"].font = Font(bold=True, size=13, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="1F3864")
    ws.merge_cells("A1:B1")
    filas = [("Caso", d["caso"]), ("Tarea", d["tarea"]), ("Proceso", d["proceso"]), ("Responsable", d["responsable"]), ("Riesgo", d["riesgo"]),
             ("Fecha", d["fecha"]), ("Estado", d["estado"]), ("Evidencia", d["evidencia"]), ("Seguimiento", d["seguimiento"]),
             ("Resultado de Audita Análisis", d["resultado"])]
    h = d["hallazgo"]
    if h:
        filas += [("", ""), ("HALLAZGO", f"{h.ref_local} · {h.titulo}"), ("Condición", h.condicion), ("Criterio", h.criterio), ("Causa", h.causa),
                  ("Efecto", h.efecto), ("Recomendación", h.recomendacion)]
    for i, (k, v) in enumerate(filas, start=3):
        ws.cell(i, 1, k).font = Font(bold=True)
        c = ws.cell(i, 2, v)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 30, 90
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def excel_panel(audit) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Excepciones"
    head = ["Caso", "Tarea", "Proceso", "Responsable", "Riesgo", "Probabilidad", "Fecha", "Estado", "Seguimiento", "Fecha límite", "Evidencia", "Resultado de Audita Análisis", "Hallazgo"]
    ws.append(head)
    for c in ws[1]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")
    for e in lista(audit):
        ws.append([e.caso, e.tarea, e.proceso, e.responsable, e.riesgo, e.probabilidad, e.fecha, e.get_estado_display(),
                   services._nombre_usuario(e.auditor_seguimiento), e.fecha_limite, e.evidencia, e.resultado_ia, e.hallazgo.ref_local if e.hallazgo else ""])
    for col, w in zip("ABCDEFGHIJKLM", (16, 38, 18, 18, 9, 11, 11, 18, 22, 12, 30, 60, 10)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        row[6].number_format = row[9].number_format = "dd/mm/yyyy"
    p = panel(audit)
    r = wb.create_sheet("Resumen")
    r.append(["Indicador", "Valor"])
    for k, v in (("Conformes (archivados)", p["kpis"]["conformes"]), ("Observaciones", p["kpis"]["observaciones"]),
                 ("Riesgo alto", p["kpis"]["riesgo_alto"]), ("Incumplimientos", p["kpis"]["incumplimientos"]), ("Pendientes de revisión", p["pendientes"])):
        r.append([k, v])
    r.append([])
    r.append(["Proceso", "Excepciones"])
    for proc, n in p["por_proceso"]:
        r.append([proc, n])
    r.column_dimensions["A"].width = 32
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def word_excepcion(ex: ExcepcionMonitoreo) -> bytes:
    from docx import Document
    from docx.shared import Pt

    d = _datos(ex)
    doc = Document()
    doc.add_heading("Monitoreo Continuo — Reporte de excepción", level=1)
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for k, v in (("Caso", d["caso"]), ("Tarea", d["tarea"]), ("Proceso", d["proceso"]), ("Responsable", d["responsable"]), ("Riesgo", d["riesgo"]),
                 ("Fecha", d["fecha"]), ("Estado", d["estado"]), ("Evidencia", d["evidencia"]), ("Seguimiento", d["seguimiento"])):
        c = t.add_row().cells
        c[0].text, c[1].text = k, str(v)
        c[0].paragraphs[0].runs[0].bold = True
    doc.add_heading("Resultado de Audita Análisis", level=2)
    doc.add_paragraph(d["resultado"])
    h = d["hallazgo"]
    if h:
        doc.add_heading(f"Hallazgo {h.ref_local}: {h.titulo}", level=2)
        for et, v in (("Condición", h.condicion), ("Criterio", h.criterio), ("Causa", h.causa), ("Efecto", h.efecto), ("Recomendación", h.recomendacion)):
            p = doc.add_paragraph()
            r = p.add_run(et + ": ")
            r.bold = True
            p.add_run(v or "")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def pdf_excepcion(ex: ExcepcionMonitoreo) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from xml.sax.saxutils import escape

    d = _datos(ex)
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"Excepción {d['caso']}")
    P = lambda t, s="BodyText": Paragraph(escape(str(t or "")), st[s])
    items = [P("Monitoreo Continuo — Reporte de excepción", "Title"), Spacer(1, 6)]
    tabla = [[P(k, "BodyText"), P(v)] for k, v in (("Caso", d["caso"]), ("Tarea", d["tarea"]), ("Proceso", d["proceso"]), ("Responsable", d["responsable"]),
                                                  ("Riesgo", d["riesgo"]), ("Fecha", d["fecha"]), ("Estado", d["estado"]), ("Evidencia", d["evidencia"]),
                                                  ("Seguimiento", d["seguimiento"]))]
    t = Table(tabla, colWidths=[4 * cm, 13 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F7")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    items += [t, Spacer(1, 10), P("Resultado de Audita Análisis", "Heading3"), P(d["resultado"])]
    h = d["hallazgo"]
    if h:
        items += [Spacer(1, 8), P(f"Hallazgo {h.ref_local}: {h.titulo}", "Heading3")]
        for et, v in (("Condición", h.condicion), ("Criterio", h.criterio), ("Causa", h.causa), ("Efecto", h.efecto), ("Recomendación", h.recomendacion)):
            items.append(Paragraph(f"<b>{et}:</b> {escape(v or '')}", st["BodyText"]))
    doc.build(items)
    return buf.getvalue()
