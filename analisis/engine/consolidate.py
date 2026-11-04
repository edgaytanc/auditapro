"""Consolidación (el «Informes» del orquestador): hallazgos comunes, tablas de riesgos y
hallazgos, indicadores de resumen y conclusión. Todo determinístico."""
from __future__ import annotations

from decimal import Decimal

from .agents.common import ALTA, BAJA, MEDIA, CAUSA_PENDIENTE, finding
from .crossmatch import CruceRow
from .normalize import fmt_money, q2
from .shared import Finding, Table

RH_NOTE = (
    "Nivel preliminar según las reglas del agente. El auditor valora el riesgo (NIA 315), concluye "
    "sobre cada hallazgo y decide si es una incorrección (NIA 450) o una deficiencia a comunicar "
    "(NIA 265). La causa siempre se confirma con la gerencia. Una alerta no demuestra fraude ni error."
)

RIESGO_HEAD = ["ID", "Riesgo", "NIA", "Aseveración", "Nivel", "Qué lo origina", "Respuesta del auditor", "Ref. origen"]
HALLAZGO_HEAD = ["ID", "Condición (qué se encontró)", "Criterio (NIA)", "Causa probable", "Efecto", "Recomendación", "Nivel", "Ref. origen"]
CRUCE_HEAD = ["N.º doc.", "Proveedor", "Importe doc.", "Estado", "Motivo", "Origen documento", "Origen auxiliar"]

_ORDER = {ALTA: 0, MEDIA: 1, BAJA: 2}


def cruce_findings(cruce: list[CruceRow], source_name: str) -> list[Finding]:
    """Hallazgos comunes a todos los agentes: documentos que no cuadran con el auxiliar."""
    bad = [c for c in cruce if c.estado == "no_cuadra"]
    if not bad:
        return []
    out = []
    for c in bad[:5]:
        amount = c.total or Decimal(0)
        out.append(
            finding(
                "cruce", "hallazgo", f"Documento {c.numero or '(s/n)'} no cuadra con el auxiliar",
                f"Documento {c.numero or '(s/n)'} ({c.proveedor or 'sin proveedor'}) por {fmt_money(amount)}: {c.motivo.lower()}",
                ALTA, importe=amount, nia="NIA 500 · NIA 450", aseveracion="Integridad · Corte · Exactitud",
                condicion=f"Documento {c.numero or '(s/n)'} por {fmt_money(amount)}: {c.motivo.lower()}",
                criterio="NIA 500: la información debe ser fiable y estar respaldada · NIA 450: acumular las incorrecciones",
                causa=f"{CAUSA_PENDIENTE} (registro omitido, fuera de período o error de captura)",
                efecto=fmt_money(amount),
                recomendacion="Pedir el soporte y el asiento; evaluar si es incorrección y si afecta el corte",
                origen=f"{c.doc_name} · pág. {c.page} / " + (f"{source_name} · fila {c.aux_row}" if c.aux_row else "sin fila en el auxiliar"),
            )
        )
    if len(bad) > 5:
        rest = sum((c.total or Decimal(0) for c in bad[5:]), Decimal(0))
        out.append(
            finding(
                "cruce", "hallazgo", f"{len(bad) - 5} documentos más no cuadran con el auxiliar",
                f"{len(bad) - 5} documentos más no cuadran con el auxiliar (ver el cruce, sección A)", MEDIA, importe=rest,
                nia="NIA 500 · NIA 450", condicion=f"{len(bad) - 5} documentos adicionales con diferencias",
                criterio="NIA 500 · NIA 450", causa=CAUSA_PENDIENTE, efecto=fmt_money(rest),
                recomendacion="Aplicar el mismo tratamiento a cada documento", origen="Cruce documento ↔ auxiliar",
            )
        )
    ratio = len(bad) / len(cruce)
    out.append(
        finding(
            "cruce", "riesgo", "Documentos que no concuerdan con el auxiliar: integridad y corte",
            f"{len(bad)} de {len(cruce)} documentos no cuadran", ALTA if ratio > 0.25 else MEDIA,
            nia="NIA 315 · 330", aseveracion="Integridad · Corte · Exactitud", origen="Cruce documento ↔ auxiliar",
            recomendacion="Ampliar la prueba a esos documentos y pedir explicación a la gerencia (NIA 330)",
        )
    )
    return out


def findings_tables(findings: list[Finding]) -> tuple[Table, Table]:
    risks = [f for f in findings if f.kind == "riesgo"]
    halls = [f for f in findings if f.kind == "hallazgo"]
    risks.sort(key=lambda f: _ORDER.get(f.alerta, 3))
    halls.sort(key=lambda f: _ORDER.get(f.alerta, 3))
    tr = Table(key="riesgos", title="RIESGOS IDENTIFICADOS (NIA 315 · 330)", head=RIESGO_HEAD, note=RH_NOTE)
    for i, f in enumerate(risks, start=1):
        tr.add(
            [f"R-{i:02d}", f.procedimiento, f.nia, f.aseveracion, f.alerta, f.resultado, f.recomendacion, f.origen],
            "error" if f.alerta == ALTA else "warn" if f.alerta == MEDIA else "",
        )
    th = Table(key="hallazgos", title="HALLAZGOS (condición · criterio · causa · efecto · recomendación)", head=HALLAZGO_HEAD, note=RH_NOTE)
    for i, f in enumerate(halls, start=1):
        th.add(
            [f"H-{i:02d}", f.condicion or f.resultado, f.criterio, f.causa, f.efecto, f.recomendacion, f.alerta, f.origen],
            "error" if f.alerta == ALTA else "warn" if f.alerta == MEDIA else "",
        )
    for i, f in enumerate(risks, start=1):
        f.codigo = f"R-{i:02d}"
    for i, f in enumerate(halls, start=1):
        f.codigo = f"H-{i:02d}"
    return tr, th


def cruce_table(cruce: list[CruceRow], source_name: str) -> Table:
    t = Table(key="cruce", title="CRUCE DOCUMENTO ↔ AUXILIAR", head=CRUCE_HEAD)
    for c in cruce:
        t.add(
            [
                c.numero or "(s/n)", c.proveedor, c.fig or c.total, "Cuadra" if c.estado == "cuadra" else "No cuadra", c.motivo,
                f"{c.doc_name} · pág. {c.page}",
                f"{source_name} · fila {c.aux_row}" if c.aux_row else "",
            ],
            "ok" if c.estado == "cuadra" else "error",
        )
    t.flagged = any(f == "error" for f in t.flags)
    t.cap()
    return t


def summary_indicators(
    *, documents: int, sections: int, fields: int, cruce: list[CruceRow], exceptions: int,
    risks: int, hallazgos: int,
) -> list[tuple[str, object]]:
    ok = sum(1 for c in cruce if c.estado == "cuadra")
    bad = [c for c in cruce if c.estado == "no_cuadra"]
    unmatched = sum((c.total or Decimal(0) for c in bad), Decimal(0))
    return [
        ("Documentos", documents),
        ("Secciones clasificadas", sections),
        ("Datos extraídos", fields),
        ("Cuadran", ok),
        ("No cuadran", len(bad)),
        ("Excepciones del agente", exceptions),
        ("Monto documental sin cuadrar", q2(unmatched)),
        ("Riesgos identificados", risks),
        ("Hallazgos", hallazgos),
    ]


def conclusion_text(agent_conclusions: list[str], cruce: list[CruceRow]) -> str:
    text = " ".join(c for c in agent_conclusions if c)
    if cruce:
        bad = sum(1 for c in cruce if c.estado == "no_cuadra")
        text += f" En el cruce documental, {bad} de {len(cruce)} documentos no cuadran con el auxiliar."
    return text.strip()
