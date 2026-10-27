"""Enlaces de compra suministrados por AuditaPro en los DOCX del paquete.

IMPORTANTE: Los enlaces checkout-session podrían caducar; confirmar con ventas.
Para reemplazar uno, actualizar este diccionario y probar el destino.
"""

ENLACES = {
    "auditapro-mensual": "https://app.recurrente.com/s/auditoriapractica/auditapro-mensual",
    "auditapro-anual": "https://app.recurrente.com/checkout-session/ch_2fpcaoagpqj2zlfb",
    "analisis-mensual": "https://app.recurrente.com/s/auditoriapractica/acceso-audita-ia-analisis",
    "analisis-max-anual": "https://app.recurrente.com/s/auditoriapractica/audita-ia-anual",
    "grupo-2": "https://app.recurrente.com/s/auditoriapractica/2-usuarios-298-ano-auditapro-anual-en-equipo",
    # Según el documento proporcionado. Comprobar que la página efectivamente
    # corresponde a 3 usuarios/$399: su slug indica un paquete más amplio.
    "grupo-3": "https://app.recurrente.com/s/auditoriapractica/acceso-completo-ecosistema-audita",
    "renovacion-anual": "https://app.recurrente.com/checkout-session/ch_hw8ajkciigeqeegs",
}
