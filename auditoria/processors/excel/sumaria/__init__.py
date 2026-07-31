# Paquete de procesador SUMARIA
"""Funciones para procesar cédulas Sumarias.

• fechas.py          → utilidades de fechas.
• deteccion.py       → detección de la cuenta asociada y validaciones.
• layout.py          → localiza la cuadrícula real de la plantilla.
• escritura.py       → escribe cuentas y saldos según ese layout.
• data_extraction.py → extracción y obtención de datos.
• insercion.py       → escritura en celdas fijas (plantillas anteriores).
• formulas.py        → helpers para manipular fórmulas.

`process_sumaria_file` es la API externa que agrupa todo.
"""

from __future__ import annotations

import logging

from openpyxl.workbook import Workbook

from .fechas import obtener_fechas_semestrales
from .deteccion import (
    determinar_cuenta_por_nombre_archivo,
    verificar_cuenta_en_balances,
    cuenta_importada_equivalente,
    buscar_tabla_sumaria,
    numero_de_cedula_generica,
    cuentas_sin_cedula_propia,
)
from .data_extraction import obtener_todas_cuentas_seccion
from .insercion import (
    insertar_datos_cuenta,
    insertar_multiples_cuentas,
    actualizar_fechas_encabezados,
)
from .layout import detectar_layout
from .escritura import escribir_sumaria

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Selección de las cuentas que corresponden a la cédula
# ---------------------------------------------------------------------

def _seccion_de_archivo(file_name):
    """Sección completa que toca volcar cuando la cédula es de un bloque entero."""
    nombre = file_name.upper()
    if 'PATRIMONIO' in nombre:
        return 'Patrimonio'
    if 'ESTADO RESULTADOS' in nombre or 'ESTADO_DE_RESULTADOS' in nombre:
        return 'ESTADO DE RESULTADOS'
    return None


def _cuenta_generica(balances, fechas, file_name):
    """
    Cuenta que corresponde a una cédula genérica ('N CEDULA_SUMARIA.xlsx').

    Las cédulas de 'OTRAS CEDULAS SUMARIAS' están para las cuentas que el
    cliente agrega a su Excel Financiero y que no tienen cédula propia
    (p. ej. 'Contratos'). Se reparten en orden: la cédula 1 recibe la primera
    cuenta sin cédula propia, la 2 la segunda, y así sucesivamente.
    """
    numero = numero_de_cedula_generica(file_name)
    if not numero:
        return None

    pendientes = cuentas_sin_cedula_propia(balances, fechas)
    if numero > len(pendientes):
        return None
    return pendientes[numero - 1]


def _cuentas_a_escribir(balances, fechas, file_name):
    """
    Devuelve {cuenta: {fecha: importe}} con lo que corresponde a esta cédula.

    · Cédulas de bloque (Patrimonio / Estado de Resultados): todas las cuentas
      de la sección.
    · Cédulas de un área concreta: la cuenta que nombra el archivo.
    · Cédulas genéricas ('N CEDULA_SUMARIA.xlsx'): la enésima cuenta importada
      que no tiene cédula propia (las cuentas nuevas del Excel del cliente).
    """
    seccion = _seccion_de_archivo(file_name)
    if seccion:
        return obtener_todas_cuentas_seccion(balances, fechas, seccion) or {}

    cuenta = determinar_cuenta_por_nombre_archivo(file_name)
    if not cuenta:
        cuenta = _cuenta_generica(balances, fechas, file_name)
        if not cuenta:
            return {}

    existe, datos = verificar_cuenta_en_balances(balances, cuenta, fechas)
    return {cuenta: datos} if existe else {}


def _referencias_de(cuentas):
    """Referencia de sumaria (A-1, H-1, J-1…) para la columna Ref P/T."""
    try:
        from auditoria.services.referencias import ref_para_cuenta
    except Exception:
        return {}
    return {nombre: ref_para_cuenta(nombre) for nombre in cuentas}


# ---------------------------------------------------------------------
# API Principal del procesador SUMARIA
# ---------------------------------------------------------------------

def _subcuentas_de_cuenta(audit_id, balances, cuenta_archivo, fechas_semestrales):
    """
    Subcuentas importadas (RevisoriaSubcuenta) de la cuenta que nombra la
    cédula, o [] si no hay. Es el mismo detalle que llenan las cédulas de
    Revisoría: la sumaria muestra las subcuentas REALES del Excel del cliente.
    """
    if not audit_id or not cuenta_archivo:
        return []
    try:
        from auditoria.models import RevisoriaSubcuenta
    except Exception:
        return []

    cuenta_real = cuenta_importada_equivalente(
        balances, cuenta_archivo, fechas_semestrales) or cuenta_archivo

    return list(
        RevisoriaSubcuenta.objects
        .filter(audit_id=audit_id, cuenta_principal__iexact=cuenta_real)
        .order_by('nombre_subcuenta')
    )


def process_sumaria_file(
    workbook: Workbook,
    balances: dict[str, float],
    ajustes_reclasificaciones: dict[str, float],
    file_name: str,
    audit_id=None,
):
    """
    Procesa archivos SUMARIA insertando los saldos del Excel Financiero.

    Recorre las hojas buscando una cuadrícula de cédula sumaria clásica
    (cuenta + cortes con fecha + ajustes Debe/Haber). Las sumarias
    especializadas de cada área —Activos Fijos, Inversiones, Inventarios,
    Construcciones, Intangible, Cuentas por Pagar, Préstamos, Patrimonio y
    Estado de Resultados— tienen columnas propias que no corresponden a los
    cortes del balance, así que se dejan intactas: reciben igualmente el
    encabezado, los datos del auditor y su referencia.

    Con `audit_id` además:
      · las columnas de corte se rotulan con las fechas REALES del Excel
        importado (guardadas en ParametrosAuditoria), y
      · si la cuenta del área trae subcuentas (hojas 'SUBCUENTAS ...'),
        la cédula lista ese detalle igual que las cédulas de Revisoría.
    """
    fechas_semestrales = obtener_fechas_semestrales(balances)
    if not fechas_semestrales:
        return workbook

    fechas_ordenadas = sorted(fechas_semestrales)
    cuentas = _cuentas_a_escribir(balances, fechas_semestrales, file_name)
    if not cuentas:
        return workbook

    referencias = _referencias_de(cuentas)

    # Cortes reales del último Excel Financiero importado (si se guardaron)
    try:
        from auditoria.services.cortes_excel import cortes_de_auditoria
        cortes = cortes_de_auditoria(audit_id)
    except Exception:
        cortes = None

    # Guarda: si los cortes guardados no corresponden a los balances actuales
    # (p. ej. luego se reimportó un archivo del formato clásico), se ignoran.
    if cortes:
        fechas_guardadas = {
            f.isoformat()
            for f in list(cortes.get('cortes') or []) + [cortes.get('actual')]
            if f
        }
        if not fechas_guardadas & set(fechas_semestrales):
            cortes = None

    # Cédulas de un área concreta: subcuentas y título del área
    titulo = None
    subcuentas = []
    if not _seccion_de_archivo(file_name):
        cuenta_area = determinar_cuenta_por_nombre_archivo(file_name)
        if cuenta_area:
            # Cédula de un área concreta (Caja y Bancos, Inventarios...): lista
            # el detalle de subcuentas, igual que las cédulas de Revisoría.
            titulo = cuenta_area
            subcuentas = _subcuentas_de_cuenta(
                audit_id, balances, cuenta_area, fechas_semestrales)
        else:
            # Cédula genérica de 'OTRAS CEDULAS SUMARIAS': el cliente pidió
            # CUENTA Y CANTIDAD, así que se escribe la cuenta misma y NO sus
            # subcuentas (antes salían los nombres de las subcuentas en vez de
            # la cuenta).
            titulo = _cuenta_generica(balances, fechas_semestrales, file_name)

    for hoja in workbook.worksheets:
        layout = detectar_layout(hoja)
        if not layout:
            continue

        escritas = escribir_sumaria(
            layout, cuentas, fechas_ordenadas, ajustes_reclasificaciones,
            referencias, cortes=cortes, subcuentas=subcuentas, titulo=titulo,
        )
        if escritas:
            logger.info(
                'SUMARIA %s: %s fila(s) escritas en la hoja %r',
                file_name, escritas, hoja.title,
            )
        return workbook

    logger.info(
        'SUMARIA %s: la plantilla no es una cédula de saldos; se deja intacta.',
        file_name,
    )
    return workbook
