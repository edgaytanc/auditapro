"""Tablas de configuración del flujo de hallazgos (fase 2).

Las guías del cliente piden que cuenta → plantillas, área → informe y las referencias NO estén escritas a
mano dentro de cada Excel. Aquí viven los valores por defecto; la tabla ``MapaConfig`` de la base de datos
los puede sustituir sin tocar código (ver ``mapa()``).
"""
from __future__ import annotations

SEVERIDADES = ("Crítica", "Alta", "Media", "Baja")
ORDEN_SEVERIDAD = {s: i for i, s in enumerate(SEVERIDADES)}
# Las plantillas solo traen Alta/Media/Baja en «Prioridad»; la Crítica se agrega a la lista de validación.
CLASIFICACIONES_FIN = ("Control Interno", "Cumplimiento Normativo", "Presentación de EEFF")
CLASIFICACIONES_AI = ("Control Interno", "Presentación EE.FF.", "Cumplimiento Legal", "Operativos", "Fraude / Irregularidades")
TIPOS_EVIDENCIA = {"D": "Documental", "T": "Testimonial", "F": "Física", "A": "Analítica", "C": "Confirmación", "O": "Observación"}

# Estados del hallazgo (guías, sección 9)
BORRADOR, EN_PAPEL, EN_REVISION, APROBADO, DEVUELTO, RECHAZADO, INCLUIDO = (
    "borrador", "en_papel", "en_revision", "aprobado", "devuelto", "rechazado", "incluido")
ETIQUETA_ESTADO = {
    BORRADOR: "Borrador", EN_PAPEL: "En papel de trabajo", EN_REVISION: "En revisión", APROBADO: "Aprobado",
    DEVUELTO: "Devuelto", RECHAZADO: "Rechazado", INCLUIDO: "Incluido en informe",
}
# Lista que ve el auditor en la columna «Estado» de la plantilla (se amplía la validación original).
ESTADOS_PLANTILLA = ",".join(["Abierto", "En Proceso", "Cerrado", "No Aplica", *ETIQUETA_ESTADO.values()])

MARCA_AUDITA = "A.A."  # marca estándar «hallazgo generado por Audita Análisis»
MARCA_AUDITA_TEXTO = "A.A. = hallazgo generado por Audita Análisis (pendiente de revisión del auditor)"

# ----------------------------------------------------------------------------- Financiera (guía, sección 4)
# clave → (carpeta de 4 PRUEBAS SUSTANTIVAS, nombre de cuenta, hallazgos, evidencias, ref. hallazgos, ref. evidencias)
CUENTAS_FIN: dict[str, dict] = {
    "caja": {"nombre": "Caja y Bancos", "carpeta": "1 CAJA Y BANCOS", "h": "17_HALLAZGOS.xlsx", "e": "18_EVIDENCIAS.xlsx", "rh": "A-21", "re": "A-22"},
    "cxc": {"nombre": "Cuentas por Cobrar", "carpeta": "2 CUENTAS POR COBRAR", "h": "15_HALLAZGOS.xlsx", "e": "16_EVIDENCIAS.xlsx", "rh": "B-17", "re": "B-18"},
    "inversiones": {"nombre": "Inversiones", "carpeta": "3 INVERSIONES", "h": "7_HALLAZGOS.xlsx", "e": "8_EVIDENCIAS.xlsx", "rh": "C-6", "re": "C-7"},
    "inventarios": {"nombre": "Inventarios", "carpeta": "4 INVENTARIOS", "h": "16_HALLAZGOS.xlsx", "e": "17_EVIDENCIAS.xlsx", "rh": "D-15", "re": "D-16"},
    "construcciones": {"nombre": "Construcciones en Proceso", "carpeta": "5 CONSTRUCCIONES EN PROCESO", "h": "13_HALLAZGOS.xlsx", "e": "14_EVIDENCIAS.xlsx", "rh": "E-13", "re": "E-14"},
    "activos_fijos": {"nombre": "Activos Fijos", "carpeta": "6 AUDITORIA ACTIVOS FIJOS", "h": "13_HALLAZGOS.xlsx", "e": "14_EVIDENCIAS.xlsx", "rh": "F-12", "re": "F-13"},
    "intangible": {"nombre": "Activo Intangible", "carpeta": "7 AUDITORIA ACTIVO INTANGIBLE", "h": "10_HALLAZGOS.xlsx", "e": "11_EVIDENCIAS.xlsx", "rh": "G-9", "re": "G-10"},
    "cxp": {"nombre": "Cuentas por Pagar", "carpeta": "9 AUDITORIA CUENTAS POR PAGAR", "h": "19_HALLAZGOS.xlsx", "e": "20_EVIDENCIAS.xlsx", "rh": "H-20", "re": "H-21"},
    "pasivo_lp": {"nombre": "Pasivo Largo Plazo", "carpeta": "10 AUDITORIA PASIVO LARGO PLAZO", "h": "9_HALLAZGOS.xlsx", "e": "10_EVIDENCIAS.xlsx", "rh": "I-9", "re": "I-10"},
    "patrimonio": {"nombre": "Patrimonio", "carpeta": "11  AUDITORIA PATRIMONIO", "h": "8_HALLAZGOS.xlsx", "e": "9_EVIDENCIAS.xlsx", "rh": "J-7", "re": "J-8"},
    "resultados": {"nombre": "Estado de Resultados", "carpeta": "13  AUDITORIA DE ESTADO RESULTADOS", "h": "13_HALLAZGOS.xlsx", "e": "14_EVIDENCIAS.xlsx", "rh": "R-12", "re": "R-13"},
}
# Carpetas 8 y 12 (Otras Cédulas Sumarias): «por definir» en la guía → no generan hallazgos.
RAIZ_PRUEBAS_FIN = "4 PRUEBAS SUSTANTIVAS"

# ----------------------------------------------------------------------------- Auditoría Interna (guía, sección 5)
AREAS_AI: dict[str, dict] = {
    "contabilidad": {"nombre": "Contabilidad", "informe": "1 Informe Auditoria Contabilidad.docx", "ref": "5.1.1"},
    "tesoreria": {"nombre": "Tesorería", "informe": "2 Informe de Auditoría Tesorería.docx", "ref": "5.1.2"},
    "anticipo": {"nombre": "Anticipo", "informe": "3 Infome Auditoría Anticipo.docx", "ref": "5.1.3"},
    "creditos": {"nombre": "Créditos", "informe": "4 Informe Auditoría Créditos.docx", "ref": "5.1.4"},
    "inventarios": {"nombre": "Inventarios", "informe": "5 Informe Auditoría Inventarios.docx", "ref": "5.1.5"},
    "compras": {"nombre": "Compras", "informe": "6 Informe Auditoría Compras.docx", "ref": "5.1.6"},
    "ventas": {"nombre": "Ventas", "informe": "7 Informe Auditoría Ventas.docx", "ref": "5.1.7"},
    "presupuestos": {"nombre": "Presupuestos", "informe": "8 Informe Auditoría Presupuestos.docx", "ref": "5.1.8"},
    "rrhh": {"nombre": "Recursos Humanos", "informe": "9 Informe Auditoría Recursos Humanos.docx", "ref": "5.1.9"},
    "juridico": {"nombre": "Jurídico", "informe": "10 Informe Auditoría Jurídico.docx", "ref": "5.1.10"},
    "informatica": {"nombre": "Informática", "informe": "11 Informe Auditoría Informatica.docx", "ref": "5.1.11"},
    "transversal": {"nombre": "Transversal / sin área", "informe": "", "ref": "5.1.12 y 5.1.13"},
}
CARPETA_INFORMES_AI = "5 INFORME/8 INFORMES ESPECIFICOS POR AREAS"
REFS_AI = {"hallazgos": "5.2", "evidencias": "5.3", "borrador": "5.6"}

# ----------------------------------------------------------------------------- Revisoría Fiscal (guía, secciones 3 y 11)
REFS_RF = {"hallazgos": "4.3", "evidencias": "4.4", "comunicacion": "4.5"}
NOMBRES_RF = {"hallazgos": "3_Hallazgos.xlsx", "evidencias": "4_Evidencias.xlsx", "comunicacion": "5_COMUNICACION.xlsx"}
CARPETA_RF = "4 COMUNICACION"
HOJA_R3 = "R-3"
ENCABEZADO_R3_SECCION7 = "7. HALLAZGOS Y RECOMENDACIONES"
NOMBRE_BLOQUE_R3 = "HALLAZGOS_R3"

MODULOS = {"F": "financiera", "I": "interna", "R": "revisoria"}
NOMBRE_MODULO = {"F": "Auditoría Financiera", "I": "Auditoría Interna", "R": "Revisoría Fiscal"}

# Normativa que cita cada módulo en «Criterio» cuando el análisis no trae una propia.
CRITERIO_POR_DEFECTO = {
    "F": "NIA 315 / NIA 330 / NIA 450 (identificación y evaluación de incorrecciones) y NIA 265 (comunicación de deficiencias).",
    "I": "Normas Globales de Auditoría Interna del IIA y el marco de control interno de la entidad.",
    "R": "NIA 265 / NIA 450 / NIA 500 y las obligaciones del revisor fiscal.",
}


def mapa(tipo: str, defecto: dict) -> dict:
    """Devuelve el mapa ``tipo`` de la base de datos si el administrador lo editó; si no, el valor por defecto."""
    try:
        from ..models import MapaConfig

        row = MapaConfig.objects.filter(tipo=tipo).first()
        if row and row.datos:
            return row.datos
    except Exception:  # noqa: BLE001 - tabla aún sin migrar
        pass
    return defecto


def cuentas_fin() -> dict:
    return mapa("cuentas_fin", CUENTAS_FIN)


def areas_ai() -> dict:
    return mapa("areas_ai", AREAS_AI)
