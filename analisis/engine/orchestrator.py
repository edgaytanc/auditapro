"""Orquestador: reconoce el papel de trabajo y decide qué agentes activar y por qué.

Reglas (documento «Orquestador Inteligente», §2 y §5; guía del Portal del Cliente, §5.2 y §9):
- Se elige por el objetivo y los procedimientos del papel, no solo por el nombre del archivo.
- No se activa el Predictivo por defecto si el papel solo necesita una conciliación aritmética.
- Cada agente queda «activo» (con lo que hará) o «no se usa» (con la razón).
- «Informes» no es un quinto agente: la consolidación la hace ``consolidate.py`` (la guía del
  Portal propone mantenerlo dentro del asistente de Cierre).
- El auditor puede forzar los agentes; el orquestador solo sugiere.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .agents.common import AGENTES


@dataclass
class PaperKind:
    code: str
    ref: str
    label: str
    keywords: list[re.Pattern]
    agents: list[str]
    not_used: dict[str, str] = field(default_factory=dict)


def _kw(*patterns: str) -> list[re.Pattern]:
    return [re.compile(p, re.I) for p in patterns]


KINDS: list[PaperKind] = [
    PaperKind(
        "cxc", "C-2", "Cuentas por cobrar — antigüedad y estimación de deterioro",
        _kw(r"cobrar", r"cartera", r"clientes", r"antig[uü]edad", r"deterioro"),
        ["masivo", "predictivo"],
        {"fraudes": "Sin pagos ni proveedores que examinar", "contratos": "Sin contratos que revisar"},
    ),
    PaperKind(
        "bancos", "A-3", "Conciliaciones bancarias",
        _kw(r"\bbanc", r"concilia"),
        ["masivo"],
        {"predictivo": "La conciliación es aritmética: no necesita tendencias",
         "fraudes": "Solo si aparecen partidas inusuales", "contratos": "Sin contratos que revisar"},
    ),
    PaperKind(
        "pagos", "P-1", "Revisión de pagos y proveedores",
        _kw(r"pagos?\b", r"proveedor", r"cuentas por pagar", r"duplicad"),
        ["masivo", "fraudes"],
        {"predictivo": "No se requieren tendencias para revisar los pagos",
         "contratos": "Se activa si se suben contratos"},
    ),
    PaperKind(
        "contratos", "L-1", "Contratos y arrendamientos (NIIF 16)",
        _kw(r"contrat", r"arrend", r"pr[eé]stamo"),
        ["contratos", "masivo"],
        {"predictivo": "No se requieren tendencias", "fraudes": "Se activa si hay pagos fuera de contrato"},
    ),
    PaperKind(
        "deprec", "F-2", "Propiedad, planta y equipo — depreciación",
        _kw(r"deprecia", r"propiedad,? planta", r"activos? fijos?", r"\bppe\b"),
        ["masivo"],
        {"predictivo": "El recálculo de la depreciación es aritmético",
         "fraudes": "Sin transacciones que examinar", "contratos": "Sin contratos que revisar"},
    ),
    PaperKind(
        "ef", "B-1", "Procedimientos analíticos de estados financieros",
        _kw(r"estados? financieros?", r"balance", r"resultados?\b", r"anal[ií]tic"),
        ["masivo", "predictivo"],
        {"fraudes": "Sin transacciones que examinar", "contratos": "Sin contratos que revisar"},
    ),
    PaperKind(
        "usuarios", "CI-3", "Accesos al sistema contable",
        _kw(r"usuarios?\b", r"accesos?\b", r"perfil"),
        ["masivo", "fraudes"],
        {"predictivo": "Sin series de tiempo que proyectar", "contratos": "Sin contratos que revisar"},
    ),
    PaperKind(
        "actas", "AP-4", "Lectura de actas",
        _kw(r"\bactas?\b"),
        ["contratos"],
        {"masivo": "Sin datos tabulares", "predictivo": "Sin datos tabulares", "fraudes": "Sin datos tabulares"},
    ),
]

_REQUEST_RULES: dict[str, re.Pattern] = {
    "fraudes": re.compile(r"duplic|fraud|fantasma|irregular|inusual|fracciona|at[ií]pic|benford|banderas?", re.I),
    "predictivo": re.compile(r"tendenc|proyec|predic|estimaci|presupuesto|desviaci|expectativa", re.I),
    "contratos": re.compile(r"contrat|cl[aá]usula|vigencia|arrend|penaliz|vencimiento", re.I),
    "masivo": re.compile(r"cruce|concilia|sumaria|auxiliar|integra|mayor\b|poblaci|cotej|masiv", re.I),
}

ACTIVE_REASON = {
    "masivo": "Cruza y resume el 100 % del auxiliar contra los documentos",
    "predictivo": "Calcula la tendencia mensual, las desviaciones y la proyección",
    "fraudes": "Busca duplicados, atípicos, montos redondos, fines de semana y Benford",
    "contratos": "Revisa vigencias, cláusulas de riesgo y gasto contra contrato",
}

STEPS = [
    ("Clasificar", "Reconoce la plantilla, los procedimientos y el tamaño de los archivos"),
    ("Planificar", "Selecciona los agentes necesarios y define el orden"),
    ("Ejecutar", "Cada agente devuelve resultados con un formato común"),
    ("Integrar en el papel de trabajo", "Completa una copia del Excel sin tocar el original ni las fórmulas"),
    ("Validar archivo", "Comprueba que el Excel abre y conserva hojas, encabezados y fórmulas"),
]


@dataclass
class PlanItem:
    agent: str
    active: bool
    reason: str


@dataclass
class Plan:
    kind_code: str = ""
    kind_label: str = ""
    kind_ref: str = ""
    confidence: float = 0.0
    candidates: list[dict] = field(default_factory=list)
    items: list[PlanItem] = field(default_factory=list)
    needs_confirmation: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def active_agents(self) -> list[str]:
        return [i.agent for i in self.items if i.active]

    def to_dict(self) -> dict:
        return {
            "kind_code": self.kind_code,
            "kind_label": self.kind_label,
            "kind_ref": self.kind_ref,
            "confidence": round(self.confidence, 2),
            "candidates": self.candidates,
            "agents": [{"agent": i.agent, "name": AGENTES[i.agent], "active": i.active, "reason": i.reason} for i in self.items],
            "needs_confirmation": self.needs_confirmation,
            "notes": self.notes,
            "steps": [{"title": t, "detail": d} for t, d in STEPS],
        }


def recognize_kind(text: str) -> tuple[PaperKind | None, float, list[dict]]:
    """Puntaje por coincidencias (no «gana el primero»); el auditor confirma si es dudoso."""
    scored = []
    for kind in KINDS:
        hits = sum(1 for rx in kind.keywords if rx.search(text))
        if hits:
            scored.append((hits, kind))
    scored.sort(key=lambda t: -t[0])
    if not scored:
        return None, 0.0, []
    best_hits, best = scored[0]
    second_hits = scored[1][0] if len(scored) > 1 else 0
    confidence = min(0.95, 0.4 + 0.15 * best_hits) - (0.2 if second_hits == best_hits else 0.0)
    return best, max(confidence, 0.2), [{"ref": k.ref, "label": k.label, "score": h} for h, k in scored[:3]]


def build_plan(
    *,
    context_text: str,
    request: str = "",
    requested_agents: list[str] | None = None,
    has_tabular: bool,
    has_dates: bool,
    has_amounts: bool,
    contract_docs: int = 0,
) -> Plan:
    plan = Plan()
    kind, confidence, candidates = recognize_kind(f"{context_text}\n{request}")
    if kind:
        plan.kind_code, plan.kind_label, plan.kind_ref = kind.code, kind.label, kind.ref
        plan.confidence = confidence
        plan.candidates = candidates
        plan.needs_confirmation = confidence < 0.6
        if plan.needs_confirmation:
            plan.notes.append("El tipo de papel no es del todo claro: confirme los agentes sugeridos.")
    else:
        plan.notes.append("No se reconoció el tipo de papel: los agentes se eligen por los datos y la instrucción.")
        plan.needs_confirmation = True

    wanted: dict[str, str] = {}
    if requested_agents:
        for agent in requested_agents:
            if agent in AGENTES:
                wanted[agent] = "Elegido por el auditor"
    else:
        if kind:
            for agent in kind.agents:
                wanted[agent] = f"Papel {kind.ref}: {ACTIVE_REASON[agent].lower()}"
        for agent, rx in _REQUEST_RULES.items():
            if rx.search(request or "") and agent not in wanted:
                wanted[agent] = f"Lo pide la instrucción: {ACTIVE_REASON[agent].lower()}"
        if contract_docs and "contratos" not in wanted:
            wanted["contratos"] = "Se subieron contratos: " + ACTIVE_REASON["contratos"].lower()
        if not wanted:
            if has_tabular:
                wanted["masivo"] = "Agente por defecto para auxiliares: " + ACTIVE_REASON["masivo"].lower()
            elif contract_docs:
                wanted["contratos"] = ACTIVE_REASON["contratos"]

    # compuertas: un agente sin los datos que necesita no corre (y se explica por qué)
    blocked: dict[str, str] = {}
    if not has_tabular and not contract_docs:
        blocked = {a: "No hay un auxiliar en Excel/CSV ni contratos que analizar" for a in AGENTES}
    else:
        if not (has_tabular and has_amounts):
            for a in ("masivo", "predictivo", "fraudes"):
                blocked[a] = "El auxiliar no tiene una columna de importes reconocible"
        if not has_dates:
            blocked["predictivo"] = "No hay columna de fecha para armar la serie mensual"
        if not has_dates and not contract_docs:
            blocked["contratos"] = "Sin fecha de vencimiento ni contratos en PDF/Word"

    for agent in AGENTES:
        if agent in wanted and agent not in blocked:
            plan.items.append(PlanItem(agent, True, wanted[agent]))
        elif agent in wanted:
            plan.items.append(PlanItem(agent, False, f"No se puede ejecutar: {blocked[agent]}"))
            plan.notes.append(f"{AGENTES[agent]}: {blocked[agent]}.")
        else:
            reason = (kind.not_used.get(agent) if kind else None) or "No es necesario para este papel"
            plan.items.append(PlanItem(agent, False, reason))
    return plan
