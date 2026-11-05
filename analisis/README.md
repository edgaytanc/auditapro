# Audita Análisis — módulo de AuditaPro

El auditor sube **su papel de trabajo (Excel)**, el **auxiliar** y los **documentos del cliente**
(PDF, Word, Excel, CSV). El **orquestador** reconoce el papel y activa solo los agentes necesarios;
los agentes analizan y **el resultado se escribe en una copia del mismo papel de trabajo**, con
cada cifra enlazada a su archivo y página. El auditor revisa, decide y aprueba.

English version: [README.en.md](README.en.md)

## Reglas que el código hace cumplir

| Regla | Cómo se cumple | Prueba |
|---|---|---|
| Los números los calcula el código, no la IA | `engine/` usa `Decimal`; la IA es opcional y solo clasifica/redacta | `test_ai.py` |
| El original nunca se modifica | Se lee, se escribe en una copia `_llenado.xlsx` y se compara el SHA-256 antes/después | `test_template.py` |
| Una fórmula jamás se sobrescribe | Rango destino verificado; si está ocupado: siguiente celda libre / cancelar; las fórmulas nunca se pisan | `test_template.py` |
| Texto de un documento que empieza con `=` no se vuelve fórmula | Se guarda como texto; el CSV lo neutraliza | `test_template.py` |
| Toda cifra tiene origen | `CifraAnalisis` (archivo, hoja, filas/página, coordenadas) + comentario en la celda | `test_template.py` |
| La copia se verifica | Tras guardar se compara celda por celda con el original; si algo cambió fuera del rango, no se entrega. Lo que la copia no conserve (formas, imágenes, formato condicional…) se advierte | `test_template.py`, `test_plantillas_reales.py` |
| Propuesto ≠ aprobado | Solo el jefe de auditoría del proyecto aprueba, y solo si todas las cifras cuadran con su origen | `test_template.py` |
| Bitácora (NIA 230) | Encadenada con hash, solo se agrega | `test_template.py` |
| Una alerta no demuestra fraude | Texto fijo en pantalla y en el papel; la conclusión es del auditor | `test_views.py` |

## Que no se sobrecargue el sistema

- **Validación de archivos** antes de guardar: lista de formatos, contenido real (no solo extensión),
  anti «bomba zip», archivos vacíos, nombre interno aleatorio, SHA-256, almacenamiento privado
  (fuera de `static/` y `media/`).
- **Límites** (variables de entorno, ver abajo): tamaño por archivo y total, cantidad de archivos,
  filas leídas, páginas de PDF. Si un archivo supera el límite se lee hasta el límite **y se avisa**.
- **Cola acotada**: `ANALISIS_MAX_WORKERS` trabajadores; tope global y por usuario de corridas
  activas (lo que lo excede se rechaza con mensaje). Una corrida sin avance por
  `ANALISIS_STALE_MINUTES` se marca con error (`python manage.py analisis_recuperar`).
- **Lectura en flujo** (`openpyxl` read-only) y sin cargar archivos enteros en memoria.
- **Medido**: auxiliar de 50,000 filas + PDF de 100 páginas + papel de trabajo, 4 agentes:
  **≈ 56 s** y **≈ 104 MB** de pico (Python) en una máquina de desarrollo
  (`ANALISIS_SLOW_TESTS=1 python manage.py test analisis.tests.test_performance`). Criterio de la
  guía: menos de 5 minutos.

## Flujo en pantalla (menú «Audita Análisis», `/analisis/`)

1. **Nuevo análisis**: proyecto, instrucción en lenguaje natural, archivos, agentes (opcional),
   parámetros y columnas (opcional; se detectan por encabezado).
2. **Corrida** (en segundo plano, con avance en vivo): 01 Lectura/clasificación por página →
   02 Extracción → 03 Cruce documento↔auxiliar → 04 Agentes → consolidación → llenado del papel.
3. **Resultado**: plan del orquestador (cada agente «activo» o «no se usa» con su razón), 9
   indicadores, conclusión, tablas (cruce, análisis por agente, pruebas adicionales), riesgos y
   hallazgos con decisión del auditor (aceptar / descartar con motivo).
4. **Papel de trabajo**: copia llenada por versiones, «pegar de nuevo» con hoja/celda/conflicto,
   hoja «Evidencia», comentario con el origen en cada cifra.
5. **Validar cédula** (relee cada cifra desde su archivo) → **Aprobar** (jefe de auditoría).
6. Clic en cualquier cifra: visor de origen (fila y vecinas en Excel; página del PDF con el importe resaltado).

### Los 4 agentes (NIA)

| Agente | Prueba principal | Pruebas adicionales |
|---|---|---|
| Datos masivos (500·530) | Sumaria por grupo, concentración > 30 % | Estadísticas, top 10 con cobertura, cuadre contra el mayor, corte ±10 días |
| Predictivo (520·315) | Serie mensual, tendencia (mínimos cuadrados), ±30 %, proyección | Estacionalidad y cierre, semestres por grupo, análisis horizontal |
| Detección de fraudes (240·330) | Duplicados, atípicos (\|z\|>3), montos redondos, fin de semana, Benford | Bajo el límite de autorización, numeración consecutiva, proveedor ocasional, documentos fuera del auxiliar |
| Revisión de contratos (500·501·250) | Vigencia al cierre | Contratos leídos de PDF/Word, cláusulas de riesgo, gasto vs. contrato, facturas posteriores al vencimiento |

«Informes» no es un quinto agente: la consolidación la hace `engine/consolidate.py` (la guía del
Portal propone mantenerlo dentro del asistente de Cierre; se puede separar si el cliente lo decide).

## Regla de pegado: cada dato en su columna (todas las plantillas)

Regla del cliente (guía «Prueba de Ingresos PT A-11»): cada plantilla tiene su tabla con sus columnas y sus nombres;
ahí se pegan las transacciones, sustituyendo los ejemplos. Se aplica a cualquier plantilla con una tabla de
transacciones (encabezados con monto y fecha o número de documento, y una fila TOTAL con `=SUM`).

- **Columna por nombre**: cada columna del papel se empareja con la del archivo que tiene su nombre o un sinónimo
  («Monto Doc. (Q)» ← `Total_Facturado`, «Boleta No.» ← `Referencia_Bancaria`, «Banco» ← `Cuenta_Bancaria_Destino`,
  «Tipo Doc.» ← «Factura» si el archivo tiene número de factura…). El encabezado lleva un comentario con el origen.
- **Una transacción por fila**; si no caben, **la tabla crece** (se insertan filas como en Excel): el `=SUM` del total
  se agranda solo y lo de abajo (atributos, control interno, conclusión, firmas) baja con sus fórmulas, celdas
  combinadas, formatos, validaciones y área de impresión (`engine/sheet_rows.py`). Hasta 5,000 filas; más que eso,
  integración mensual + hoja «Detalle integración».
- **Observaciones** = análisis del sistema por transacción (estado y método de cobro si existen, más la alerta:
  duplicado, atípico, fin de semana, cotejo con documento… o «Sin alertas en las pruebas del sistema»).
- Lo del auditor queda vacío (fecha y monto del depósito, atributos ✓/✗) y la fórmula que depende de ello se
  condiciona: `=J19-F19` pasa a `=IF(J19="","",J19-F19)` para no mostrar diferencias falsas.
- **Parámetros de la prueba** completados (período, población, muestra 100 %, método, cuentas revisadas).
- **Conclusión**: la de ejemplo de la plantilla se sustituye por la propuesta (pendiente de firma; el texto original
  queda en un comentario). Los «✓ Cumple» de ejemplo del control interno pasan a «Por evaluar».
- **Lo demás va en hojas aparte**: «ANÁLISIS AGENTES» (sumarias, estadísticas, corte, fraude, riesgos, hallazgos,
  resumen y fuentes) y «Evidencia». Nada se pega debajo del papel.
- Con varios auxiliares, la tabla se llena con el que tiene las columnas de la plantilla (p. ej. el reporte de
  facturas y no el libro mayor).
- La copia se verifica contra el original con el desplazamiento de filas: ninguna fórmula del papel se pierde.
- Pruebas: `test_ingresos_a11.py` (500 facturas, plantilla real PT A-11), `test_egresos_a12.py` (70 egresos, A-12) y
  la de las 538 plantillas con dos juegos de datos.

En **ingresos** las facturas son de la entidad: no aplica el límite de autorización (es de pagos) ni la numeración
consecutiva de proveedor; se prueba la **correlatividad** (saltos en la numeración, atributo 3).

Reglas afinadas en esta prueba de gastos: los **pagos recurrentes** (alquiler, honorario fijo) no son duplicados ni
montos redondos; la **numeración consecutiva** solo aplica a facturas del proveedor (no a cheques propios); la
**vigencia por fila** solo si la columna es de vencimiento (en un libro de transacciones la vigencia sale del
contrato); una factura del mismo proveedor y fecha con otro monto se informa como **«importe difiere»**; y el
análisis no se marca «Terminado» hasta que el papel está llenado.

## Claude (opcional)

Sin clave el sistema funciona completo con reglas. Con clave, Claude: clasifica páginas dudosas,
lee campos de documentos difíciles (con evidencia literal obligatoria), interpreta el pedido del auditor
y redacta la conclusión. **Toda respuesta se valida contra un esquema; todo número redactado debe
existir en los datos calculados o se descarta.** El contenido de los documentos se trata como dato,
no como instrucciones. Se envía solo el texto necesario (máx. 6,000 caracteres por página) —
documentar esto con el cliente antes de producción (retención de datos del proveedor).

> **La clave nunca va en el repositorio.** Se lee de la variable de entorno `ANTHROPIC_API_KEY`.

## Configuración (variables de entorno)

| Variable | Defecto | Para qué |
|---|---|---|
| `ANTHROPIC_API_KEY` | vacío | Clave de Claude. Vacío = sin IA |
| `ANALISIS_USE_AI` | `True` | Apagar la IA aunque haya clave |
| `ANALISIS_CLAUDE_MODEL` | `claude-sonnet-5-5` | Modelo |
| `ANALISIS_STORAGE_ROOT` | `./private_analisis` | **En producción, un volumen persistente** (en Docker, montar `/app/private_analisis`) |
| `ANALISIS_MAX_FILE_MB` / `_TOTAL_MB` / `_FILES` | 100 / 400 / 40 | Límites de subida |
| `ANALISIS_MAX_ROWS` / `_MAX_PDF_PAGES` | 100000 / 300 | Límites de lectura |
| `ANALISIS_MAX_WORKERS` / `_MAX_QUEUE` / `_MAX_ACTIVE_PER_USER` | 2 / 8 / 2 | Cola acotada |
| `ANALISIS_STALE_MINUTES` | 20 | Corrida sin avance = con error |

Instalar dependencias nuevas: `pip install -r requirements.txt` (openpyxl, python-docx, pdfplumber, requests).
Migrar: `python manage.py migrate`.

## Pruebas

```
python manage.py test analisis --settings=saas_project.settings_test
```
120 pruebas (la de rendimiento y la de las 538 plantillas se saltan salvo `ANALISIS_SLOW_TESTS=1`). Requieren `reportlab` solo para
generar PDFs de ejemplo. `saas_project/settings_test.py` solo desactiva el manifiesto de estáticos.

## Lo que NO incluye esta versión (decisiones pendientes)

- **Portal del Cliente** y **Monitoreo Continuo (carpeta 8)**: son otros módulos de las guías; este
  entregable es Audita Análisis. `services.create_run()` es el punto de enlace para «Aceptar y analizar».
- **OCR** de PDF escaneados o imágenes: se clasifican como «Evidencia sin texto», se avisan y quedan
  para revisión manual (la guía propone Tesseract o visión de Claude).
- **Tarjetas de decisión** que pausan al agente, **PBC**, **créditos/planes**, **expediente cerrado**
  y **aislamiento por firma**: AuditaPro aísla por proyecto de auditoría y por rol; no se creó el modelo multi-firma.
- **Plantillas reales del Módulo Auditoría** (`static/templates_base_financiera`, `_interna`, `_revisoria`): probadas
  las **538** (437 Financiera, 67 Interna, 34 Revisoría Fiscal). Todas se llenan y pasan la verificación celda por celda;
  0 fórmulas sobrescritas (26,765 fórmulas en 386 plantillas). 4 copias no conservan un elemento gráfico menor
  (un cuadro de texto vacío en Revisoría «Centralizadora del pasivo» y en «… del estado de resultados», líneas
  dibujadas en «Fase 1 Planeación», y 1 regla de formato condicional extendido en Financiera «Evaluación de procesos – Cuentas por
  cobrar»): **el sistema lo advierte** en la versión del papel. Prueba: `test_plantillas_reales.py`
  (todas con `ANALISIS_SLOW_TESTS=1`).
- Páginas de **Word** = secciones por saltos de página (Word no guarda páginas fijas).
- La cola es de hilos en el proceso web. Con varios procesos o mucha carga, migrar a Celery/RQ como propone la guía.
- La API de Claude se probó en vivo (clasificar, extraer con evidencia, interpretar el pedido, redactar la conclusión).
