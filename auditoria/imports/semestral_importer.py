from datetime import datetime
import traceback
from audits.models import Audit
from auditoria.models import BalanceCuentas, AjustesReclasificaciones

__all__ = ["process_semestral_sheet"]

def process_semestral_sheet(sheet, audit_id):
    """Procesa la hoja de estados financieros semestrales con 6 columnas de valores
    (tres cortes del año anterior, una del año actual) y columnas de ajustes
    (Debe/Haber)."""
    try:
        current_section = None
        fechas_globales = []
        audit_instance = Audit.objects.get(pk=audit_id)

        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_vals = row[:7]  # A-G
            primera_columna = str(row_vals[0]).strip() if row_vals[0] is not None else ""

            if primera_columna in [
                "CUENTA",
                "Fecha corte año anterior",
                "Fecha corte año actual",
                "TOTAL ACTIVO",
                "TOTAL PASIVO",
                "TOTAL PATRIMONIO",
            ]:
                continue

            es_valor_numerico = any(isinstance(x, (int, float)) for x in row_vals[1:])
            if (
                primera_columna in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]
                and not es_valor_numerico
            ):
                current_section = primera_columna
                if current_section == "Activo":
                    fechas_globales = []
                    balance_idx = [1, 2, 3, 6]  # B, C, D, G
                    for idx in balance_idx:
                        cell = row_vals[idx] if idx < len(row_vals) else None
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

            balance_idx = [1, 2, 3, 6]  # B, C, D, G
            valores_balance = []
            for idx in balance_idx:
                try:
                    valor = row_vals[idx] if idx < len(row_vals) else None
                    valores_balance.append(float(valor) if valor is not None else None)
                except (ValueError, TypeError):
                    valores_balance.append(None)

            # Ajustes (Debe / Haber)
            try:
                debe_val = float(row_vals[4]) if row_vals[4] not in [None, ""] else None
            except (ValueError, TypeError):
                debe_val = None

            try:
                haber_val = float(row_vals[5]) if row_vals[5] not in [None, ""] else None
            except (ValueError, TypeError):
                haber_val = None

            if all(v is None for v in valores_balance) and debe_val is None and haber_val is None:
                continue

            nombre_cuenta = primera_columna
            if not fechas_globales or all(f is None for f in fechas_globales):
                continue

            tipo_balance = "SEMESTRAL"
            tipo_cuenta = "NT"

            for valor, fecha in zip(valores_balance, fechas_globales):
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

            # Guardar ajustes/reclasificaciones
            if (debe_val is not None and debe_val != 0) or (haber_val is not None and haber_val != 0):
                AjustesReclasificaciones.objects.create(
                    audit=audit_instance,
                    nombre_cuenta=nombre_cuenta,
                    debe=debe_val or 0,
                    haber=haber_val or 0,
                )
        return True
    except Exception:
        traceback.print_exc()
        return False
