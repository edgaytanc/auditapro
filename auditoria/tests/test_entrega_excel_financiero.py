"""
Pruebas de la entrega «Excel Financiero + plantillas oficiales 2026».

Cubren, punto por punto, lo que el cliente pidió verificar:

  1. Años (actual/anterior) editables y tomados del Excel al importar.
  2. Bases de Materialidad / Importancia Relativa: 'Ingresos totales' y
     'Utilidad antes de impuesto', con tolerancia de rotulación y respaldo
     calculado mientras el Excel no las traiga.
  3. Plantillas oficiales sin duplicados '_MODIFICADO' y sin carpeta repetida.
  4. Cédulas sumarias: layout real de cada plantilla.
  5. Muestreo: lectura en memoria del Excel de datos y descarga solo en Excel.
  6. Referencias: automáticas, editables por el auditor y pegadas en la plantilla.
"""

import io
import json
import os
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audits.models import Audit
from users.models import Roles

from auditoria.models import ParametrosAuditoria, ReferenciaPapelTrabajo
from auditoria.services import muestreo_datos, muestreo_nia530
from auditoria.services.parametros_anios import (
    actualizar_anios_desde_import,
    anios_de_auditoria,
    guardar_anios_manuales,
)
from auditoria.services.referencias import (
    inyectar_ref_propia,
    obtener_ref,
    ref_automatica,
    ref_para_cuenta,
)
from auditoria.processors.excel.importance_relativa.datos_entrada import (
    calcular_ingresos_totales,
    calcular_utilidad_antes_impuesto,
)
from auditoria.processors.excel.sumaria.layout import detectar_layout
from auditoria.management.commands.sync_plantillas import es_archivo_excluido

User = get_user_model()

RAIZ_FINANCIERA = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')
RAIZ_INTERNA = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')


def _crear_auditoria(tipo='F'):
    rol, _ = Roles.objects.get_or_create(name='audit_manager')
    jefe = User.objects.create_user(
        username=f'jefe_{tipo}_{Audit.objects.count()}',
        password='clave-de-prueba',
        role=rol,
    )
    audit = Audit.objects.create(
        title='Auditoria de prueba',
        identidad='ENTIDAD DEMO, S.A.',
        tipoAuditoria=tipo,
        moneda='GTQ',
        fechaInit=datetime(2025, 1, 1),
        fechaEnd=datetime(2025, 12, 31),
        audit_manager=jefe,
    )
    audit.assigned_users.add(jefe)
    return audit, jefe


# ---------------------------------------------------------------------
# 1. Años de la auditoría
# ---------------------------------------------------------------------

class AniosAuditoriaTestCase(TestCase):
    """Observación 1: años editables y actualizados desde el Excel."""

    def setUp(self):
        self.audit, self.jefe = _crear_auditoria()

    def test_import_toma_los_dos_anios_cuando_los_cortes_difieren(self):
        actual, anterior = actualizar_anios_desde_import(
            self.audit.id, date(2024, 12, 31), date(2025, 12, 31))
        self.assertEqual((actual, anterior), (2025, 2024))

    def test_cortes_iguales_deducen_el_anio_anterior(self):
        """El Excel de ejemplo trae 'Al 31/12/2025' en los dos cortes."""
        actual, anterior = actualizar_anios_desde_import(
            self.audit.id, date(2025, 12, 31), date(2025, 12, 31))
        self.assertEqual(actual, 2025)
        self.assertEqual(anterior, 2024)

    def test_el_auditor_puede_editar_los_anios(self):
        guardar_anios_manuales(self.audit.id, 2026, 2025)
        self.assertEqual(anios_de_auditoria(self.audit.id), (2026, 2025))
        self.assertTrue(ParametrosAuditoria.objects.get(audit=self.audit).anios_manuales)

    def test_reimportar_el_mismo_excel_respeta_la_edicion_manual(self):
        actualizar_anios_desde_import(self.audit.id, date(2024, 12, 31), date(2025, 12, 31))
        guardar_anios_manuales(self.audit.id, 2030, 2029)

        actualizar_anios_desde_import(self.audit.id, date(2024, 12, 31), date(2025, 12, 31))
        self.assertEqual(anios_de_auditoria(self.audit.id), (2030, 2029))

    def test_un_excel_con_otros_anios_si_actualiza(self):
        guardar_anios_manuales(self.audit.id, 2030, 2029)
        actualizar_anios_desde_import(self.audit.id, date(2022, 12, 31), date(2023, 12, 31))
        self.assertEqual(anios_de_auditoria(self.audit.id), (2023, 2022))

    def test_anio_anterior_debe_ser_menor(self):
        with self.assertRaises(ValueError):
            guardar_anios_manuales(self.audit.id, 2025, 2026)

    def test_endpoint_de_anios(self):
        self.client.force_login(self.jefe)
        url = reverse('anios_auditoria', kwargs={'audit_id': self.audit.id})

        respuesta = self.client.post(
            url, data=json.dumps({'anio_actual': 2025, 'anio_anterior': 2024}),
            content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['success'])

        respuesta = self.client.get(url)
        datos = respuesta.json()
        self.assertEqual(datos['anio_actual'], 2025)
        self.assertEqual(datos['anio_anterior'], 2024)
        self.assertTrue(datos['manuales'])


# ---------------------------------------------------------------------
# 2. Bases de Materialidad / Importancia Relativa
# ---------------------------------------------------------------------

class BasesMaterialidadTestCase(TestCase):
    """Observación 2: 'Ingresos totales' y 'Utilidad antes de impuesto'."""

    def test_toma_las_cuentas_del_excel_cuando_existen(self):
        balances = {
            'ANUAL-2025-ESTADO DE RESULTADOS-Ingresos totales': 5_000_000,
            'ANUAL-2025-ESTADO DE RESULTADOS-Utilidad antes de impuesto': 800_000,
        }
        self.assertEqual(calcular_ingresos_totales(balances, '2025'), 5_000_000)
        self.assertEqual(calcular_utilidad_antes_impuesto(balances, '2025'), 800_000)

    def test_tolera_mayusculas_tildes_y_plural(self):
        balances = {
            'ANUAL-2025-ESTADO DE RESULTADOS-INGRESOS TOTALES': 4_000_000,
            'ANUAL-2025-ESTADO DE RESULTADOS-Utilidad Antes de Impuestos': 600_000,
        }
        self.assertEqual(calcular_ingresos_totales(balances, '2025'), 4_000_000)
        self.assertEqual(calcular_utilidad_antes_impuesto(balances, '2025'), 600_000)

    def test_respaldo_calculado_si_el_excel_aun_no_trae_las_cuentas(self):
        """El Excel actual no las incluye: la base no debe quedar en cero."""
        balances = {
            'ANUAL-2025-ESTADO DE RESULTADOS-Ingresos por ventas': 3_000_000,
            'ANUAL-2025-ESTADO DE RESULTADOS-Otros ingresos': 500_000,
            'ANUAL-2025-ESTADO DE RESULTADOS-Gastos de administracion': 900_000,
            'ANUAL-2025-ESTADO DE RESULTADOS-Impuesto corriente': 250_000,
        }
        self.assertEqual(calcular_ingresos_totales(balances, '2025'), 3_500_000)
        # Ingresos - gastos, sin considerar las cuentas de impuesto
        self.assertEqual(calcular_utilidad_antes_impuesto(balances, '2025'), 2_600_000)

    def test_sin_estado_de_resultados_devuelve_none(self):
        self.assertIsNone(calcular_ingresos_totales({}, '2025'))
        self.assertIsNone(calcular_utilidad_antes_impuesto({}, '2025'))


# ---------------------------------------------------------------------
# 3. Plantillas oficiales publicadas
# ---------------------------------------------------------------------

class PlantillasOficialesTestCase(TestCase):
    """Observaciones 3 y 4: sin '_MODIFICADO' y sin carpeta 14 duplicada."""

    def _archivos(self, raiz):
        for carpeta, _sub, archivos in os.walk(raiz):
            for archivo in archivos:
                yield os.path.join(carpeta, archivo)

    def test_no_quedan_plantillas_modificado(self):
        for raiz in (RAIZ_FINANCIERA, RAIZ_INTERNA):
            for ruta in self._archivos(raiz):
                self.assertNotIn('_MODIFICADO', os.path.basename(ruta).upper(),
                                 f'Quedó una plantilla duplicada: {ruta}')

    def test_no_quedan_temporales_de_office(self):
        for raiz in (RAIZ_FINANCIERA, RAIZ_INTERNA):
            for ruta in self._archivos(raiz):
                nombre = os.path.basename(ruta)
                self.assertFalse(es_archivo_excluido(nombre),
                                 f'Quedó un temporal de Office: {ruta}')

    def test_pruebas_sustantivas_sin_numeros_repetidos(self):
        raiz = os.path.join(RAIZ_FINANCIERA, '4 PRUEBAS SUSTANTIVAS')
        numeros = []
        for nombre in os.listdir(raiz):
            if os.path.isdir(os.path.join(raiz, nombre)):
                numeros.append(nombre.split()[0])
        self.assertEqual(len(numeros), len(set(numeros)),
                         f'Hay carpetas con el mismo número: {sorted(numeros)}')

    def test_la_estructura_json_coincide_con_el_disco(self):
        from auditoria.management.commands.verificar_plantillas import (
            archivos_de_json, archivos_en_disco,
        )
        for nombre_json, raiz in (
            ('folder_structure_financiera.json', RAIZ_FINANCIERA),
            ('folder_structure_interna.json', RAIZ_INTERNA),
        ):
            ruta = os.path.join(settings.BASE_DIR, 'auditoria', 'config', nombre_json)
            with open(ruta, encoding='utf-8') as archivo:
                estructura = json.load(archivo)
            self.assertEqual(archivos_de_json(estructura), archivos_en_disco(raiz),
                             f'{nombre_json} no coincide con las plantillas publicadas')


# ---------------------------------------------------------------------
# 4. Layout de las cédulas sumarias
# ---------------------------------------------------------------------

class LayoutSumariaTestCase(TestCase):
    """La cuadrícula se localiza por rótulos, no por celdas fijas."""

    def _abrir(self, ruta_relativa):
        import openpyxl
        return openpyxl.load_workbook(os.path.join(RAIZ_FINANCIERA, ruta_relativa))

    def test_sumaria_clasica_se_detecta(self):
        wb = self._abrir(os.path.join(
            '4 PRUEBAS SUSTANTIVAS', '1 CAJA Y BANCOS',
            '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'))
        layout = detectar_layout(wb.active)

        self.assertIsNotNone(layout, 'No se detectó la cuadrícula de la sumaria')
        # 'Cuenta Contable' está en la columna C y los cortes en E, F y G
        self.assertEqual(layout.col_cuenta, 3)
        self.assertEqual(layout.cols_saldo, [5, 6, 7])
        self.assertEqual((layout.col_debe, layout.col_haber), (8, 9))
        self.assertEqual(layout.col_ref, 4)

    def test_otras_cedulas_sumarias_comparten_layout(self):
        wb = self._abrir(os.path.join(
            '4 PRUEBAS SUSTANTIVAS', '8 OTRAS CEDULAS SUMARIAS', '1 CEDULA_SUMARIA.xlsx'))
        layout = detectar_layout(wb.active)
        self.assertIsNotNone(layout)
        self.assertEqual(layout.col_cuenta, 3)

    def test_sumarias_especializadas_no_se_tocan(self):
        """
        Patrimonio, Activos Fijos y Estado de Resultados son análisis con
        columnas propias: el escritor debe dejarlas intactas en vez de
        descuadrarlas con los saldos del balance.
        """
        especializadas = [
            os.path.join('4 PRUEBAS SUSTANTIVAS', '11  AUDITORIA PATRIMONIO',
                         '2_SUMARIA_PATRIMONIO.xlsx'),
            os.path.join('4 PRUEBAS SUSTANTIVAS', '6 AUDITORIA ACTIVOS FIJOS',
                         '2_SUMARIA_ACTIVOS_FIJOS.xlsx'),
            os.path.join('4 PRUEBAS SUSTANTIVAS', '13  AUDITORIA DE ESTADO RESULTADOS',
                         '2_SUMARIA_ESTADO_DE_RESULTADOS.xlsx'),
        ]
        for ruta in especializadas:
            wb = self._abrir(ruta)
            detectados = [detectar_layout(hoja) for hoja in wb.worksheets]
            self.assertTrue(all(l is None for l in detectados),
                            f'{ruta} no debería tratarse como sumaria de saldos')


# ---------------------------------------------------------------------
# 5. Muestreo NIA 530 con Excel de datos
# ---------------------------------------------------------------------

class MuestreoDatosTestCase(TestCase):
    """El Excel de datos se lee en memoria y nunca se almacena."""

    def setUp(self):
        self.audit, self.jefe = _crear_auditoria()
        self.formato = muestreo_datos.generar_formato_ejemplo()

    def test_el_formato_de_ejemplo_es_legible_por_el_propio_parser(self):
        datos = muestreo_datos.parsear_mayor_auxiliar(io.BytesIO(self.formato))
        self.assertEqual(datos['n'], 5)
        self.assertIn('Cuentas por Cobrar', datos['cuenta'])
        self.assertGreater(datos['bv'], 0)

    def test_archivo_sin_encabezados_da_error_en_espanol(self):
        from openpyxl import Workbook
        libro = Workbook()
        libro.active['A1'] = 'archivo sin la estructura esperada'
        buffer = io.BytesIO()
        libro.save(buffer)
        buffer.seek(0)

        with self.assertRaises(ValueError) as contexto:
            muestreo_datos.parsear_mayor_auxiliar(buffer)
        self.assertIn('encabezados', str(contexto.exception))

    def test_los_parametros_vacios_se_completan_con_el_archivo(self):
        datos = muestreo_datos.parsear_mayor_auxiliar(io.BytesIO(self.formato))
        parametros = muestreo_datos.completar_parametros(
            'aleatorio_simple',
            {'nivel_confianza': 95, 'tolerancia': 0.10, 'materialidad': 5000,
             'poblacion': '', 'sigma': ''},
            datos,
        )
        self.assertEqual(parametros['poblacion'], datos['n'])
        self.assertEqual(parametros['sigma'], datos['sigma'])

    def test_lo_que_el_auditor_escribio_manda_sobre_el_archivo(self):
        datos = muestreo_datos.parsear_mayor_auxiliar(io.BytesIO(self.formato))
        parametros = muestreo_datos.completar_parametros(
            'aleatorio_simple', {'poblacion': 999, 'sigma': 1234.5}, datos)
        self.assertEqual(parametros['poblacion'], 999)
        self.assertEqual(parametros['sigma'], 1234.5)

    def test_la_seleccion_se_mapea_a_las_partidas_reales(self):
        datos = muestreo_datos.parsear_mayor_auxiliar(io.BytesIO(self.formato))
        resultado = muestreo_nia530.calcular_muestreo(
            'aleatorio_simple',
            {'nivel_confianza': 90, 'tolerancia': 0.10, 'materialidad': 100000,
             'poblacion': datos['n'], 'sigma': datos['sigma']},
            audit_id=self.audit.id,
        )
        detalle = muestreo_datos.mapear_seleccion_a_partidas(resultado, datos['partidas'])

        self.assertTrue(detalle, 'No se mapearon las partidas del archivo')
        documentos = {p['documento'] for p in datos['partidas']}
        for item in detalle:
            self.assertIn(item['documento'], documentos)
            self.assertIn('descripcion', item)
            self.assertIn('monto', item)

    def test_endpoint_de_importacion_no_guarda_el_archivo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.jefe)
        url = reverse('muestreo_importar_datos', kwargs={'audit_id': self.audit.id})
        archivo = SimpleUploadedFile(
            'mayor.xlsx', self.formato,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        respuesta = self.client.post(url, {
            'archivo_datos': archivo,
            'metodo': 'aleatorio_simple',
            'parametros': json.dumps({'nivel_confianza': 90, 'tolerancia': 0.10,
                                      'materialidad': 100000}),
        })

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['success'], datos.get('error'))
        self.assertEqual(datos['origen']['partidas'], 5)
        self.assertIn('no se almacenó', datos['mensaje'])

        # El archivo no debe haber quedado en MEDIA_ROOT ni en la carpeta estática
        media = getattr(settings, 'MEDIA_ROOT', None)
        if media and os.path.isdir(media):
            for carpeta, _sub, archivos in os.walk(media):
                for nombre in archivos:
                    self.assertNotIn('mayor', nombre.lower(),
                                     f'El archivo quedó guardado en {carpeta}')

    def test_la_descarga_solo_admite_excel(self):
        self.client.force_login(self.jefe)
        url = reverse('muestreo_descargar', kwargs={'audit_id': self.audit.id})
        parametros = json.dumps({'nivel_confianza': 90, 'tolerancia': 0.10,
                                 'materialidad': 100000, 'poblacion': 100, 'sigma': 500})

        respuesta = self.client.get(url, {'metodo': 'aleatorio_simple',
                                          'parametros': parametros, 'formato': 'word'})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('Excel', respuesta.json()['error'])

        respuesta = self.client.get(url, {'metodo': 'aleatorio_simple',
                                          'parametros': parametros, 'formato': 'excel'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('spreadsheetml', respuesta['Content-Type'])

    def test_el_formato_de_ejemplo_se_puede_descargar(self):
        self.client.force_login(self.jefe)
        url = reverse('muestreo_formato_datos', kwargs={'audit_id': self.audit.id})
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('spreadsheetml', respuesta['Content-Type'])


# ---------------------------------------------------------------------
# 6. Referencias de papeles de trabajo
# ---------------------------------------------------------------------

class ReferenciasTestCase(TestCase):
    """El sistema calcula la Ref.; si el auditor fija la suya, se respeta."""

    def setUp(self):
        self.audit, self.jefe = _crear_auditoria()

    def test_la_sumaria_de_cada_area_conserva_su_letra(self):
        casos = {
            ('4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS',
             '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'): 'A-1',
            ('4 PRUEBAS SUSTANTIVAS/9 AUDITORIA CUENTAS POR PAGAR',
             '2_SUMARIA_CUENTAS_POR_PAGAR.xlsx'): 'H-1',
            ('4 PRUEBAS SUSTANTIVAS/11  AUDITORIA PATRIMONIO',
             '2_SUMARIA_PATRIMONIO.xlsx'): 'J-1',
            ('4 PRUEBAS SUSTANTIVAS/13  AUDITORIA DE ESTADO RESULTADOS',
             '2_SUMARIA_ESTADO_DE_RESULTADOS.xlsx'): 'R-1',
        }
        for (carpeta, archivo), esperada in casos.items():
            self.assertEqual(ref_automatica('F', carpeta, archivo), esperada)

    def test_la_columna_ref_pt_asigna_la_sumaria_de_cada_cuenta(self):
        self.assertEqual(ref_para_cuenta('Caja y Bancos'), 'A-1')
        self.assertEqual(ref_para_cuenta('Efectivo y Equivalentes'), 'A-1')
        self.assertEqual(ref_para_cuenta('Cuentas por Pagar'), 'H-1')
        self.assertEqual(ref_para_cuenta('Resultado del ejercicio', seccion='Patrimonio'), 'J-1')

    def test_la_referencia_del_auditor_manda(self):
        carpeta = '4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS'
        archivo = '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'

        self.assertEqual(obtener_ref('F', carpeta, archivo, audit_id=self.audit.id), 'A-1')

        ReferenciaPapelTrabajo.objects.create(
            audit=self.audit, carpeta=carpeta, archivo=archivo, referencia='CB-100')

        self.assertEqual(obtener_ref('F', carpeta, archivo, audit_id=self.audit.id), 'CB-100')
        # La automática no cambia para el resto de auditorías
        self.assertEqual(ref_automatica('F', carpeta, archivo), 'A-1')

    def test_endpoint_fija_y_restablece_la_referencia(self):
        self.client.force_login(self.jefe)
        url = reverse('referencia_papel', kwargs={'audit_id': self.audit.id})
        cuerpo = {'carpeta': '4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS',
                  'archivo': '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'}

        respuesta = self.client.post(
            url, data=json.dumps({**cuerpo, 'referencia': 'CB-1'}),
            content_type='application/json')
        self.assertTrue(respuesta.json()['manual'])
        self.assertEqual(respuesta.json()['referencia'], 'CB-1')

        # Vaciarla devuelve el papel a la referencia automática
        respuesta = self.client.post(
            url, data=json.dumps({**cuerpo, 'referencia': ''}),
            content_type='application/json')
        self.assertFalse(respuesta.json()['manual'])
        self.assertEqual(respuesta.json()['referencia'], 'A-1')
        self.assertFalse(ReferenciaPapelTrabajo.objects.filter(audit=self.audit).exists())

    def test_la_referencia_se_pega_en_el_hueco_de_la_plantilla(self):
        """Las plantillas traen 'Ref.      XXXXXX' en una sola celda."""
        from openpyxl import Workbook

        libro = Workbook()
        hoja = libro.active
        hoja['L1'] = 'Ref.      XXXXXX'
        inyectar_ref_propia(libro, 'A-1')
        self.assertEqual(hoja['L1'].value, 'Ref.      A-1')

    def test_no_se_pisa_una_referencia_ya_escrita(self):
        from openpyxl import Workbook

        libro = Workbook()
        hoja = libro.active
        hoja['A1'] = 'Ref.'
        hoja['B1'] = 'ESCRITA POR EL AUDITOR'
        inyectar_ref_propia(libro, 'A-1')
        self.assertEqual(hoja['B1'].value, 'ESCRITA POR EL AUDITOR')
