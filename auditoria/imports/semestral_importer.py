from datetime import datetime
import traceback
from audits.models import Audit
from auditoria.models import BalanceCuentas

__all__ = ["process_semestral_sheet"]

def process_semestral_sheet(sheet, audit_id):
    """Procesa la hoja de estados financieros semestrales (4 columnas de valores)."""
    try:
        current_section = None
        fechas_globales = []
        audit_instance = Audit.objects.get(pk=audit_id)

        for row in sheet.iter_rows(min_row=2, values_only=True):
            row5 = row[:5]
            primera_columna = str(row5[0]).strip() if row5[0] is not None else ""

            if primera_columna in [
                "CUENTA",
                "Fecha corte año anterior",
                "Fecha corte año actual",
                "TOTAL ACTIVO",
                "TOTAL PASIVO",
                "TOTAL PATRIMONIO",
            ]:
                continue

            es_valor_numerico = any(isinstance(x, (int, float)) for x in row5[1:])
            if (
                primera_columna in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]
                and not es_valor_numerico
            ):
                current_section = primera_columna
                if current_section == "Activo":
                    fechas_globales = []
                    for cell in row5[1:5]:
                        if isinstance(cell, str) and cell.strip().lower().startswith("al "):
                            raw = cell.replace("Al ", "").strip()
                            try:
                                fechas_globales.append(datetime.strptime(raw, "%d/%m/%Y").date())
                            except Exception:
                                fechas_globales.append(None)
                        else:
                            fechas_globales.append(None)
                continue

            if current_section is None:
                continue

            valores = []
            for valor in row5[1:5]:
                try:
                    valores.append(float(valor) if valor is not None else None)
                except (ValueError, TypeError):
                    valores.append(None)

            if all(v is None for v in valores):
                continue

            nombre_cuenta = primera_columna
            if not fechas_globales or all(f is None for f in fechas_globales):
                continue

            tipo_balance = "SEMESTRAL"
            tipo_cuenta = "NT"

            for valor, fecha in zip(valores, fechas_globales):
                if valor is not None and fecha is not None:
                    BalanceCuentas.objects.create(
                        audit=audit_instance,
                        tipo_balance=tipo_balance,
                        fecha_corte=fecha,
                        seccion=current_section,
                        nombre_cuenta=nombre_cuenta,
                        tipo_cuenta=tipo_cuenta,
                        valor=valor,
                    )
        return True
    except Exception:
        traceback.print_exc()
        return False
