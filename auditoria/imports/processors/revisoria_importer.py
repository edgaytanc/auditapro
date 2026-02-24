# auditoria/imports/processors/revisoria_importer.py

from datetime import datetime
import traceback

from audits.models import Audit
from auditoria.models import BalanceCuentas, RevisoriaSubcuenta

__all__ = [
    "process_revisoria_sheet",
    "importar_subcuentas_estados_financieros",
    "process_estado_resultados_revisoria",
]



# ==========================================================
#  Helpers comunes
# ==========================================================

def _norm(value):
    """Normaliza texto: sin tildes, minúsculas y sin espacios."""
    import unicodedata

    if not value:
        return ""
    value = str(value)
    value = "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )
    return value.lower().replace(" ", "").replace("\xa0", "")


def _num(value):
    """Convierte a float o None."""
    try:
        return float(value) if value not in (None, "") else None
    except Exception:
        return None


def _find_sheet(workbook, *candidates):
    """
    Busca una hoja por nombre ignorando espacios y mayúsculas.

    Ej:
        _find_sheet(wb, "SUBCUENTAS ACTIVO", "SUBCUENTAS ACTIVO ")
    """
    normalized_candidates = [c.strip().upper() for c in candidates]


    for name in workbook.sheetnames:
        norm_name = name.strip().upper()
        if norm_name in normalized_candidates:
            return workbook[name]
    return None


def _es_encabezado_cedula(nombre_str, row):
    """
    Heurística para detectar una fila que es encabezado de cédula
    (ej: 'Casa', 'PRUEBA2', 'PRUEBA3', 'Capital Social', etc.)
    aunque NO exista en ESTADOS FINANCIEROS.

    Regla:
      - Columna A tiene texto
      - Las columnas numéricas típicas (B..G) vienen vacías
        → es muy probablemente un título de bloque, no una subcuenta.
    """
    if not nombre_str:
        return False

    # Revisamos las siguientes columnas (B..G => índices 1..6)
    celdas_numeros = row[1:7]
    for c in celdas_numeros:
        if c not in (None, "", 0, 0.0):
            # Si hay algún valor distinto de vacío/0, ya es fila de detalle
            return False
    return True


# ==========================================================
#  1) Importador de la hoja "ESTADOS FINANCIEROS"
# ==========================================================

def process_revisoria_sheet(sheet, audit_id):
    """
    Importador de la hoja 'ESTADOS FINANCIEROS' para Revisoría.

    ✅ Importa las filas de los bloques:
       - Código+Activo      → seccion='Activo'
       - Código+Pasivo      → seccion='Pasivo'
       - Código+Patrimonio  → seccion='Patrimonio' (si existe)

    ✅ Guarda:
       - Saldos ANUALES (C, D, E, H) como tipo_balance='ANUAL', tipo_cuenta='NT'
       - Ajustes (Debe/Haber) como tipo_balance='AJUSTE', tipo_cuenta='DEBE'/'HABER'

    🔹 Al final también dispara la importación del bloque
       'ESTADO DE RESULTADOS' en esta misma hoja.
    """

    try:
        audit_instance = Audit.objects.get(pk=audit_id)

        # ------------------------------------------------------------------
        # 1) Detectar las fechas de las columnas C, D, E, H usando el
        #    mismo helper que ESTADO DE RESULTADOS (_parse_fecha_revisoria)
        #    para que funcione con cualquier mes y tanto texto como datetime.
        # ------------------------------------------------------------------
        def _safe_parse_cell(addr):
            try:
                return _parse_fecha_revisoria(sheet[addr].value)
            except Exception:
                return None

        # índices de columna (0-based) → fecha
        fechas_columnas = {
            2: _safe_parse_cell("C6"),  # Columna C
            3: _safe_parse_cell("D6"),  # Columna D
            4: _safe_parse_cell("E6"),  # Columna E (la de 30/08/2024, por ejemplo)
            7: _safe_parse_cell("H6"),  # Columna H (año actual / ajustes)
        }

        # Fecha de AJUSTE (usaremos la fecha del año actual, columna H)
        fecha_ajuste = fechas_columnas.get(7, None)

        # ------------------------------------------------------------------
        # 2) Recorrer filas de la hoja: Activo, Pasivo y Patrimonio
        # ------------------------------------------------------------------
        current_section = None  # 'Activo', 'Pasivo' o 'Patrimonio'

        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
            colA = row[0] if len(row) > 0 else None
            colB = row[1] if len(row) > 1 else None

            txtA = _norm(colA)
            txtB = _norm(colB)

            # --- Detectar encabezados de sección --------------------------------
            if ("codigo+activo" in txtA) or ("codigo+activo" in txtB):
                current_section = "Activo"
                continue

            if ("codigo+pasivo" in txtA) or ("codigo+pasivo" in txtB):
                current_section = "Pasivo"
                continue

            if ("codigo+patrimonio" in txtA) or ("codigo+patrimonio" in txtB):
                current_section = "Patrimonio"
                continue

            # 👉 Cuando empieza "Código + ESTADO DE RESULTADO", dejamos de procesar balance
            if ("codigo+estado" in txtA) or ("codigo+estado" in txtB):
                current_section = None
                continue

            # Si no estamos dentro de una sección válida, saltamos
            if current_section not in ("Activo", "Pasivo", "Patrimonio"):
                continue

            # Filas de totales/títulos: las ignoramos (suelen tener 'total ...')
            if "total" in txtA or "total" in txtB:
                continue

            # Filas vacías → saltar
            if (colA is None or str(colA).strip() == "") and (
                colB is None or str(colB).strip() == ""
            ):
                continue

            # Intentar leer el código (columna A). Si no es número, ignoramos.
            try:
                codigo = int(str(colA).strip())
            except Exception:
                continue

            nombre_cuenta = str(colB).strip() if colB else None
            if not nombre_cuenta:
                continue

            # ------------------------------------------------------------------
            # 2.a) Saldos ANUALES (C, D, E, H)
            # ------------------------------------------------------------------
            for col_idx, fecha in fechas_columnas.items():
                if fecha is None:
                    continue

                try:
                    valor = row[col_idx]
                except IndexError:
                    valor = None

                if valor in (None, ""):
                    continue

                try:
                    valor = float(valor)
                except Exception:
                    continue

                # ✅ SOLO para E (idx=4) y H (idx=7): las fechas pueden ser iguales,
                # así que distinguimos por tipo_cuenta para que NO se pisen.
                tipo_cuenta = "NT"
                if col_idx == 4:      # Columna E (año anterior 31/12)
                    tipo_cuenta = "NT_ANT"
                elif col_idx == 7:    # Columna H (año actual 31/12)
                    tipo_cuenta = "NT_ACT"

                BalanceCuentas.objects.update_or_create(
                    audit=audit_instance,
                    tipo_balance="ANUAL",
                    fecha_corte=fecha,
                    seccion=current_section,
                    nombre_cuenta=nombre_cuenta,
                    tipo_cuenta=tipo_cuenta,  # 👈 clave para evitar “agrupación”
                    defaults={
                        "valor": valor,
                    },
                )


            # ------------------------------------------------------------------
            # 2.b) AJUSTES / RECLASIFICACIONES (Debe / Haber)
            # ------------------------------------------------------------------
            if fecha_ajuste:
                # Col F → Debe (índice 5), Col G → Haber (índice 6)
                valor_debe = row[5] if len(row) > 5 else None
                valor_haber = row[6] if len(row) > 6 else None

                # Debe
                if valor_debe not in (None, ""):
                    try:
                        v = float(valor_debe)
                        BalanceCuentas.objects.update_or_create(
                            audit=audit_instance,
                            tipo_balance="AJUSTE",
                            fecha_corte=fecha_ajuste,
                            seccion=current_section,
                            nombre_cuenta=nombre_cuenta,
                            tipo_cuenta="DEBE",
                            defaults={"valor": v},
                        )
                    except Exception:
                        pass

                # Haber
                if valor_haber not in (None, ""):
                    try:
                        v = float(valor_haber)
                        BalanceCuentas.objects.update_or_create(
                            audit=audit_instance,
                            tipo_balance="AJUSTE",
                            fecha_corte=fecha_ajuste,
                            seccion=current_section,
                            nombre_cuenta=nombre_cuenta,
                            tipo_cuenta="HABER",
                            defaults={"valor": v},
                        )
                    except Exception:
                        pass

        # ------------------------------------------------------------------
        # 3) IMPORTAR TAMBIÉN ESTADO DE RESULTADOS EN BalanceCuentas
        # ------------------------------------------------------------------
        try:
            process_estado_resultados_revisoria(sheet, audit_id)
        except Exception:
            traceback.print_exc()

        return True

    except Exception:
        traceback.print_exc()
        return False


# ==========================================================
#  2) Importador de SUBCUENTAS (ACTIVO / PASIVO / PATRIMONIO / RESULTADOS)
# ==========================================================

def importar_subcuentas_estados_financieros(audit, workbook):
    """
    Lee las hojas SUBCUENTAS ACTIVO / PASIVO / PATRIMONIO / RESULTADOS
    y guarda cada subcuenta en RevisoriaSubcuenta.
    No toca BalanceCuentas ni nada de lo que ya funciona.
    """

    # 1) Sacar las cuentas principales de la hoja ESTADOS FINANCIEROS
    main_sheet = workbook["ESTADOS FINANCIEROS"]
    cuentas_principales = set()

    for row in main_sheet.iter_rows(min_row=3, values_only=True):
        codigo = row[0]
        cuenta = row[1]
        if (isinstance(codigo, (int, float)) or str(codigo).isdigit()) and cuenta:
            cuentas_principales.add(str(cuenta).strip())

    # 2) Buscar y procesar cada subhoja, de forma robusta

    # SUBCUENTAS ACTIVO  (admite con/sin espacio final)
    sheet_activo = _find_sheet(workbook, "SUBCUENTAS ACTIVO", "SUBCUENTAS ACTIVO ")
    if sheet_activo is not None:
        _procesar_subhoja(
            audit,
            sheet_activo,
            "Activo",
            cuentas_principales,
        )

    # SUBCUENTAS PASIVO  (seccion_fija = None → dentro se decide PASIVO / PATRIMONIO según encabezados)
    sheet_pasivo = _find_sheet(workbook, "SUBCUENTAS PASIVO")
    if sheet_pasivo is not None:
        _procesar_subhoja(
            audit,
            sheet_pasivo,
            None,  # aquí dentro seccion cambia entre Pasivo/Patrimonio si la hoja los trae juntos
            cuentas_principales,
        )

    # SUBCUENTAS PATRIMONIO (si viene en hoja separada)
    sheet_patrimonio = _find_sheet(workbook, "SUBCUENTAS PATRIMONIO")
    if sheet_patrimonio is not None:
        _procesar_subhoja(
            audit,
            sheet_patrimonio,
            "Patrimonio",  # sección fija PATRIMONIO
            cuentas_principales,
        )

    # SUBCUENTAS RESULTADOS
    sheet_resultados = _find_sheet(workbook, "SUBCUENTAS RESULTADOS")
    if sheet_resultados is not None:
        _procesar_subhoja(
            audit,
            sheet_resultados,
            "EstadoResultado",
            cuentas_principales,
        )


def _procesar_subhoja(audit, sheet, seccion_fija, cuentas_principales):
    """
    Procesa una subhoja de ACTIVO / PASIVO / PATRIMONIO / RESULTADOS.

    Si seccion_fija es None (caso PASIVO), detectamos PASIVO / PATRIMONIO dentro de la hoja.

    👉 Ajuste importante:
       - Para subhojas con sección fija (Activo, Patrimonio, EstadoResultado), también consideramos
         como cuenta_principal cualquier fila que luzca como encabezado de cédula
         aunque NO esté en `cuentas_principales`.
    """

    current_seccion = seccion_fija  # 'Activo', 'EstadoResultado', 'Patrimonio' o None
    current_cuenta_principal = None

    # Saltamos las primeras filas de títulos (normalmente hasta la 6)
    for row in sheet.iter_rows(min_row=5, values_only=True):
        nombre = row[0]
        if not nombre:
            continue

        nombre_str = str(nombre).strip()

        # Encabezados generales de bloque
        if nombre_str.upper() in ("ACTIVO", "PASIVO", "PATRIMONIO", "ESTADO DE RESULTADOS"):
            # En PASIVO la seccion_fija viene en None, así que aquí se actualiza
            if seccion_fija is None:
                if nombre_str.upper() == "PASIVO":
                    current_seccion = "Pasivo"
                elif nombre_str.upper() == "PATRIMONIO":
                    current_seccion = "Patrimonio"
            # En RESULTADOS sólo usamos esto como marcador, la seccion_fija ya es 'EstadoResultado'
            current_cuenta_principal = None
            continue

        # Filas de TOTAL (no las tratamos como subcuenta)
        if nombre_str.upper().startswith("TOTAL "):
            current_cuenta_principal = None  # cerramos el bloque
            continue

        # 1️⃣ Caso normal: CUENTA PRINCIPAL que viene desde ESTADOS FINANCIEROS
        if nombre_str in cuentas_principales:
            # Esto es una cuenta principal (ej: 'Efectivo y Equivalentes', 'Casa', 'PRUEBA2', etc.)
            current_cuenta_principal = nombre_str
            continue

        # 2️⃣ Encabezado de cédula definido SOLO en subhojas con sección fija
        #    (ej: PRUEBA3 en ACTIVO, 'Capital Social' en PATRIMONIO, etc.)
        if seccion_fija is not None and _es_encabezado_cedula(nombre_str, row):
            current_cuenta_principal = nombre_str
            cuentas_principales.add(nombre_str)
            continue

        # Si no tenemos sección o cuenta principal, no sabemos dónde ubicarla aún
        if not current_seccion or not current_cuenta_principal:
            continue

        # A partir de aquí: es SUBCUENTA REAL
        saldo_ini_ant    = _num(row[1])  # Al 01/01/2023
        saldo_jul_ant    = _num(row[2])  # Al 31/07/2023
        saldo_dic_ant    = _num(row[3])  # Al 31/12/2023
        ajuste_debe      = _num(row[4])  # Debe
        ajuste_haber     = _num(row[5])  # Haber
        saldo_dic_actual = _num(row[6])  # Al 31/12/2024

        obj, created = RevisoriaSubcuenta.objects.update_or_create(
            audit=audit,
            seccion=current_seccion,
            cuenta_principal=current_cuenta_principal,
            nombre_subcuenta=nombre_str,
            defaults={
                "saldo_ini_anterior":   saldo_ini_ant,
                "saldo_julio_anterior": saldo_jul_ant,
                "saldo_dic_anterior":   saldo_dic_ant,
                "ajuste_debe":          ajuste_debe,
                "ajuste_haber":         ajuste_haber,
                "saldo_dic_actual":     saldo_dic_actual,
            },
        )



def _parse_fecha_revisoria(value):
    """
    Convierte cadenas tipo 'Al 31/12/2024' en date.
    Se usa la misma lógica para todas las secciones (Activo, Pasivo, Patrimonio, EstadoResultado).
    """
    if not value:
        return None

    s = str(value).strip()
    if s.lower().startswith("al "):
        s = s[3:].strip()

    # Intentamos con formatos comunes dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # Fallback: últimos 10 caracteres (por si viene con texto adicional)
    if len(s) >= 10:
        tail = s[-10:]
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(tail, fmt).date()
            except ValueError:
                continue

    raise ValueError(f"[Revisoria] No se pudo parsear fecha desde: {value!r}")


def process_estado_resultados_revisoria(sheet, audit_id):
    """
    Lee el bloque 'ESTADO DE RESULTADOS' de la hoja 'ESTADOS FINANCIEROS'
    y guarda las cuentas en BalanceCuentas con:

      seccion = 'EstadoResultado'
      tipo_balance = 'ANUAL' (4 fechas) + 'AJUSTE' (Debe/Haber para la última fecha)
    """

    # 1️⃣ Obtener las 4 fechas desde la fila 6 (C6, D6, E6, H6)
    fecha_d1 = _parse_fecha_revisoria(sheet["C6"].value)  # Al 01/12/2025
    fecha_d2 = _parse_fecha_revisoria(sheet["D6"].value)  # Al 31/07/2023
    fecha_d3 = _parse_fecha_revisoria(sheet["E6"].value)  # Al 31/12/2022
    fecha_d4 = _parse_fecha_revisoria(sheet["H6"].value)  # Al 31/12/2024

    fechas = [fecha_d1, fecha_d2, fecha_d3, fecha_d4]


    # 2️⃣ Buscar la fila donde está el encabezado 'ESTADO DE RESULTADOS'
    header_row = None
    for row in range(1, sheet.max_row + 1):
        val_a = sheet.cell(row=row, column=1).value  # Columna A
        val_b = sheet.cell(row=row, column=2).value  # Columna B

        texto_a = str(val_a).upper() if isinstance(val_a, str) else ""
        texto_b = str(val_b).upper() if isinstance(val_b, str) else ""

        if "ESTADO DE RESULTADOS" in texto_a or "ESTADO DE RESULTADOS" in texto_b:
            header_row = row
            break

    if not header_row:
        print("ℹ️ [ESTADO RESULTADOS] No se encontró encabezado 'ESTADO DE RESULTADOS' en la hoja.")
        return

    print(f"🔎 [ESTADO RESULTADOS] Encabezado encontrado en fila {header_row}")

    # 3️⃣ Recorrer las filas de detalle (debajo del encabezado) hasta 'Total ...' o fila vacía
    row = header_row + 1
    seccion = "EstadoResultado"

    while row <= sheet.max_row:
        nombre = sheet.cell(row=row, column=2).value  # Columna B → nombre cuenta

        # Si la fila está vacía, asumimos fin del bloque
        if not nombre:
            # Verificamos si toda la fila está vacía (más robusto)
            if not any(sheet.cell(row=row, column=c).value for c in range(1, 9)):
                break

        if isinstance(nombre, str) and "TOTAL" in nombre.upper():
            # Fila 'Total Estado de Resultados', la saltamos y terminamos
            break

        nombre_cuenta = str(nombre).strip()
        if not nombre_cuenta:
            row += 1
            continue

        # Valores numéricos:
        # C = fecha d1, D = d2, E = d3, H = d4, F = Debe (ajuste), G = Haber (ajuste)
        v_d1 = sheet.cell(row=row, column=3).value
        v_d2 = sheet.cell(row=row, column=4).value
        v_d3 = sheet.cell(row=row, column=5).value
        v_d4 = sheet.cell(row=row, column=8).value

        ajuste_debe = sheet.cell(row=row, column=6).value
        ajuste_haber = sheet.cell(row=row, column=7).value

        print(
            f"   ▶ [ESTADO RESULTADOS] fila {row} | cuenta='{nombre_cuenta}' | "
            f"d1={v_d1} d2={v_d2} d3={v_d3} d4={v_d4} | "
            f"ajuste_debe={ajuste_debe} ajuste_haber={ajuste_haber}"
        )

        # 4️⃣ Guardar 4 registros ANUAL (uno por fecha) si hay valor
        for fecha, valor, slot in zip(
            fechas,
            [v_d1, v_d2, v_d3, v_d4],
            ("d1", "d2", "d3", "d4"),
        ):
            if fecha and valor not in (None, "", 0):
                try:
                    v = float(valor)
                except Exception:
                    # Si la celda trae texto o algo raro, la saltamos
                    continue

                BalanceCuentas.objects.update_or_create(
                    audit_id=audit_id,
                    seccion=seccion,
                    nombre_cuenta=nombre_cuenta,
                    tipo_balance="ANUAL",
                    fecha_corte=fecha,
                    tipo_cuenta="NT",
                    defaults={"valor": v},
                )

        # 5️⃣ Guardar AJUSTES (Debe / Haber) en la última fecha (d4)
        if fecha_d4:
            if ajuste_debe not in (None, "", 0):
                try:
                    v = float(ajuste_debe)
                    BalanceCuentas.objects.update_or_create(
                        audit_id=audit_id,
                        seccion=seccion,
                        nombre_cuenta=nombre_cuenta,
                        tipo_balance="AJUSTE",
                        fecha_corte=fecha_d4,
                        tipo_cuenta="DEBE",
                        defaults={"valor": v},
                    )
                except Exception:
                    pass

            if ajuste_haber not in (None, "", 0):
                try:
                    v = float(ajuste_haber)
                    BalanceCuentas.objects.update_or_create(
                        audit_id=audit_id,
                        seccion=seccion,
                        nombre_cuenta=nombre_cuenta,
                        tipo_balance="AJUSTE",
                        fecha_corte=fecha_d4,
                        tipo_cuenta="HABER",
                        defaults={"valor": v},
                    )
                except Exception:
                    pass

        row += 1

    print("✔️ [ESTADO RESULTADOS] Cuentas importadas a BalanceCuentas ✔️")
