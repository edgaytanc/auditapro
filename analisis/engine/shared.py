"""Tipos compartidos por el motor y su serialización a JSON.

``Fig`` es una cifra con su origen (archivo, hoja, fila(s) o página y coordenadas).
Las tablas se guardan en la base de datos como JSON para poder volver a pegarlas en el
papel de trabajo sin recalcular.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

# Tope de filas por tabla guardada/pegada. El resto se resume en ``truncated``.
MAX_TABLE_ROWS = 1000
# Una cifra agregada guarda sus filas solo si son pocas; si no, guarda cómo recalcularla.
MAX_FIG_ROWS = 50


@dataclass
class Fig:
    """Cifra con trazabilidad. ``value`` es lo que se escribe en el papel de trabajo."""

    value: Any
    doc: str = ""
    sheet: str = ""
    page: int | None = None
    rows: list[int] = field(default_factory=list)
    agg: dict | None = None
    bbox: dict | None = None
    label: str = ""
    kind: str = "importe"  # importe | conteo | porcentaje
    col: int | None = None  # índice de la columna del importe en la hoja de origen
    fid: str = ""  # C-0001, asignado al guardar la corrida

    def origin(self) -> str:
        if self.page is not None:
            return f"{self.doc} · pág. {self.page}"
        if self.rows:
            shown = ", ".join(str(r) for r in self.rows[:3])
            more = f"… ({len(self.rows)})" if len(self.rows) > 3 else ""
            label = "fila" if len(self.rows) == 1 else "filas"
            return f"{self.doc} · {label} {shown}{more}"
        if self.agg:
            return f"{self.doc} · {self.agg.get('count', 'varias')} filas"
        return self.doc


@dataclass
class Table:
    key: str
    title: str
    head: list[str]
    rows: list[list] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)  # '', ok, error, warn, total
    note: str = ""
    truncated: int = 0
    flagged: bool = False

    def add(self, cells: list, flag: str = "") -> None:
        self.rows.append(cells)
        self.flags.append(flag)

    def cap(self, limit: int = MAX_TABLE_ROWS) -> None:
        """Recorta filas sin perder las de total ni contarlas mal."""
        if len(self.rows) <= limit:
            return
        keep = [i for i, f in enumerate(self.flags) if f == "total"]
        head_idx = [i for i in range(len(self.rows)) if i not in keep][: max(limit - len(keep), 0)]
        order = sorted(head_idx + keep)
        self.truncated += len(self.rows) - len(order)
        self.rows = [self.rows[i] for i in order]
        self.flags = [self.flags[i] for i in order]


@dataclass
class Finding:
    """Formato común de resultado de los agentes (documento del Orquestador, §4)."""

    agent: str
    kind: str  # hallazgo | riesgo | excepcion
    procedimiento: str
    resultado: str
    alerta: str = "Media"  # Alta | Media | Baja
    codigo: str = ""  # R-01 / H-01, asignado al consolidar
    importe: Decimal | None = None
    fecha: date | None = None
    origen: str = ""
    nia: str = ""
    aseveracion: str = ""
    condicion: str = ""
    criterio: str = ""
    causa: str = "Por confirmar con la gerencia"
    efecto: str = ""
    recomendacion: str = ""
    destino_pt: str = ""


@dataclass
class AgentOutput:
    agent: str
    main: Table
    extras: list[Table] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    conclusion: str = ""
    warnings: list[str] = field(default_factory=list)
    exceptions: int = 0


# --------------------------------------------------------------------------- JSON

def enc(value: Any) -> Any:
    """Codifica una celda a JSON conservando Decimal, date y Fig."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return {"$d": str(value)}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, Fig):
        return {
            "$fig": {
                "value": enc(value.value),
                "doc": value.doc,
                "sheet": value.sheet,
                "page": value.page,
                "rows": value.rows,
                "agg": value.agg,
                "bbox": value.bbox,
                "label": value.label,
                "kind": value.kind,
                "col": value.col,
                "fid": value.fid,
            }
        }
    return str(value)


def dec(value: Any) -> Any:
    if isinstance(value, dict):
        if "$d" in value:
            return Decimal(value["$d"])
        if "$date" in value:
            return date.fromisoformat(value["$date"])
        if "$fig" in value:
            f = value["$fig"]
            return Fig(
                value=dec(f["value"]),
                doc=f.get("doc", ""),
                sheet=f.get("sheet", ""),
                page=f.get("page"),
                rows=f.get("rows") or [],
                agg=f.get("agg"),
                bbox=f.get("bbox"),
                label=f.get("label", ""),
                kind=f.get("kind", "importe"),
                col=f.get("col"),
                fid=f.get("fid", ""),
            )
    return value


def table_to_dict(table: Table) -> dict:
    return {
        "key": table.key,
        "title": table.title,
        "head": table.head,
        "rows": [[enc(c) for c in row] for row in table.rows],
        "flags": table.flags,
        "note": table.note,
        "truncated": table.truncated,
        "flagged": table.flagged,
    }


def table_from_dict(data: dict) -> Table:
    return Table(
        key=data["key"],
        title=data["title"],
        head=data["head"],
        rows=[[dec(c) for c in row] for row in data["rows"]],
        flags=data.get("flags") or [""] * len(data["rows"]),
        note=data.get("note", ""),
        truncated=data.get("truncated", 0),
        flagged=data.get("flagged", False),
    )


def plain(cell: Any) -> Any:
    """Valor visible de una celda (desenvuelve ``Fig``)."""
    return cell.value if isinstance(cell, Fig) else cell
