"""Los cuatro agentes de Audita Análisis: datos masivos, predictivo, fraudes y contratos."""
from . import contratos, fraudes, masivo, predictivo
from .common import (
    AGENTES, NIA_AGENTE, AgentContext, AgentError, ColumnMap, build_aux_rows, detect_columns, resolve_columns,
)

RUNNERS = {
    "masivo": masivo.run,
    "predictivo": predictivo.run,
    "fraudes": fraudes.run,
    "contratos": contratos.run,
}

__all__ = [
    "AGENTES", "NIA_AGENTE", "RUNNERS", "AgentContext", "AgentError", "ColumnMap",
    "build_aux_rows", "detect_columns", "resolve_columns",
]
