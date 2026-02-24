# auditoria/Revisoria/pasivo_patrimonio.py

from django.db.models import Q

from auditoria.models import BalanceCuentas
from .common import (
    _clean,
    _normalizar,
    _extraer_fechas_desde_db,
    _formatear_fecha,
    _set_cell_value,
)

# ============================================================
# 🔹 UTILIDADES GENÉRICAS PARA OBTENER DATOS POR SECCIONES
# ============================================================


def _obtener_cuentas_por_secciones(audit_id, secciones, label_debug="PASIVO+PATRIMONIO"):
    """
    Versión genérica: arma una estructura por cuenta con d1..d4 usando BalanceCuentas
    para las secciones indicadas en `secciones`.
    """

    # 1) Fechas oficiales d1..d4 (las mismas de ACTIVO)
    fechas = _extraer_fechas_desde_db(audit_id)


    d1 = fechas.get("d1")
    d2 = fechas.get("d2")
    d3 = fechas.get("d3")
    d4 = fechas.get("d4")

    qs = (
        BalanceCuentas.objects.filter(
            audit_id=audit_id,
            tipo_balance="ANUAL",
            seccion__in=secciones,
        ).order_by("nombre_cuenta", "fecha_corte")
    )

    cuentas = {}

    for bc in qs:
        nombre = (bc.nombre_cuenta or "").strip()
        if not nombre:
            continue

        f = bc.fecha_corte
        slot = None

        # 🔗 Mapeo 1:1 contra las fechas clasificadas
        tc = (bc.tipo_cuenta or "").strip().upper()

        if d1 and f == d1:
            slot = "d1"
        elif d2 and f == d2:
            slot = "d2"
        # ✅ Si d3 y d4 son la MISMA fecha, distinguir por tipo_cuenta
        elif d3 and d4 and d3 == d4 and f == d3:
            slot = "d4" if tc == "NT_ACT" else "d3"
        elif d3 and f == d3:
            slot = "d3"
        elif d4 and f == d4:
            slot = "d4"



        if not slot:
            # Fecha que no coincide con ninguno de los cortes oficiales
            continue

        if nombre not in cuentas:
            cuentas[nombre] = {
                "nombre": nombre,
                "d1": None,
                "d2": None,
                "d3": None,
                "d4": None,
            }

        cuentas[nombre][slot] = float(bc.valor)


    # Resumen por columna
    totales_por_slot = {"d1": 0, "d2": 0, "d3": 0, "d4": 0}
    for c in cuentas.values():
        for slot in totales_por_slot.keys():
            if c[slot] is not None:
                totales_por_slot[slot] += 1

    return list(cuentas.values())


def _obtener_ajustes_por_secciones(audit_id, secciones, label_debug="PASIVO+PATRIMONIO"):
    """
    Versión genérica para AJUSTES (Debe/Haber) por secciones indicadas.

    Devuelve:
    {
        'Cuenta X': {'debe': 150000.0, 'haber': 120000.0},
        ...
    }
    """
    qs = BalanceCuentas.objects.filter(
        audit_id=audit_id,
        tipo_balance="AJUSTE",
        seccion__in=secciones,
    )

    ajustes = {}
    for bc in qs:
        nombre = (bc.nombre_cuenta or "").strip()
        if not nombre:
            continue

        if nombre not in ajustes:
            ajustes[nombre] = {"debe": None, "haber": None}

        tipo = (bc.tipo_cuenta or "").upper()
        if tipo == "DEBE":
            ajustes[nombre]["debe"] = float(bc.valor)
        elif tipo == "HABER":
            ajustes[nombre]["haber"] = float(bc.valor)

    return ajustes


# ============================================================
# 🔹 VERSIONES ESPECÍFICAS YA EXISTENTES (NO CAMBIA COMPORTO)
# ============================================================


def _obtener_cuentas_pasivo_patrimonio(audit_id):
    """
    Arma estructura por cuenta con d1..d4 para secciones:
    PASIVO / PATRIMONIO / PASIVO Y PATRIMONIO.
    (Comportamiento equivalente al original, solo refactorizado)
    """
    return _obtener_cuentas_por_secciones(
        audit_id,
        secciones=["Pasivo", "Patrimonio", "Pasivo y Patrimonio"],
        label_debug="PASIVO+PATRIMONIO",
    )


def _obtener_ajustes_pasivo_patrimonio(audit_id):
    """
    Devuelve Debe/Haber para secciones:
    PASIVO / PATRIMONIO / PASIVO Y PATRIMONIO.
    """
    return _obtener_ajustes_por_secciones(
        audit_id,
        secciones=["Pasivo", "Patrimonio", "Pasivo y Patrimonio"],
        label_debug="PASIVO+PATRIMONIO",
    )


# ============================================================
# 🔹 NUEVO: SOLO PASIVO (PENSADO PARA 4 CENTRALIZADORA DEL PASIVO)
# ============================================================


def _obtener_cuentas_pasivo_solo(audit_id):
    return _obtener_cuentas_por_secciones(
        audit_id,
        secciones=["Pasivo"],
        label_debug="PASIVO",
    )


def _obtener_ajustes_pasivo_solo(audit_id):
    return _obtener_ajustes_por_secciones(
        audit_id,
        secciones=["Pasivo"],
        label_debug="PASIVO",
    )


# ============================================================
# 🔹 BUSCAR FILAS EN CENTRALIZADORA
# ============================================================


def _encontrar_fila_codigo_pasivo_patrimonio(sheet):
    """
    Busca la fila donde aparece el encabezado:
      - 'Código+Pasivo+Patrimonio' (BALANCE), o
      - 'Código+Pasivo' (4 CENTRALIZADORA DEL PASIVO)
    en las columnas B o C.
    """
    patrones = [
        "codigo+pasivo+patrimonio",
        "codigo+pasivoypatrimonio",
        "codigopasivoypatrimonio",
        "codigo+pasivo",  # para hoja SOLO PASIVO
        "codigopasivo",
    ]

    for row in range(1, sheet.max_row + 1):
        for col in (2, 3):
            value = _normalizar(sheet.cell(row=row, column=col).value)
            if any(p in value for p in patrones):
                return row
    return None


def _encontrar_fila_suma_pasivo_patrimonio(sheet, fila_inicio):
    """
    Busca la fila donde está:
      - 'Suma Pasivo y Patrimonio' (BALANCE), o
      - 'Suma Pasivo' (4 CENTRALIZADORA DEL PASIVO)
    en las columnas B o C, a partir de fila_inicio.
    """
    if not fila_inicio:
        return None

    patrones = [
        "sumapasivoypatrimonio",
        "sumapasivo+patrimonio",
        "sumapasivo",  # para plantilla solo Pasivo
    ]

    for row in range(fila_inicio + 1, sheet.max_row + 1):
        for col in (2, 3):
            value = _clean(sheet.cell(row=row, column=col).value)
            if any(p in value for p in patrones):
                return row
    return None


# ============================================================
# 🔹 ESCRIBIR BLOQUE EN CENTRALIZADORA
# ============================================================


def _actualizar_bloque_pasivo_patrimonio(sheet, audit_id, cuentas=None, ajustes=None):
    """
    Actualiza el bloque CÓDIGO+PASIVO+PATRIMONIO (o CÓDIGO+PASIVO en la otra plantilla)
    en la hoja CENTRALIZADORA, usando las secciones configuradas en `cuentas`.

    Si `cuentas` y `ajustes` son None, se usan las de PASIVO+PATRIMONIO (balance general).
    """

    fila_header = _encontrar_fila_codigo_pasivo_patrimonio(sheet)
    fila_suma = _encontrar_fila_suma_pasivo_patrimonio(sheet, fila_header)

    if cuentas is None:
        cuentas = _obtener_cuentas_pasivo_patrimonio(audit_id)
    if ajustes is None:
        ajustes = _obtener_ajustes_pasivo_patrimonio(audit_id)

    if not fila_header or not fila_suma or not cuentas:
        print("ℹ No se pudo localizar bloque PASIVO+PATRIMONIO (o no hay cuentas).")
        return

    fila_inicio = fila_header + 1
    filas_actuales = fila_suma - fila_inicio
    filas_necesarias = len(cuentas)

    # Ajustar filas dinámicamente (igual que en ACTIVO)
    if filas_necesarias > filas_actuales:
        sheet.insert_rows(fila_suma, filas_necesarias - filas_actuales)
    elif filas_necesarias < filas_actuales:
        for r in range(fila_inicio + filas_necesarias, fila_suma):
            for c in range(1, 20):
                sheet.cell(row=r, column=c).value = None

    # Columnas (misma estructura que ACTIVO en CENTRALIZADORA)
    COL_COD = 2  # Código+Pasivo(+Patrimonio)
    COL_NOM = 3  # Cuenta
    COL_D1 = 5  # Al 01/12/AAAA
    COL_D2 = 6  # Al 31/07/AAAA
    COL_D3 = 7  # Al 31/12 año anterior
    COL_DEBE = 8  # Debe (ajustes)
    COL_HABER = 9  # Haber (ajustes)
    COL_D4 = 10  # Al 31/12 año actual

    for i, cta in enumerate(cuentas):
        r = fila_inicio + i
        nombre = cta["nombre"]

        v_d1 = cta.get("d1")
        v_d2 = cta.get("d2")
        v_d3 = cta.get("d3")
        v_d4 = cta.get("d4")

        datos_ajuste = ajustes.get(nombre, {}) if ajustes else {}
        v_debe = datos_ajuste.get("debe")
        v_haber = datos_ajuste.get("haber")


        sheet.cell(row=r, column=COL_COD).value = i + 1
        sheet.cell(row=r, column=COL_NOM).value = nombre
        sheet.cell(row=r, column=COL_D1).value = v_d1
        sheet.cell(row=r, column=COL_D2).value = v_d2
        sheet.cell(row=r, column=COL_D3).value = v_d3
        sheet.cell(row=r, column=COL_D4).value = v_d4

        if datos_ajuste:
            sheet.cell(row=r, column=COL_DEBE).value = v_debe
            sheet.cell(row=r, column=COL_HABER).value = v_haber

    print("✔️ PASIVO+PATRIMONIO → Base actualizada (CENTRALIZADORA)")


# ============================================================
# 🔹 BLOQUE EN "ESTADOS FINANCIEROS"
# ============================================================


def _actualizar_hoja_estados_financieros_pasivo_patrimonio(workbook, cuentas, ajustes):
    """
    Actualiza el bloque CÓDIGO+PASIVO+PATRIMONIO en la hoja 'ESTADOS FINANCIEROS …'.
    No toca las fechas del encabezado (ya las pone ACTIVO).
    """
    target_name = None
    for name in workbook.sheetnames:
        if "ESTADOS FINANCIEROS" in str(name).upper():
            target_name = name
            break

    if not target_name:
        print("ℹ Hoja 'ESTADOS FINANCIEROS …' no encontrada para PASIVO+PATRIMONIO.")
        return

    sheet = workbook[target_name]

    # ⚙ Ajusta esta fila según donde comienza Código+Pasivo+Patrimonio en tu plantilla
    FILA_INICIO_PP = 26  # <--- si en tu Excel empieza en otra fila, cambia este valor

    COL_COD = 1  # A → Código+Pasivo+Patrimonio
    COL_NOM = 2  # B → Cuenta
    COL_D1 = 3  # C → Fecha corte 1
    COL_D2 = 4  # D → Fecha corte 2
    COL_D3 = 5  # E → Fecha corte 3
    COL_DEBE = 6  # F → Debe
    COL_HABER = 7  # G → Haber
    COL_D4 = 8  # H → Fecha corte 4 (año actual)

    for i, cta in enumerate(cuentas):
        r = FILA_INICIO_PP + i
        nombre = cta["nombre"]

        sheet.cell(row=r, column=COL_COD).value = i + 1
        sheet.cell(row=r, column=COL_NOM).value = nombre
        sheet.cell(row=r, column=COL_D1).value = cta["d1"]
        sheet.cell(row=r, column=COL_D2).value = cta["d2"]
        sheet.cell(row=r, column=COL_D3).value = cta["d3"]
        sheet.cell(row=r, column=COL_D4).value = cta["d4"]

        datos_ajuste = ajustes.get(nombre, {})
        if datos_ajuste:
            sheet.cell(row=r, column=COL_DEBE).value = datos_ajuste.get("debe")
            sheet.cell(row=r, column=COL_HABER).value = datos_ajuste.get("haber")

    print("✔️ PASIVO+PATRIMONIO → Base actualizada (ESTADOS FINANCIEROS)")


# ============================================================
# 🔹 WRAPPER PARA 4 CENTRALIZADORA DEL PASIVO (SOLO PASIVO)
# ============================================================



def _obtener_cuentas_pasivo(audit_id):
    """
    Arma una estructura por cuenta con d1, d2, d3, d4 usando BalanceCuentas,
    pero tomando SOLO la sección PASIVO.

    Usa exactamente las mismas fechas d1..d4 que `_extraer_fechas_desde_db`,
    para que las columnas del Excel queden alineadas con ACTIVO.
    """
    fechas = _extraer_fechas_desde_db(audit_id)

    d1 = fechas.get("d1")
    d2 = fechas.get("d2")
    d3 = fechas.get("d3")
    d4 = fechas.get("d4")

    qs = (
        BalanceCuentas.objects
        .filter(
            audit_id=audit_id,
            tipo_balance="ANUAL",
            seccion__iexact="Pasivo",
        )
        .order_by("nombre_cuenta", "fecha_corte")
    )

    cuentas = {}

    for bc in qs:
        nombre = (bc.nombre_cuenta or "").strip()
        if not nombre:
            continue

        # 🚫 Parche: excluir cualquier cuenta que incluya la palabra 'Patrimonio'
        if "patrimonio" in _normalizar(nombre):
            print(f"   ⏭  Saltando cuenta de PATRIMONIO en SOLO PASIVO: '{nombre}'")
            continue

        f = bc.fecha_corte
        slot = None

        tc = (bc.tipo_cuenta or "").strip().upper()

        if d1 and f == d1:
            slot = "d1"
        elif d2 and f == d2:
            slot = "d2"
        # ✅ Si d3 y d4 son la MISMA fecha, distinguir por tipo_cuenta
        elif d3 and d4 and d3 == d4 and f == d3:
            slot = "d4" if tc == "NT_ACT" else "d3"
        elif d3 and f == d3:
            slot = "d3"
        elif d4 and f == d4:
            slot = "d4"



        if not slot:
            continue

        if nombre not in cuentas:
            cuentas[nombre] = {
                "nombre": nombre,
                "d1": None,
                "d2": None,
                "d3": None,
                "d4": None,
            }

        cuentas[nombre][slot] = float(bc.valor)


    totales_por_slot = {"d1": 0, "d2": 0, "d3": 0, "d4": 0}
    for c in cuentas.values():
        for slot in totales_por_slot.keys():
            if c[slot] is not None:
                totales_por_slot[slot] += 1

    return list(cuentas.values())


def _obtener_ajustes_pasivo(audit_id):
    """
    Devuelve un dict con Debe/Haber por cuenta para los AJUSTES de PASIVO:

    {
        'Cuenta X': {'debe': 150000.0, 'haber': 120000.0},
        ...
    }
    """
    qs = (
        BalanceCuentas.objects
        .filter(
            audit_id=audit_id,
            tipo_balance="AJUSTE",
            seccion__iexact="Pasivo",
        )
    )

    ajustes = {}
    for bc in qs:
        nombre = (bc.nombre_cuenta or "").strip()
        if not nombre:
            continue
        
        # 🚫 Parche: excluir ajustes de Patrimonio en la CENTRALIZADORA DEL PASIVO
        if "patrimonio" in _normalizar(nombre):
            print(f"   ⏭  Saltando AJUSTE de PATRIMONIO en SOLO PASIVO: '{nombre}'")
            continue

        if nombre not in ajustes:
            ajustes[nombre] = {"debe": None, "haber": None}

        tipo = (bc.tipo_cuenta or "").upper()
        if tipo == "DEBE":
            ajustes[nombre]["debe"] = float(bc.valor)
        elif tipo == "HABER":
            ajustes[nombre]["haber"] = float(bc.valor)

    return ajustes

# ================== BUSCAR FILAS EN CENTRALIZADORA PASIVO ==================

def _encontrar_fila_codigo_pasivo(sheet):
    """
    Busca la fila donde aparece el encabezado 'Código+Pasivo'
    (o variaciones) en las columnas B o C.
    """
    for row in range(1, sheet.max_row + 1):
        for col in (2, 3):
            value = _normalizar(sheet.cell(row=row, column=col).value)
            if any(p in value for p in [
                "codigo+pasivo",
                "codigopasivo",
            ]):
                return row
    return None


def _encontrar_fila_suma_pasivo(sheet, fila_inicio):
    """
    Busca la fila donde está 'Suma Pasivo' en las columnas B o C,
    a partir de fila_inicio.
    """
    if not fila_inicio:
        return None

    for row in range(fila_inicio + 1, sheet.max_row + 1):
        for col in (2, 3):
            value = _clean(sheet.cell(row=row, column=col).value)
            if any(p in value for p in [
                "sumapasivo",
                "sumapasivos",
            ]):
                return row
    return None

# ================== ESCRIBIR BLOQUE EN '4 CENTRALIZADORA DEL PASIVO' ==================

def _actualizar_bloque_pasivo_centralizadora(sheet, audit_id, cuentas=None, ajustes=None):
    """
    Actualiza el bloque CÓDIGO+PASIVO en la hoja '4 CENTRALIZADORA DEL PASIVO.xlsx'.

    Estructura igual a la CENTRALIZADORA general:
    - Col B: Código
    - Col C: Cuenta
    - Col E, F, G, J: d1..d4
    - Col H, I: Debe / Haber (ajustes)
    """

    fila_header = _encontrar_fila_codigo_pasivo(sheet)
    fila_suma = _encontrar_fila_suma_pasivo(sheet, fila_header)

    if cuentas is None:
        cuentas = _obtener_cuentas_pasivo(audit_id)
    if ajustes is None:
        ajustes = _obtener_ajustes_pasivo(audit_id)

    if not fila_header or not fila_suma or not cuentas:
        print("ℹ No se pudo localizar bloque PASIVO (o no hay cuentas).")
        return

    fila_inicio = fila_header + 1
    filas_actuales = fila_suma - fila_inicio
    filas_necesarias = len(cuentas)

    # Ajustar filas dinámicamente
    if filas_necesarias > filas_actuales:
        sheet.insert_rows(fila_suma, filas_necesarias - filas_actuales)
    elif filas_necesarias < filas_actuales:
        for r in range(fila_inicio + filas_necesarias, fila_suma):
            for c in range(1, 20):
                sheet.cell(row=r, column=c).value = None

    # Columnas (igual que en CENTRALIZADORA)
    COL_COD = 2     # Código+Pasivo
    COL_NOM = 3     # Cuenta
    COL_D1 = 5      # Al corte d1
    COL_D2 = 6      # Al corte d2
    COL_D3 = 7      # Al corte d3
    COL_DEBE = 8    # Debe (ajustes)
    COL_HABER = 9   # Haber (ajustes)
    COL_D4 = 10     # Al corte d4

    for i, cta in enumerate(cuentas):
        r = fila_inicio + i
        nombre = cta["nombre"]

        v_d1 = cta.get("d1")
        v_d2 = cta.get("d2")
        v_d3 = cta.get("d3")
        v_d4 = cta.get("d4")

        datos_ajuste = ajustes.get(nombre, {}) if ajustes else {}
        v_debe = datos_ajuste.get("debe")
        v_haber = datos_ajuste.get("haber")


        sheet.cell(row=r, column=COL_COD).value = i + 1
        sheet.cell(row=r, column=COL_NOM).value = nombre
        sheet.cell(row=r, column=COL_D1).value = v_d1
        sheet.cell(row=r, column=COL_D2).value = v_d2
        sheet.cell(row=r, column=COL_D3).value = v_d3
        sheet.cell(row=r, column=COL_D4).value = v_d4

        if datos_ajuste:
            sheet.cell(row=r, column=COL_DEBE).value = v_debe
            sheet.cell(row=r, column=COL_HABER).value = v_haber

    print("✔️ PASIVO → Base actualizada (CENTRALIZADORA DEL PASIVO)")
