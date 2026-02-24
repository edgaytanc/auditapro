from datetime import datetime
import traceback
from auditoria.models import SaldoInicial, BalanceCuentas

__all__ = ["process_initial_balances"]

def process_initial_balances(sheet, audit_id):
    """Procesa la hoja de saldos iniciales y crea registros en la BD.

    Se toma la fecha de corte del balance más reciente para la auditoría, o la
    fecha actual si no existe.
    """
    try:
        # Determinar fecha de corte por defecto
        fecha_corte = datetime.now().date()
        try:
            balances = BalanceCuentas.objects.filter(audit_id=audit_id).order_by("-fecha_corte")
            if balances.exists():
                fecha_corte = balances.first().fecha_corte
        except Exception:
            pass

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(cell for cell in row):
                continue
            cuenta = str(row[1]).strip() if row[1] else None
            saldo = row[2] if isinstance(row[2], (int, float)) else None
            if cuenta and cuenta.upper().startswith("TOTAL"):
                continue
            if cuenta and saldo is not None:
                SaldoInicial.objects.create(
                    audit_id=audit_id,
                    cuenta=cuenta,
                    saldo=saldo,
                    fecha_corte=fecha_corte,
                )
        return True
    except Exception:
        traceback.print_exc()
        return False
