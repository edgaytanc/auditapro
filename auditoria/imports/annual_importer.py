from datetime import datetime
import traceback
from audits.models import Audit
from auditoria.models import BalanceCuentas, AjustesReclasificaciones

__all__ = ["process_annual_sheet"]

def process_annual_sheet(sheet, audit_id):
    """Procesa la hoja *ESTADOS FINANCIEROS ANUAL* con la nueva estructura.

    Columnas esperadas por fila de cuenta:
        A -> Nombre de la cuenta
        B -> Valor año anterior
        C -> Debe (ajustes / reclasificaciones)
        D -> Haber (ajustes / reclasificaciones)
        E -> Valor año actual
        F -> Tipo. Cuenta (C / NC)

    Crea registros en:
        - BalanceCuentas (valores de años)
        - AjustesReclasificaciones (debe / haber)
    """
    try:
        current_section = None
        audit_instance = Audit.objects.get(pk=audit_id)

        SECCIONES_VALIDAS = ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]
        ENCABEZADOS_A_OMITIR = [
            "CUENTA",
            "Fecha corte año anterior",
            "Fecha corte año actual",
        ]
        PALABRAS_TOTAL = [
            "TOTAL ACTIVO",
            "TOTAL PASIVO",
            "TOTAL PATRIMONIO",
            "TOTAL PASIVO Y PATRIMONIO",
        ]

        # Variables para almacenar las fechas globales
        fechas_globales_anterior = None
        fechas_globales_actual = None

        for row in sheet.iter_rows(min_row=2, max_col=6, values_only=True):
            primera_columna = str(row[0]).strip() if row[0] is not None else ""

            if all(cell is None for cell in row):
                continue
            if primera_columna in ENCABEZADOS_A_OMITIR:
                continue
            if any(total in primera_columna for total in PALABRAS_TOTAL):
                continue

            if (
                primera_columna in SECCIONES_VALIDAS
                and (row[1] is None or isinstance(row[1], str))
            ):
                current_section = primera_columna
                if current_section == "Activo":
                    # Extraer fechas de la fila de encabezado
                    if isinstance(row[1], str) and row[1].strip().lower().startswith("al "):
                        raw_date_anterior = row[1].replace("Al ", "").strip()
                        try:
                            fechas_globales_anterior = datetime.strptime(
                                raw_date_anterior, "%d/%m/%Y"
                            ).date()
                        except Exception:
                            pass
                    # La fecha del año actual ahora está en la columna E (índice 4)
                    if isinstance(row[4], str) and row[4].strip().lower().startswith("al "):
                        raw_date_actual = row[4].replace("Al ", "").strip()
                        try:
                            fechas_globales_actual = datetime.strptime(
                                raw_date_actual, "%d/%m/%Y"
                            ).date()
                        except Exception:
                            pass
                continue

            if current_section is None:
                continue

            if len(row) < 6:
                continue

            try:
                valor_anterior = float(row[1]) if row[1] not in (None, "") else None
                valor_actual = float(row[4]) if row[4] not in (None, "") else None

                debe = float(row[2]) if row[2] not in (None, "") else 0
                haber = float(row[3]) if row[3] not in (None, "") else 0

                # Si todos los valores son cero o None, omitir fila
                if (
                    valor_anterior is None
                    and valor_actual is None
                    and debe == 0
                    and haber == 0
                ):
                    continue
            except (ValueError, TypeError):
                continue

            nombre_cuenta = primera_columna
            tipo_cuenta_raw = str(row[5]).strip().upper() if len(row) >= 6 and row[5] is not None else ""
            if tipo_cuenta_raw == "C":
                tipo_cuenta = "Corriente"
            elif tipo_cuenta_raw == "NC":
                tipo_cuenta = "No Corriente"
            else:
                tipo_cuenta = None

            if not (fechas_globales_anterior and fechas_globales_actual):
                continue

            tipo_balance = "ANUAL"
            if valor_anterior is not None:
                BalanceCuentas.objects.create(
                    audit=audit_instance,
                    tipo_balance=tipo_balance,
                    fecha_corte=fechas_globales_anterior,
                    seccion=current_section,
                    nombre_cuenta=nombre_cuenta,
                    tipo_cuenta=tipo_cuenta,
                    valor=valor_anterior,
                )
            if valor_actual is not None:
                BalanceCuentas.objects.create(
                    audit=audit_instance,
                    tipo_balance=tipo_balance,
                    fecha_corte=fechas_globales_actual,
                    seccion=current_section,
                    nombre_cuenta=nombre_cuenta,
                    tipo_cuenta=tipo_cuenta,
                    valor=valor_actual,
                )

            # Registrar ajustes / reclasificaciones si existen
            if debe != 0 or haber != 0:
                AjustesReclasificaciones.objects.create(
                    audit=audit_instance,
                    nombre_cuenta=nombre_cuenta,
                    debe=debe,
                    haber=haber,
                )
        return True
    except Exception:
        traceback.print_exc()
        return False
