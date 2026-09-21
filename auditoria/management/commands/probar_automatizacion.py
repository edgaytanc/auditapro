"""
Prueba de extremo a extremo de las automatizaciones con el Excel Financiero.

Uso:
    python manage.py probar_automatizacion --excel "<ruta al Excel Financiero>" \
        [--salida <carpeta de evidencias>] [--mantener]

Qué hace, para Auditoría Financiera y Auditoría Interna:

  1. Crea una auditoría de prueba (entidad, período, tipo y moneda propios).
  2. Importa el Excel Financiero por el mismo camino que usa el botón
     «Importar → Excel Financiero» de la pantalla de Papeles de Trabajo.
  3. Descarga un conjunto de plantillas por el mismo camino que el usuario
     (modify_document_excel + marcas + referencia propia) y las guarda como
     evidencia.
  4. Comprueba sobre el archivo descargado:
       · Encabezado: Entidad, Auditoría (tipo), Período y Moneda.
       · Referencia propia del papel (celda 'Ref.').
       · Centralizadoras: cuentas, importes y columna Ref P/T (A-1, H-1, J-1…).
       · Cédulas sumarias: cuenta e importes.
       · Materialidad NIA 320 e Importancia Relativa: bases llenas.
       · Análisis Horizontal/Vertical: cuentas y rótulos de año.

Devuelve código de salida 1 si alguna comprobación falla.
"""

import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from audits.models import Audit

SALIDA_POR_DEFECTO = os.path.join('..', 'entregables_daniel', 'evidencias_verificacion')

# Papeles que se descargan y comprueban por tipo de auditoría.
# (carpeta, archivo, [comprobaciones])
PAPELES_FINANCIERA = [
    ('4 PRUEBAS SUSTANTIVAS', 'CENTRALIZADORA_BALANCE.xlsx',
     ['encabezado', 'centralizadora']),
    ('4 PRUEBAS SUSTANTIVAS', 'CENTRALIZADORA_DEL_ACTIVO_.xlsx',
     ['encabezado', 'centralizadora']),
    ('4 PRUEBAS SUSTANTIVAS', 'CENTRALIZADORA_DEL_PASIVO_Y_PATRIMONIO.xlsx',
     ['encabezado', 'centralizadora']),
    ('4 PRUEBAS SUSTANTIVAS', 'CENTRALIZADORA__DEL_ESTADO_DE_RESULTADOS.xlsx',
     ['encabezado', 'centralizadora']),
    ('4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS', '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx',
     ['encabezado', 'sumaria', 'ref_propia', 'sumaria_caja']),
    ('4 PRUEBAS SUSTANTIVAS/9 AUDITORIA CUENTAS POR PAGAR', '2_SUMARIA_CUENTAS_POR_PAGAR.xlsx',
     ['encabezado', 'sumaria', 'ref_propia']),
    ('4 PRUEBAS SUSTANTIVAS/11  AUDITORIA PATRIMONIO', '2_SUMARIA_PATRIMONIO.xlsx',
     ['encabezado', 'sumaria', 'ref_propia']),
    ('4 PRUEBAS SUSTANTIVAS/13  AUDITORIA DE ESTADO RESULTADOS', '2_SUMARIA_ESTADO_DE_RESULTADOS.xlsx',
     ['encabezado', 'sumaria', 'ref_propia']),
    ('4 PRUEBAS SUSTANTIVAS/8 OTRAS CEDULAS SUMARIAS', '1 CEDULA_SUMARIA.xlsx',
     ['encabezado']),
    ('4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS', '1_PROGRAMA_AUDITORIA_CAJA_BANCOS.xlsx',
     ['encabezado', 'ref_propia']),
    ('2 PLANEACION/8 Materialidad', 'Materialidad_NIA320.xlsx',
     ['encabezado', 'materialidad']),
    ('2 PLANEACION/7 Importancia Relativa', 'Importancia Relativa.xlsx',
     ['encabezado', 'importancia_relativa']),
    ('2 PLANEACION/4 Revision Informacion y Registros/2 Análisis Financiero Preliminar agregar',
     '1_Analisis_Horizontal.xlsx', ['encabezado', 'analisis_hv']),
    ('2 PLANEACION/4 Revision Informacion y Registros/2 Análisis Financiero Preliminar agregar',
     '2_Analisis_Vertical_.xlsx', ['encabezado', 'analisis_hv']),
    ('1 FASE INICIAL', '1 INICIO_ENCARGO_AUDITORIA.xlsx', ['encabezado', 'ref_propia']),
]

PAPELES_INTERNA = [
    ('3 PLANEACION/3 ANALISIS FINANCIERO', '1_Analisis_Horizontal.xlsx',
     ['encabezado', 'analisis_hv']),
    ('3 PLANEACION/3 ANALISIS FINANCIERO', '2_Analisis_Vertical.xlsx',
     ['encabezado', 'analisis_hv']),
    ('2 PROYECTOS', '1_REUNION_INICIAL.xlsx', ['encabezado', 'ref_propia']),
    ('4 PRUEBAS DE PROCESO', '1_Pruebas_en_Compras.xlsx', ['encabezado', 'ref_propia']),
    ('5 INFORME', '1_Documentacion_Hallazgos.xlsx', ['encabezado', 'ref_propia']),
    ('3 PLANEACION/4 EVALUACION DE  RIESGOS', '1_CUESTIONARIO_IDENTIFICACION_RIESGOS.xlsx',
     ['encabezado', 'ref_propia']),
    ('1 DIRECTRICES', '4  MATRIZ DE AUTORIDADES Y RESPONSABILIDADES.xlsx', ['encabezado']),
    ('7 CALIDAD', '1_Programa_de_Aseguramiento.xlsx', ['encabezado']),
]


def _fecha(valor):
    """Devuelve la fecha con o sin zona horaria según la configuración activa."""
    return timezone.make_aware(valor) if settings.USE_TZ else valor


def _norm(texto):
    """Texto sin tildes, en minúsculas y con espacios colapsados."""
    if texto is None:
        return ''
    s = unicodedata.normalize('NFD', str(texto))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(s.lower().split())


def _textos_de(workbook, max_filas=40):
    """Todos los textos de las primeras filas de cada hoja, normalizados."""
    textos = []
    for hoja in workbook.worksheets:
        for fila in hoja.iter_rows(min_row=1, max_row=min(hoja.max_row, max_filas)):
            for celda in fila:
                if isinstance(celda.value, str) and celda.value.strip():
                    textos.append(_norm(celda.value))
    return textos


class Command(BaseCommand):
    help = 'Prueba de extremo a extremo de las automatizaciones del Excel Financiero.'

    def add_arguments(self, parser):
        parser.add_argument('--excel', required=True, help='Ruta al Excel Financiero')
        parser.add_argument('--salida', default=SALIDA_POR_DEFECTO,
                            help='Carpeta donde guardar las evidencias descargadas')
        parser.add_argument('--mantener', action='store_true',
                            help='No borrar las auditorías de prueba al terminar')

    # ------------------------------------------------------------------
    # Preparación
    # ------------------------------------------------------------------

    def _crear_auditoria(self, tipo, entidad):
        from users.models import Roles
        from django.contrib.auth import get_user_model

        User = get_user_model()
        rol_jefe = Roles.objects.get(name='audit_manager')
        jefe = User.objects.filter(role=rol_jefe).first()
        if not jefe:
            raise CommandError('No hay ningún usuario con rol audit_manager en la base.')

        etiqueta = {'F': 'Auditoria Financiera', 'I': 'Auditoria Interna'}[tipo]
        audit = Audit.objects.create(
            title=f'{etiqueta} - Verificacion Excel Financiero',
            identidad=entidad,
            tipoAuditoria=tipo,
            moneda='GTQ',
            fechaInit=_fecha(datetime(2025, 1, 1)),
            fechaEnd=_fecha(datetime(2025, 12, 31)),
            audit_manager=jefe,
        )
        audit.assigned_users.add(jefe)
        return audit

    def _importar(self, audit, ruta_excel):
        """Importa el Excel por el mismo camino que el botón de la pantalla."""
        from auditoria.imports.estados_financieros_importer import EstadosFinancierosImporter
        from auditoria.utils.import_utils import _wipe_import_data
        from django.db import transaction

        with open(ruta_excel, 'rb') as archivo:
            contenido = archivo.read()

        subido = SimpleUploadedFile(
            os.path.basename(ruta_excel), contenido,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        importer = EstadosFinancierosImporter(subido, audit.id)

        if not importer.validate_file():
            raise CommandError('El Excel no pasó la validación del importador.')

        with transaction.atomic():
            if importer.es_formato_subcuentas():
                _wipe_import_data(audit.id)
            subido.seek(0)
            exito, mensaje = importer.process_file()

        if not exito:
            raise CommandError(f'La importación falló: {mensaje}')
        return mensaje

    def _descargar(self, audit, carpeta, archivo, destino):
        """Reproduce la descarga real del papel de trabajo y devuelve el libro."""
        import openpyxl
        from auditoria.views.utils import get_template_path
        from auditoria.excel_utils import modify_document_excel
        from auditoria.services.audit_mark_processor import AuditMarkProcessor
        from auditoria.services.referencias import obtener_ref, inyectar_ref_propia

        ruta = get_template_path(carpeta, archivo, audit_type=audit.tipoAuditoria)
        if not ruta or not os.path.exists(ruta):
            raise CommandError(f'Plantilla no encontrada: {carpeta}/{archivo}')

        wb = modify_document_excel(ruta, audit)

        try:
            wb = AuditMarkProcessor(audit.id, archivo).process_excel_document(wb)
        except Exception:
            pass

        ref_propia = obtener_ref(audit.tipoAuditoria, carpeta, archivo)
        if ref_propia:
            wb = inyectar_ref_propia(wb, ref_propia)

        os.makedirs(destino, exist_ok=True)
        ruta_salida = os.path.join(destino, archivo)
        wb.save(ruta_salida)

        return (
            openpyxl.load_workbook(ruta_salida),
            openpyxl.load_workbook(ruta),
            ref_propia,
            ruta_salida,
        )

    # ------------------------------------------------------------------
    # Comprobaciones
    # ------------------------------------------------------------------

    def _check_encabezado(self, wb, wb_plantilla, audit, fallos, etiqueta):
        """
        Comprueba el encabezado SOLO en los campos que la plantilla declara.

        No todas las plantillas traen las cuatro líneas: las de instrucciones o
        las matrices de directrices, por ejemplo, no llevan entidad ni período.
        Exigirlas ahí marcaría un fallo que no lo es, así que primero se mira
        qué anclas tiene la plantilla original.
        """
        unido = ' | '.join(_textos_de(wb))
        original = ' | '.join(_textos_de(wb_plantilla))

        marcados = []

        # El ancla es el hueco de la entidad ('Entidad XXXX', 'Entidad:',
        # '[IDENTIDAD]'), no cualquier mención a la palabra en un instructivo.
        tiene_ancla_entidad = bool(re.search(
            r'entidad\s*(x{3,}|:|walmart|tesla)|\[identidad\]|\[nombre_cliente\]|nombre de la entidad',
            original,
        ))

        if tiene_ancla_entidad:
            if _norm(audit.identidad) in unido:
                marcados.append('entidad')
            else:
                fallos.append(f'{etiqueta}: no se pegó la Entidad "{audit.identidad}"')

        tipo_esperado = {'F': 'financiera', 'I': 'interna', 'R': 'revisoria'}[audit.tipoAuditoria]
        if re.search(r'auditor[ií]a (financiera|interna|de procesos)', original):
            if f'auditoria {tipo_esperado}' in unido or _norm(audit.title) in unido:
                marcados.append('tipo')
            else:
                fallos.append(f'{etiqueta}: no se pegó el Tipo de auditoría ({tipo_esperado})')

        if re.search(r'del \d{1,2} de \w+', original):
            if re.search(r'del \d{1,2} de \w+ de \d{4} al \d{1,2} de \w+ de \d{4}', unido):
                marcados.append('periodo')
            else:
                fallos.append(f'{etiqueta}: no se pegó el Período')

        if 'cifras expresadas en' in original or 'cifras expresadas en' in unido:
            if 'quetzales' in unido:
                marcados.append('moneda')
            else:
                fallos.append(f'{etiqueta}: la leyenda de moneda no se actualizó')

        return marcados

    def _check_ref_propia(self, ref, fallos, etiqueta):
        if not ref:
            fallos.append(f'{etiqueta}: el papel no tiene referencia asignada')

    def _check_centralizadora(self, wb, audit, fallos, etiqueta):
        """
        Comprueba los bloques de cuentas de la centralizadora.

        Solo se revisan las filas que van entre un encabezado 'Cuenta' y su
        fila 'Suma ...': el resto de la hoja son rótulos, marcas y la
        conclusión, que no son cuentas.

        En cada fila se exige que la cuenta venga del Excel importado (las
        plantillas oficiales traen cuentas de muestra que hay que limpiar) y
        que su Ref P/T sea la de la cédula sumaria del área.
        """
        from auditoria.models import BalanceCuentas
        from auditoria.services.referencias import ref_para_cuenta

        hoja = wb['Hoja1'] if 'Hoja1' in wb.sheetnames else wb.worksheets[0]

        # Cuenta -> sección con que se importó (la sección manda sobre las
        # palabras clave al asignar la referencia)
        secciones = {}
        for nombre, seccion in BalanceCuentas.objects.filter(audit=audit).values_list(
                'nombre_cuenta', 'seccion'):
            secciones.setdefault(_norm(nombre), seccion)

        cuentas = 0
        con_importe = 0
        con_ref = 0
        en_bloque = False

        for fila in range(1, hoja.max_row + 1):
            valor = hoja.cell(row=fila, column=2).value
            texto = _norm(valor)

            if texto == 'cuenta':          # encabezado: empieza un bloque
                en_bloque = True
                continue
            if texto.startswith(('suma', 'total')):   # fin del bloque
                en_bloque = False
                continue
            if not en_bloque or not isinstance(valor, str) or not valor.strip():
                continue

            nombre = valor.strip()
            cuentas += 1

            if _norm(nombre) not in secciones:
                fallos.append(
                    f'{etiqueta}: quedo la cuenta de muestra "{nombre}" '
                    f'(fila {fila}), que no viene del Excel importado'
                )
                continue

            if any(isinstance(hoja.cell(row=fila, column=col).value, (int, float))
                   for col in range(4, 10)):
                con_importe += 1

            ref = hoja.cell(row=fila, column=3).value
            esperada = ref_para_cuenta(nombre, seccion=secciones[_norm(nombre)])
            if esperada and ref != esperada:
                fallos.append(
                    f'{etiqueta}: la Ref P/T de "{nombre}" es {ref!r} '
                    f'y deberia ser {esperada!r}'
                )
            if isinstance(ref, str) and re.match(r'^[A-Z]-\d+$', ref.strip()):
                con_ref += 1

        if cuentas == 0:
            fallos.append(f'{etiqueta}: la centralizadora no trajo ninguna cuenta')
        if con_importe == 0:
            fallos.append(f'{etiqueta}: la centralizadora no trajo importes')
        if con_ref == 0:
            fallos.append(f'{etiqueta}: la columna Ref P/T quedo vacia (A-1, H-1, J-1...)')

        return {'cuentas': cuentas, 'con_importe': con_importe, 'con_ref': con_ref}


    def _check_rotulos_centralizadora(self, wb, audit, fallos, etiqueta):
        """
        Los rótulos de fecha (fila 12) deben ser las fechas REALES del Excel
        importado, no fechas fabricadas ('Al 01/01/2025').
        """
        from auditoria.services.cortes_excel import cortes_de_auditoria

        cortes = cortes_de_auditoria(audit.id)
        if not cortes:
            return

        hoja = wb['Hoja1'] if 'Hoja1' in wb.sheetnames else wb.worksheets[0]

        esperados = {}
        for col, fecha in zip(('D', 'E', 'F'), cortes['cortes']):
            if fecha:
                esperados[col] = f"Al {fecha.strftime('%d/%m/%Y')}"
        actual = cortes['actual'] or next(
            (f for f in reversed(cortes['cortes']) if f), None)
        if actual:
            esperados['I'] = f"Al {actual.strftime('%d/%m/%Y')}"

        for col, esperado in esperados.items():
            rotulo = hoja[f'{col}12'].value
            if _norm(rotulo) != _norm(esperado):
                fallos.append(
                    f'{etiqueta}: la columna {col} dice {rotulo!r} y el Excel '
                    f'importado pide {esperado!r}'
                )

    def _check_sumaria_caja(self, wb, audit, fallos, etiqueta):
        """
        La sumaria de Caja y Bancos debe traer: el título del área (sin el
        hueco XXXXXXXXX), el detalle de subcuentas del Excel (como Revisoría)
        y el corte del año actual en su columna (para que 'Saldo según
        auditoría' no quede en cero).
        """
        from auditoria.models import RevisoriaSubcuenta

        subcuentas = list(
            RevisoriaSubcuenta.objects
            .filter(audit=audit, cuenta_principal__iexact='Efectivo y Equivalentes')
            .values_list('nombre_subcuenta', flat=True)
        )

        hoja = wb.worksheets[0]
        textos = set()
        for fila in hoja.iter_rows(min_row=1, max_row=min(hoja.max_row, 60)):
            for celda in fila:
                if isinstance(celda.value, str) and celda.value.strip():
                    textos.add(_norm(celda.value))

        if any('sumaria' in t and 'xxx' in t for t in textos):
            fallos.append(f'{etiqueta}: el título sigue con el hueco XXXXXXXXX')

        presentes = 0
        if subcuentas:
            presentes = sum(1 for s in subcuentas if _norm(s) in textos)
            if presentes < min(3, len(subcuentas)):
                fallos.append(
                    f'{etiqueta}: las subcuentas del Excel no aparecen en la '
                    f'cédula ({presentes} de {len(subcuentas)})'
                )

        # Columna G = tercer corte de la plantilla (el que alimenta la fórmula
        # J = G + Debe - Haber del 'Saldo según auditoría').
        numericos_g = sum(
            1 for f in range(9, 41)
            if isinstance(hoja.cell(row=f, column=7).value, (int, float))
        )
        if numericos_g == 0:
            fallos.append(
                f'{etiqueta}: la columna del corte de cierre quedó vacía '
                f"(el 'Saldo según auditoría' saldría 0)"
            )

        return {'subcuentas': len(subcuentas), 'presentes': presentes}

    def _check_sumaria(self, wb, fallos, etiqueta):
        cuentas = 0
        importes = 0
        for hoja in wb.worksheets:
            for fila in range(1, min(hoja.max_row, 60) + 1):
                for col in range(1, 5):
                    valor = hoja.cell(row=fila, column=col).value
                    if isinstance(valor, str) and len(valor.strip()) > 3:
                        texto = _norm(valor)
                        if texto.startswith(('cuenta', 'codigo', 'suma', 'no.', 'fuente',
                                             'objetivo', 'conclusion', 'marcas', 'ref')):
                            continue
                        cuentas += 1
                for col in range(4, 12):
                    if isinstance(hoja.cell(row=fila, column=col).value, (int, float)):
                        importes += 1

        if importes == 0:
            fallos.append(f'{etiqueta}: la cédula sumaria no trajo importes del Excel')
        return {'importes': importes, 'textos': cuentas}

    def _check_bases_capturadas(self, audit, bases, fallos, etiqueta):
        """
        Si el Excel trae 'Total Ingresos' / 'Utilidad antes de impuesto' como
        filas de total, la base de Materialidad debe ser EXACTAMENTE esa cifra
        (trazable al archivo del cliente).
        """
        from auditoria.services.cortes_excel import totales_er_de_auditoria

        ingresos_excel, utilidad_excel = totales_er_de_auditoria(audit.id)
        comparaciones = (
            ('ingresos totales', ingresos_excel, 'Total Ingresos'),
            ('utilidad antes de impuestos', utilidad_excel, 'Utilidad antes de impuesto'),
        )
        for clave, esperado, rotulo in comparaciones:
            if esperado is None:
                continue
            valor = bases.get(clave)
            if isinstance(valor, (int, float)) and abs(valor - esperado) > 0.01:
                fallos.append(
                    f'{etiqueta}: la base "{clave}" es {valor} y el archivo '
                    f'trae {rotulo} = {esperado}'
                )

    def _check_bases(self, wb, fallos, etiqueta, etiquetas_esperadas, nombre_hoja):
        hoja = next(
            (wb[n] for n in wb.sheetnames if nombre_hoja in _norm(n)),
            None,
        )
        if hoja is None:
            fallos.append(f'{etiqueta}: no se encontró la hoja "{nombre_hoja}"')
            return {}

        encontrados = {}
        for fila in range(1, min(hoja.max_row, 60) + 1):
            etiqueta_fila = _norm(hoja.cell(row=fila, column=1).value)
            for esperada in etiquetas_esperadas:
                if esperada in etiqueta_fila:
                    valor = hoja.cell(row=fila, column=2).value
                    encontrados[esperada] = valor

        for esperada in etiquetas_esperadas:
            if esperada not in encontrados:
                fallos.append(f'{etiqueta}: no se localizó la base "{esperada}"')
            elif not isinstance(encontrados[esperada], (int, float)):
                fallos.append(f'{etiqueta}: la base "{esperada}" no quedó con un importe')

        return encontrados

    def _check_analisis_hv(self, wb, fallos, etiqueta, anio_actual=None,
                           anio_anterior=None):
        cuentas = 0
        anios = []
        for hoja in wb.worksheets:
            for fila in range(1, min(hoja.max_row, 80) + 1):
                valor = hoja.cell(row=fila, column=2).value
                if isinstance(valor, str) and valor.strip():
                    cuentas += 1
                for col in (3, 4, 5):
                    rotulo = hoja.cell(row=fila, column=col).value
                    if isinstance(rotulo, str) and re.match(r'^A[ñn]o \d{4}$', rotulo.strip()):
                        anios.append(rotulo.strip())

        if cuentas == 0:
            fallos.append(f'{etiqueta}: el análisis no trajo cuentas')
        if not anios:
            fallos.append(f'{etiqueta}: no se rotularon las columnas de año')

        # Con un solo ejercicio ('si es 2025 pues 2025') NO debe aparecer
        # ningún año que el Excel no traiga (nada de 'Año 2024' inventado).
        if anio_actual:
            permitidos = {f'Año {anio_actual}'}
            if anio_anterior:
                permitidos.add(f'Año {anio_anterior}')
            extranos = sorted(set(anios) - permitidos)
            if extranos:
                fallos.append(
                    f'{etiqueta}: aparecen años que el Excel no trae: {extranos}'
                )
            if f'Año {anio_actual}' not in anios:
                fallos.append(
                    f'{etiqueta}: falta el rótulo del año actual (Año {anio_actual})'
                )

        return {'cuentas': cuentas, 'anios': sorted(set(anios))}

    # ------------------------------------------------------------------
    # Orquestación
    # ------------------------------------------------------------------

    def _probar_tipo(self, tipo, entidad, papeles, ruta_excel, salida, fallos):
        etiqueta_tipo = {'F': 'Auditoría Financiera', 'I': 'Auditoría Interna'}[tipo]
        self.stdout.write('')
        self.stdout.write('=' * 72)
        self.stdout.write(f'{etiqueta_tipo}')
        self.stdout.write('=' * 72)

        audit = self._crear_auditoria(tipo, entidad)
        mensaje = self._importar(audit, ruta_excel)
        self.stdout.write(f'  Importacion: {mensaje}')

        from auditoria.services.parametros_anios import anios_de_auditoria
        anio_actual, anio_anterior = anios_de_auditoria(audit.id)
        self.stdout.write(f'  Anios detectados del Excel -> actual={anio_actual} anterior={anio_anterior}')

        carpeta_salida = os.path.join(salida, etiqueta_tipo.replace(' ', '_'))

        for carpeta, archivo, comprobaciones in papeles:
            etiqueta = f'{etiqueta_tipo} · {archivo}'
            try:
                wb, wb_plantilla, ref, _ruta = self._descargar(
                    audit, carpeta, archivo, carpeta_salida)
            except Exception as error:
                fallos.append(f'{etiqueta}: no se pudo descargar ({error})')
                self.stdout.write(f'  [X] {archivo}: {error}')
                continue

            detalle = []
            if 'encabezado' in comprobaciones:
                marcados = self._check_encabezado(wb, wb_plantilla, audit, fallos, etiqueta)
                detalle.append('encabezado: ' + ('+'.join(marcados) if marcados else 'sin campos'))
            if 'ref_propia' in comprobaciones:
                self._check_ref_propia(ref, fallos, etiqueta)
            if 'centralizadora' in comprobaciones:
                datos = self._check_centralizadora(wb, audit, fallos, etiqueta)
                self._check_rotulos_centralizadora(wb, audit, fallos, etiqueta)
                detalle.append(
                    f"cuentas={datos['cuentas']} importes={datos['con_importe']} refPT={datos['con_ref']}")
            if 'sumaria' in comprobaciones:
                datos = self._check_sumaria(wb, fallos, etiqueta)
                detalle.append(f"importes={datos['importes']}")
            if 'sumaria_caja' in comprobaciones:
                datos = self._check_sumaria_caja(wb, audit, fallos, etiqueta)
                detalle.append(
                    f"subcuentas={datos['presentes']}/{datos['subcuentas']}")
            if 'materialidad' in comprobaciones:
                datos = self._check_bases(
                    wb, fallos, etiqueta,
                    ['utilidad antes de impuestos', 'activos totales',
                     'ingresos totales', 'patrimonio'],
                    'entrada de datos')
                self._check_bases_capturadas(audit, datos, fallos, etiqueta)
                detalle.append(', '.join(f'{k}={v}' for k, v in datos.items()))
            if 'importancia_relativa' in comprobaciones:
                datos = self._check_bases(
                    wb, fallos, etiqueta,
                    ['ingresos totales', 'activos totales', 'utilidad antes'],
                    'datos entrada')
                detalle.append(', '.join(f'{k}={v}' for k, v in datos.items()))
            if 'analisis_hv' in comprobaciones:
                from auditoria.services.parametros_anios import anios_de_auditoria
                anio_actual, anio_anterior = anios_de_auditoria(audit.id)
                datos = self._check_analisis_hv(
                    wb, fallos, etiqueta,
                    anio_actual=anio_actual, anio_anterior=anio_anterior)
                detalle.append(f"cuentas={datos['cuentas']} anios={datos['anios']}")

            marca = 'OK ' if ref is None else f'Ref {ref}'
            extra = (' | ' + ' | '.join(d for d in detalle if d)) if detalle else ''
            self.stdout.write(f'  [{marca}] {archivo}{extra}')

        return audit, carpeta_salida

    def handle(self, *args, **opciones):
        # La consola de Windows suele venir en cp1252 y los mensajes del
        # importador traen emojis; sin esto el informe se corta a mitad.
        for flujo in (sys.stdout, sys.stderr):
            try:
                flujo.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                pass

        ruta_excel = opciones['excel']
        if not os.path.isfile(ruta_excel):
            raise CommandError(f'No existe el Excel indicado: {ruta_excel}')

        salida = opciones['salida']
        if not os.path.isabs(salida):
            salida = os.path.abspath(os.path.join(settings.BASE_DIR, salida))
        if os.path.isdir(salida):
            shutil.rmtree(salida)
        os.makedirs(salida, exist_ok=True)

        self.stdout.write(f'Excel Financiero: {ruta_excel}')
        self.stdout.write(f'Evidencias en:    {salida}')

        fallos = []
        auditorias = []

        try:
            audit_f, _ = self._probar_tipo(
                'F', 'ENTIDAD DEMO, S.A.', PAPELES_FINANCIERA, ruta_excel, salida, fallos)
            auditorias.append(audit_f)

            audit_i, _ = self._probar_tipo(
                'I', 'ENTIDAD DEMO, S.A.', PAPELES_INTERNA, ruta_excel, salida, fallos)
            auditorias.append(audit_i)
        finally:
            if not opciones['mantener']:
                for audit in auditorias:
                    audit.delete()

        self.stdout.write('')
        self.stdout.write('=' * 72)
        if fallos:
            for fallo in fallos:
                self.stdout.write(self.style.ERROR(f'  [X] {fallo}'))
            self.stderr.write(f'\n{len(fallos)} comprobacion(es) fallidas.')
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(
            '[OK] Todas las automatizaciones verificadas con el Excel Financiero.'
        ))
