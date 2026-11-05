"""Lógica de negocio de Audita Análisis fuera de las vistas: acceso, subida, llenado,
validación, aprobación y exportación."""
from __future__ import annotations

import csv
import io
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from audits.models import Audit

from .engine.normalize import fmt_money, parse_amount, parse_date
from .engine.readers import Limits, read_document
from .engine.shared import table_from_dict
from .engine.template_fill import FillError, PasteOptions, fill_template
from .models import (
    BitacoraAnalisis,
    CifraAnalisis,
    CorridaAnalisis,
    DocumentoAnalisis,
    HallazgoAnalisis,
    VersionPapel,
)
from .validators import UploadLimits, UploadRejected, sha256_of, validate_saved_file


class PasteError(Exception):
    """No se pudo llenar el papel de trabajo."""


class ApprovalError(Exception):
    """No se puede aprobar o rechazar en este estado."""


# --------------------------------------------------------------------------- acceso

def role_name(user) -> str:
    return getattr(getattr(user, "role", None), "name", "") or ""


def accessible_audits(user):
    """Auditorías en las que el usuario puede trabajar (mismo criterio que el resto de AuditaPro)."""
    if not user.is_authenticated:
        return Audit.objects.none()
    if user.is_staff:
        return Audit.objects.all()
    role = role_name(user)
    if role == "audit_manager":
        return Audit.objects.filter(audit_manager=user)
    if role in ("auditor", "supervisor"):
        return Audit.objects.filter(assigned_users=user)
    return Audit.objects.none()


def accessible_runs(user):
    return CorridaAnalisis.objects.filter(audit__in=accessible_audits(user)).select_related("audit", "creado_por")


def can_approve(user, run: CorridaAnalisis) -> bool:
    """Solo el jefe de auditoría de ese proyecto (o personal administrador) aprueba."""
    return bool(user.is_staff or (role_name(user) == "audit_manager" and run.audit.audit_manager_id == user.pk))


# --------------------------------------------------------------------------- subida

def save_upload(run: CorridaAnalisis, upload, rol: str, limits: UploadLimits | None = None) -> DocumentoAnalisis:
    """Guarda un archivo en el almacenamiento privado y lo valida; si falla, no queda nada."""
    limits = limits or UploadLimits.from_settings()
    doc = DocumentoAnalisis(corrida=run, rol=rol, nombre_original=Path(upload.name).name[:255], tamano=upload.size, formato="", sha256="")
    doc.archivo.save(upload.name, upload, save=False)
    try:
        doc.formato = validate_saved_file(doc.archivo.path, doc.nombre_original, limits)
        doc.sha256 = sha256_of(doc.archivo.path)
        if rol == DocumentoAnalisis.Rol.PLANTILLA and doc.formato != "excel":
            raise UploadRejected("El papel de trabajo debe ser un Excel (.xlsx o .xlsm).")
    except UploadRejected:
        doc.archivo.delete(save=False)
        raise
    doc.save()
    return doc


def create_run(user, audit: Audit, *, titulo: str, instruccion: str, agentes: list[str], parametros: dict,
               plantilla, auxiliares: list, soportes: list) -> CorridaAnalisis:
    """Crea la corrida con todos sus archivos o falla sin dejar archivos huérfanos."""
    limits = UploadLimits.from_settings()
    uploads = [(f, DocumentoAnalisis.Rol.PLANTILLA) for f in ([plantilla] if plantilla else [])]
    uploads += [(f, DocumentoAnalisis.Rol.AUXILIAR) for f in auxiliares]
    uploads += [(f, DocumentoAnalisis.Rol.SOPORTE) for f in soportes]
    if not uploads:
        raise UploadRejected("Suba al menos un archivo para analizar.")
    if len(uploads) > limits.max_files:
        raise UploadRejected(f"Se permiten hasta {limits.max_files} archivos por análisis.")
    total = sum(f.size for f, _ in uploads)
    if total > limits.max_total_bytes:
        raise UploadRejected(f"Los archivos suman más del máximo de {limits.max_total_bytes // (1024 * 1024)} MB por análisis.")
    for f, _ in uploads:
        if f.size > limits.max_file_bytes:
            raise UploadRejected(f"{f.name} supera el máximo de {limits.max_file_bytes // (1024 * 1024)} MB por archivo.")

    run = CorridaAnalisis.objects.create(
        audit=audit, creado_por=user, titulo=titulo[:200], instruccion=instruccion, agentes_solicitados=agentes,
        parametros=parametros,
    )
    try:
        for f, rol in uploads:
            save_upload(run, f, rol, limits)
    except UploadRejected:
        for d in run.documentos.all():
            d.archivo.delete(save=False)
        run.delete()
        raise
    BitacoraAnalisis.registrar(
        run, user, "creada",
        {"archivos": [{"nombre": d.nombre_original, "rol": d.rol, "sha256": d.sha256} for d in run.documentos.all()]},
    )
    return run


# --------------------------------------------------------------------------- pegar en el papel

def default_paste_options() -> PasteOptions:
    return PasteOptions()


def _summary_line(run: CorridaAnalisis) -> str:
    kpis = run.resumen.get("kpis", [])
    return "Resumen: " + " · ".join(f"{k} {v}" for k, v in kpis)


def _structure_data(run: CorridaAnalisis, data: dict) -> dict | None:
    """Datos para llenar la tabla propia del papel (integración, cuadre contra el mayor y observaciones)."""
    if "integracion" not in data["tablas"]:
        return None
    ledger = parse_amount(run.parametros.get("saldo_mayor")) if run.parametros.get("saldo_mayor") not in (None, "") else None
    # hallazgos concretos primero (por nivel), luego riesgos; nunca los descartados por el auditor
    nivel = {"Alta": 0, "Media": 1, "Baja": 2}
    items = [h for h in run.hallazgos.all() if h.codigo and h.decision != HallazgoAnalisis.Decision.DESCARTADO]
    items.sort(key=lambda h: (h.tipo != "hallazgo", nivel.get(h.alerta, 3), h.orden))
    observations = [f"• {h.codigo} ({h.alerta}): {h.resultado}"[:220] for h in items]
    return {
        "detail": table_from_dict(data["tablas"]["integracion"]),
        "monthly": table_from_dict(data["tablas"]["integracion_mes"]) if "integracion_mes" in data["tablas"] else None,
        "ledger_total": ledger,
        "observations": observations,
        "source": table_from_dict(data["tablas"]["integracion_fuente"]) if "integracion_fuente" in data["tablas"] else None,
        "source_name": data["tablas"]["integracion_fuente"]["title"].split("·", 1)[-1].strip() if "integracion_fuente" in data["tablas"] else "",
    }


@transaction.atomic
def paste_to_template(run: CorridaAnalisis, options: PasteOptions, user, motivo: str = "", during_run: bool = False) -> VersionPapel:
    """Escribe los resultados en una copia del papel de trabajo y la guarda como nueva versión."""
    tpl = run.plantilla
    if not tpl:
        raise PasteError("Esta corrida no tiene un papel de trabajo para llenar.")
    if run.estado != CorridaAnalisis.Estado.TERMINADO and not during_run:
        raise PasteError("El análisis aún no termina.")
    if run.revision == CorridaAnalisis.Revision.APROBADO:
        raise PasteError("El resultado ya está aprobado: no se puede volver a pegar.")

    data = run.tablas
    keys = [k for k in data["orden"] if k not in ("clasificacion", "extraccion", "integracion", "integracion_mes", "integracion_fuente")]
    tables = [table_from_dict(data["tablas"][k]) for k in keys]
    evidence = [
        [r[0], r[1], r[2], r[3], r[4] if not hasattr(r[4], "isoformat") else r[4].strftime("%d/%m/%Y"), r[5], ""]
        for r in (table_from_dict(data["tablas"]["extraccion"]).rows if "extraccion" in data["tablas"] else [])
    ]
    names = ", ".join(d.nombre_original for d in run.documentos.exclude(rol=DocumentoAnalisis.Rol.PLANTILLA))
    agents = ", ".join(a["name"] for a in run.plan.get("agents", []) if a["active"])
    sources = (
        f"Fuentes: {names} · Agentes: {agents or '—'} · Generado por Audita Análisis "
        f"{timezone.now():%d/%m/%Y %H:%M} · Pendiente de revisión del auditor"
    )
    number = (run.versiones.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
    stem = Path(tpl.nombre_original).stem
    ext = Path(tpl.nombre_original).suffix.lower()
    name = f"{stem}_llenado{'' if number == 1 else f'_v{number}'}{ext}"

    original_sha = sha256_of(tpl.archivo.path)
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / name
        try:
            report = fill_template(
                tpl.archivo.path, out_path, tables=tables, conclusion=run.conclusion, summary_line=_summary_line(run),
                sources_line=sources, evidence_rows=evidence,
                evidence_note=f"Clasificación: {len(data['tablas']['clasificacion']['rows'])} secciones de {run.documentos.count() - 1} documentos",
                options=options,
                structure=_structure_data(run, data),
            )
        except FillError as exc:
            raise PasteError(str(exc)) from None
        version = VersionPapel(
            corrida=run, numero=number, nombre=name, sha256=sha256_of(out_path), hoja=report.sheet,
            celda_inicio=report.start_cell, motivo=motivo[:200], creado_por=user if getattr(user, "pk", None) else None,
            informe={
                "celdas_escritas": report.cells_written, "formulas_sobrescritas": report.formulas_overwritten,
                "hoja_evidencia": report.evidence_sheet, "movido_desde": report.moved_from, "advertencias": report.warnings,
                "rango": f"{report.start_cell}:{report.end_cell}",
                "estructura": report.structure,
            },
        )
        with out_path.open("rb") as fh:
            version.archivo.save(name, File(fh), save=False)
        version.save()

    if sha256_of(tpl.archivo.path) != original_sha or original_sha != tpl.sha256:
        raise PasteError("El archivo original cambió durante el proceso; se canceló por seguridad.")

    # destinos de cada cifra y de cada hallazgo en el papel de trabajo
    by_fid = {c.fid: c for c in run.cifras.all()}
    updated = []
    for rec in report.figures:
        c = by_fid.get(rec.fig.fid)
        if c:
            c.hoja_destino, c.celda = rec.sheet, rec.cell
            updated.append(c)
    CifraAnalisis.objects.bulk_update(updated, ["hoja_destino", "celda"])

    placed: dict[str, str] = {}
    for key in ("riesgos", "hallazgos"):
        if key in report.addresses:
            table = table_from_dict(data["tablas"][key])
            for row, addr in zip(table.rows, report.addresses[key]):
                placed[str(row[0])] = addr
    findings = list(run.hallazgos.all())
    for f in findings:
        addr = placed.get(f.codigo)
        f.destino_pt = addr or "⚑ Revisión"
        f.marcado_revision = addr is None
    HallazgoAnalisis.objects.bulk_update(findings, ["destino_pt", "marcado_revision"])

    BitacoraAnalisis.registrar(
        run, user, "pegado",
        {"version": number, "archivo": name, "sha256": version.sha256, "hoja": report.sheet, "celda": report.start_cell,
         "original_sha256": original_sha, "formulas_sobrescritas": report.formulas_overwritten},
    )
    return version


# --------------------------------------------------------------------------- validación de cifras

TOLERANCE = Decimal("0.005")


class _Source:
    """Relee los archivos originales una sola vez para comparar cada cifra con su origen."""

    def __init__(self, run: CorridaAnalisis):
        self.docs = {}
        for d in run.documentos.exclude(rol=DocumentoAnalisis.Rol.PLANTILLA):
            self.docs.setdefault(d.nombre_original, d)
        self._read: dict[str, object] = {}
        self._rows: dict[tuple, dict[int, list]] = {}
        self._groups: dict[tuple, dict[str, Decimal]] = {}
        self._months: dict[tuple, dict[str, Decimal]] = {}
        self._total: dict[tuple, Decimal] = {}
        self._changed: dict[str, bool] = {}

    def changed(self, name: str) -> bool:
        if name not in self._changed:
            d = self.docs[name]
            self._changed[name] = sha256_of(d.archivo.path) != d.sha256
        return self._changed[name]

    def source(self, name: str):
        if name not in self._read:
            d = self.docs[name]
            self._read[name] = read_document(d.archivo.path, d.nombre_original, Limits(max_rows=10**7, max_pdf_pages=10**4))
        return self._read[name]

    def tab(self, name: str, sheet: str):
        src = self.source(name)
        for t in src.tabular:
            if not sheet or t.sheet == sheet:
                return t
        return src.main_table

    def rows(self, name: str, sheet: str) -> dict[int, list]:
        key = (name, sheet)
        if key not in self._rows:
            t = self.tab(name, sheet)
            self._rows[key] = {r.n: r.values for r in t.rows} if t else {}
        return self._rows[key]

    @staticmethod
    def _amount(values, col):
        return parse_amount(values[col]) if col is not None and 0 <= col < len(values) else None

    def group_sums(self, name, sheet, group_col, amount_col) -> dict[str, Decimal]:
        key = (name, sheet, group_col, amount_col)
        if key not in self._groups:
            sums: dict[str, Decimal] = {}
            for values in self.rows(name, sheet).values():
                a = self._amount(values, amount_col)
                if a is None:
                    continue
                g = values[group_col] if 0 <= group_col < len(values) else None
                g = str(g).strip() if g is not None else ""
                sums[g or "(sin dato)"] = sums.get(g or "(sin dato)", Decimal(0)) + a
            self._groups[key] = sums
        return self._groups[key]

    def month_sums(self, name, sheet, date_col, amount_col) -> dict[str, Decimal]:
        key = (name, sheet, date_col, amount_col)
        if key not in self._months:
            sums: dict[str, Decimal] = {}
            for values in self.rows(name, sheet).values():
                a = self._amount(values, amount_col)
                d = parse_date(values[date_col]) if 0 <= date_col < len(values) else None
                if a is None or d is None:
                    continue
                k = f"{d.year}-{d.month:02d}"
                sums[k] = sums.get(k, Decimal(0)) + a
            self._months[key] = sums
        return self._months[key]

    def total(self, name, sheet, amount_col) -> Decimal:
        key = (name, sheet, amount_col)
        if key not in self._total:
            total = Decimal(0)
            for values in self.rows(name, sheet).values():
                a = self._amount(values, amount_col)
                if a is not None:
                    total += a
            self._total[key] = total
        return self._total[key]

    def page_has_amount(self, name: str, page: int, value: Decimal) -> bool:
        from .engine.extract import _ANY_AMOUNT

        src = self.source(name)
        for p in src.pages:
            if p.number == page:
                for m in _ANY_AMOUNT.finditer(p.text):
                    a = parse_amount(m.group(1))
                    if a is not None and abs(a - value) <= TOLERANCE:
                        return True
        return False


def _check(src: _Source, c: CifraAnalisis) -> tuple[str, str]:
    name = c.documento_nombre
    if name not in src.docs:
        return CifraAnalisis.Estado.SIN_ORIGEN, "El documento de origen ya no está en el expediente"
    if src.changed(name):
        return CifraAnalisis.Estado.CAMBIO, "El archivo de origen cambió desde el análisis: vuelva a ejecutar"
    value = c.valor.quantize(Decimal("0.01"))
    agg = c.agregacion or {}
    if c.pagina is not None:
        if src.page_has_amount(name, c.pagina, value):
            return CifraAnalisis.Estado.VERIFICADA, f"Se relee en {name}, pág. {c.pagina}"
        return CifraAnalisis.Estado.NO_CUADRA, f"El importe no aparece en {name}, pág. {c.pagina}"
    amount_col = c.columna if c.columna is not None else agg.get("amount_col")
    if c.filas:
        rows = src.rows(name, c.hoja_origen)
        total = Decimal(0)
        for n in c.filas:
            values = rows.get(n)
            a = src._amount(values, amount_col) if values is not None else None
            if a is None:
                return CifraAnalisis.Estado.NO_CUADRA, f"La fila {n} ya no tiene un importe legible"
            total += a
        source_value = total
    elif agg:
        if "group" in agg:
            source_value = src.group_sums(name, c.hoja_origen, agg.get("group_col", 0), amount_col).get(agg["group"])
        elif "month" in agg:
            source_value = src.month_sums(name, c.hoja_origen, agg.get("date_col", -1), amount_col).get(agg["month"])
        else:
            source_value = src.total(name, c.hoja_origen, amount_col)
        if source_value is None:
            return CifraAnalisis.Estado.NO_CUADRA, "No se encontró el grupo o mes en el origen"
    else:
        return CifraAnalisis.Estado.SIN_ORIGEN, "La cifra no tiene fila ni página de origen"
    if abs(source_value - value) <= TOLERANCE:
        return CifraAnalisis.Estado.VERIFICADA, f"Recalculado desde el origen: {fmt_money(source_value)}"
    return CifraAnalisis.Estado.NO_CUADRA, f"Origen {fmt_money(source_value)} vs. cifra {fmt_money(value)}"


def validate_figures(run: CorridaAnalisis, user=None) -> dict:
    """Relee cada cifra desde su archivo de origen y la compara (guía §10.2)."""
    src = _Source(run)
    now = timezone.now()
    figures = list(run.cifras.all())
    for c in figures:
        c.estado, c.detalle = _check(src, c)
        c.verificada_en = now
    CifraAnalisis.objects.bulk_update(figures, ["estado", "detalle", "verificada_en"])
    summary = {
        "total": len(figures),
        "verificadas": sum(1 for c in figures if c.estado == CifraAnalisis.Estado.VERIFICADA),
        "cambio": sum(1 for c in figures if c.estado == CifraAnalisis.Estado.CAMBIO),
        "no_cuadran": sum(1 for c in figures if c.estado == CifraAnalisis.Estado.NO_CUADRA),
        "sin_origen": sum(1 for c in figures if c.estado == CifraAnalisis.Estado.SIN_ORIGEN),
        "validado_en": now.isoformat(),
    }
    run.resumen = {**run.resumen, "validacion": summary}
    run.save(update_fields=["resumen"])
    BitacoraAnalisis.registrar(run, user, "validacion", summary)
    return summary


# --------------------------------------------------------------------------- decisiones y aprobación

def decide_finding(finding: HallazgoAnalisis, user, decision: str, nota: str) -> None:
    if decision not in (HallazgoAnalisis.Decision.ACEPTADO, HallazgoAnalisis.Decision.DESCARTADO):
        raise ValueError("Decisión no válida.")
    if decision == HallazgoAnalisis.Decision.DESCARTADO and not nota.strip():
        raise ValueError("Para descartar un falso positivo escriba el motivo.")
    if finding.corrida.revision == CorridaAnalisis.Revision.APROBADO:
        raise ValueError("El resultado ya está aprobado.")
    finding.decision, finding.decision_nota = decision, nota.strip()
    finding.decidido_por, finding.decidido_en = user, timezone.now()
    finding.save(update_fields=["decision", "decision_nota", "decidido_por", "decidido_en"])
    BitacoraAnalisis.registrar(
        finding.corrida, user, "decision",
        {"hallazgo": finding.codigo, "decision": decision, "nota": nota.strip()},
    )


def approve_run(run: CorridaAnalisis, user, comentario: str = "") -> None:
    if not can_approve(user, run):
        raise ApprovalError("Solo el jefe de auditoría del proyecto puede aprobar.")
    if run.estado != CorridaAnalisis.Estado.TERMINADO:
        raise ApprovalError("El análisis aún no termina.")
    if run.revision == CorridaAnalisis.Revision.APROBADO:
        raise ApprovalError("Ya está aprobado.")
    summary = validate_figures(run, user)
    if summary["no_cuadran"] or summary["cambio"]:
        raise ApprovalError(
            f"No se puede aprobar: {summary['no_cuadran']} cifra(s) no cuadran y {summary['cambio']} cambiaron de origen."
        )
    run.revision = CorridaAnalisis.Revision.APROBADO
    run.aprobado_por, run.aprobado_en, run.revision_comentario = user, timezone.now(), comentario.strip()
    run.save(update_fields=["revision", "aprobado_por", "aprobado_en", "revision_comentario"])
    BitacoraAnalisis.registrar(run, user, "aprobada", {"comentario": comentario.strip()})


def reject_run(run: CorridaAnalisis, user, comentario: str) -> None:
    if not can_approve(user, run):
        raise ApprovalError("Solo el jefe de auditoría del proyecto puede rechazar.")
    if not comentario.strip():
        raise ApprovalError("Escriba el motivo del rechazo.")
    if run.revision == CorridaAnalisis.Revision.APROBADO:
        raise ApprovalError("Ya está aprobado.")
    run.revision = CorridaAnalisis.Revision.RECHAZADO
    run.revision_comentario = comentario.strip()
    run.save(update_fields=["revision", "revision_comentario"])
    BitacoraAnalisis.registrar(run, user, "rechazada", {"comentario": comentario.strip()})


# --------------------------------------------------------------------------- exportar

def _csv_safe(value) -> str:
    """Evita la inyección de fórmulas al abrir el CSV en Excel."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def results_csv(run: CorridaAnalisis) -> bytes:
    """CSV con ``;`` y UTF-8 con BOM para que Excel lo abra bien en español (guía del Portal §9.5)."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Código", "Tipo", "Agente", "Procedimiento", "Resultado", "Importe", "Origen", "Alerta", "NIA",
                     "Destino en el papel", "Decisión del auditor", "Nota"])
    for f in run.hallazgos.all():
        destino = "MARCADO PARA REVISIÓN" if f.marcado_revision else (f.destino_pt or "Sin papel de trabajo")
        writer.writerow(
            [_csv_safe(x) for x in (
                f.codigo, f.tipo, f.agente, f.procedimiento, f.resultado, f"{f.importe:.2f}" if f.importe is not None else "",
                f.origen, f.alerta, f.nia, destino, f.get_decision_display(), f.decision_nota,
            )]
        )
    return ("﻿" + buf.getvalue()).encode("utf-8")
