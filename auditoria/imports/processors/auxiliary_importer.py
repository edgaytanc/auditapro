import traceback
from auditoria.models import RegistroAuxiliar

__all__ = ["process_auxiliary_records"]

def process_auxiliary_records(sheet, audit_id):
    """Procesa la hoja de registros auxiliares y guarda cada cuenta/saldo."""
    try:
        records_created = 0
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(cell for cell in row):
                continue
            cuenta = str(row[1]).strip() if row[1] else None
            saldo = row[2] if isinstance(row[2], (int, float)) else None
            if cuenta and cuenta.upper().startswith("TOTAL"):
                continue
            if cuenta and saldo is not None:
                RegistroAuxiliar.objects.create(
                    audit_id=audit_id,
                    cuenta=cuenta,
                    saldo=saldo,
                )
                records_created += 1
        return records_created > 0
    except Exception:
        traceback.print_exc()
        return False
