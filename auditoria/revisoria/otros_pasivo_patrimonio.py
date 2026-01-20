# auditoria/Revisoria/otros_pasivo_patrimonio.py

from auditoria.models import RevisoriaSubcuenta
from .common import _extraer_fechas_desde_db


# ================== HELPER GENÉRICO 4.1.1 / 4.2.1 ==================

def _rellenar_cedulas_otras_4x1_desde_subcuentas(
    workbook,
    audit_id: int,
    seccion_filtro: str,
    etiqueta_seccion: str,
):
    """
    Rellena las cédulas 4.1.1 / 4.2.1 usando EXCLUSIVAMENTE
    las subcuentas que vienen de las hojas de SUBCUENTAS,
    filtrando por seccion EXACTA (PASIVO o PATRIMONIO).

    - NO usamos BalanceCuentas aquí.
    - NO excluimos cuentas especiales (como sí hicimos en ACTIVO).
    """


    # Fechas d1..d4 desde BD (misma lógica que CENTRALIZADORA / 3.6)
    fechas = _extraer_fechas_desde_db(audit_id)

    # Posiciones de fechas en encabezado (D13, E13, F13, I13)
    CELDAS_FECHAS_4X1 = {
        "d1": ("D", 13),   # 01/12/2025
        "d2": ("E", 13),   # 31/07/2023
        "d3": ("F", 13),   # 31/12/2022
        "d4": ("I", 13),   # 31/12/2024
    }

    # Área de detalle (subcuentas) filas 14..28 (29 = totales)
    AREA_DETALLE_INICIO = 14
    AREA_DETALLE_FIN = 28

    # 1️⃣ Traer TODAS las subcuentas de la sección EXACTA (PASIVO / PATRIMONIO)
    qs = (
        RevisoriaSubcuenta.objects
        .filter(
            audit_id=audit_id,
            seccion__iexact=seccion_filtro  # 👈 ahora es EXACTO, no contains
        )
        .order_by("cuenta_principal", "id")
    )


    if not qs.exists():
        print(
            f"ℹ️ [4.x.1] No hay subcuentas de {seccion_filtro.upper()} "
            f"(SUBCUENTAS); se omite."
        )
        return workbook

    # 2️⃣ Agrupar subcuentas por cuenta_principal
    cuentas = {}
    for sub in qs:
        cp = (sub.cuenta_principal or "").strip()
        nombre = (sub.nombre_subcuenta or "").strip()

        if not nombre:
            continue

        # Aquí NO excluimos encabezados ni XXXX, por petición tuya
        cuentas.setdefault(cp, []).append(sub)

    for cp, subs in cuentas.items():
        print(f"   - {cp}: {len(subs)} subcuentas")

    # 3️⃣ Recorrer cuentas principales y rellenar hojas '1', '2', '3', ...
    for idx, (cuenta, sub_list) in enumerate(cuentas.items(), start=1):
        sheet_name = str(idx)

        if sheet_name not in workbook.sheetnames:
            print(
                f"⚠️ [4.x.1] La hoja '{sheet_name}' no existe en la plantilla; "
                f"se omite ({etiqueta_seccion})."
            )
            continue

        sh = workbook[sheet_name]

        # ---------- FECHAS ENCABEZADO ----------
        for clave, (col_letra, fila) in CELDAS_FECHAS_4X1.items():
            fecha = fechas.get(clave)
            if not fecha:
                continue
            sh[f"{col_letra}{fila}"].value = fecha.strftime("%d/%m/%Y")

        # ---------- LIMPIAR ÁREA DETALLE ----------
        for row in range(AREA_DETALLE_INICIO, AREA_DETALLE_FIN + 1):
            for col in range(1, 10):  # A..I
                sh.cell(row=row, column=col).value = None

        # Título de la cédula (opcional)
        sh["A11"].value = f"CÉDULA SUMARIA - {cuenta}"

        # ---------- RELLENAR SUBCUENTAS ----------
        row = AREA_DETALLE_INICIO

        for i, sub in enumerate(sub_list, start=1):
            if row > AREA_DETALLE_FIN:
                break  # no desbordar la plantilla

            sh[f"A{row}"].value = i                    # Código correlativo
            sh[f"B{row}"].value = sub.nombre_subcuenta # Nombre subcuenta
            sh[f"C{row}"].value = ""                   # Ref P/T vacío

            # Montos (mismos campos que 3.6 ACTIVO)
            sh[f"D{row}"].value = sub.saldo_ini_anterior or 0
            sh[f"E{row}"].value = sub.saldo_julio_anterior or 0
            sh[f"F{row}"].value = sub.saldo_dic_anterior or 0
            sh[f"G{row}"].value = sub.ajuste_debe or 0
            sh[f"H{row}"].value = sub.ajuste_haber or 0
            sh[f"I{row}"].value = sub.saldo_dic_actual or 0

            row += 1

    return workbook


# ================== 4.1.1 – OTRAS CÉDULAS SUMARIAS DE PASIVO ==================

def update_cedula_411_otras(workbook, audit_id, sheet_financiero=None):
    """
    Rellena la plantilla '4.1.1 OTRAS CÉDULAS SUMARIAS DE PASIVO.xlsx'.

    🔹 Usa EXCLUSIVAMENTE las subcuentas de la sección PASIVO
       (RevisoriaSubcuenta con seccion = 'PASIVO').
    🔹 NO usa BalanceCuentas.
    🔹 No se excluyen subcuentas especiales.
    """

    try:
        workbook = _rellenar_cedulas_otras_4x1_desde_subcuentas(
            workbook=workbook,
            audit_id=audit_id,
            seccion_filtro="PASIVO",      #  SOLO PASIVO
            etiqueta_seccion="PASIVO",
        )
        print("✔️ Cédula 4.1.1 OTRAS CÉDULAS SUMARIAS DE PASIVO actualizada ✔️")
        return workbook

    except Exception as e:
        print(
            "⚠️ Error al actualizar cédula 4.1.1 OTRAS CÉDULAS SUMARIAS DE PASIVO:",
            e,
        )
        return workbook


# ================== 4.2.1 – OTRAS CÉDULAS SUMARIAS DE PATRIMONIO ==================

def update_cedula_421_otras(workbook, audit_id, sheet_financiero=None):
    """
    Rellena la plantilla '4.2.1 OTRAS CÉDULAS SUMARIAS DE PATRIMONIO.xlsx'.

    🔹 Usa EXCLUSIVAMENTE las subcuentas de la sección PATRIMONIO
       (RevisoriaSubcuenta con seccion = 'PATRIMONIO').
    🔹 NO usa BalanceCuentas.
    """

    try:
        workbook = _rellenar_cedulas_otras_4x1_desde_subcuentas(
            workbook=workbook,
            audit_id=audit_id,
            seccion_filtro="PATRIMONIO",  # 👈 SOLO PATRIMONIO
            etiqueta_seccion="PATRIMONIO",
        )
        print("✔️ Cédula 4.2.1 OTRAS CÉDULAS SUMARIAS DE PATRIMONIO actualizada ✔️")
        return workbook

    except Exception as e:
        print(
            "⚠️ Error al actualizar cédula 4.2.1 OTRAS CÉDULAS SUMARIAS DE PATRIMONIO:",
            e,
        )
        return workbook

