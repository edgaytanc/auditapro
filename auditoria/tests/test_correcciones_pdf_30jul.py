"""
Correcciones del PDF 'REVISION_30_JULIO' entregado por el cliente:

  1. Referencias que no se pegaban en las plantillas Word (incluida la que
     quedaba DETRÁS del recuadro y la plantilla .doc que no se procesaba).
  2. Encabezado: nombre de la ENTIDAD que no llegaba a todas las plantillas.
  3. Cuentas nuevas del Excel Financiero que no llegaban a OTRAS SUMARIAS.
  4. Página de Muestreo MUM entregada por el cliente, integrada al sistema.
"""
import io
import os
import re
import zipfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from docx import Document

from audits.models import Audit
from auditoria.models import ReferenciaPapelTrabajo
from auditoria.processors.excel.sumaria import _cuentas_a_escribir
from auditoria.processors.excel.sumaria.deteccion import (
    cuentas_sin_cedula_propia, numero_de_cedula_generica)
from auditoria.processors.shared.text_replacer import replace_text
from auditoria.services.referencias import inyectar_ref_propia_word
from users.models import Roles

Usuario = get_user_model()

BASE_F = os.path.join('static', 'templates_base_financiera')
BASE_I = os.path.join('static', 'templates_base_interna')


def _texto_de_cuadros(contenido):
    """Texto de cada cuadro de texto del documento Word."""
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    return [' '.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', bloque)).strip()
            for bloque in re.findall(r'<w:txbxContent>(.*?)</w:txbxContent>', xml, re.S)]


class ReferenciasEnWord(TestCase):
    """Punto 1 del PDF: la referencia debe verse en el papel de Word."""

    RUTA_ACTA = os.path.join(
        BASE_I, '3 PLANEACION', '1 PLANEACION ESTRATEGICA',
        '2 Acta_Aprobacion_Plan_Auditoria.docx')
    RUTA_MANUAL = os.path.join(
        BASE_F, '1 FASE INICIAL', '16 Manual de Calidad para Firmas.docx')

    def test_referencia_queda_dentro_del_recuadro_vacio(self):
        """
        El cliente vio la Ref 'detrás del cuadro'. Ahora se escribe DENTRO del
        recuadro vacío que dibuja la plantilla, así queda visible.
        """
        documento = inyectar_ref_propia_word(Document(self.RUTA_ACTA), 'AB25')
        buffer = io.BytesIO()
        documento.save(buffer)
        cuadros = _texto_de_cuadros(buffer.getvalue())
        con_ref = [c for c in cuadros if 'AB25' in c]
        self.assertTrue(con_ref, 'La referencia no quedó dentro del recuadro')
        # Word duplica cada forma: todas las copias deben mostrarla
        self.assertEqual(len(con_ref), len([c for c in cuadros if c]),
                         'Quedó una copia del recuadro sin la referencia')

    def test_manual_de_calidad_es_docx_y_recibe_referencia(self):
        """
        El 'Manual de Calidad para Firmas' venía en formato .doc (Word 97),
        que el sistema no puede rellenar. Ahora es .docx y recibe su Ref.
        """
        self.assertTrue(os.path.exists(self.RUTA_MANUAL),
                        'Falta la versión .docx del Manual de Calidad')
        self.assertFalse(
            os.path.exists(self.RUTA_MANUAL.replace('.docx', '.doc')),
            'Sigue el .doc antiguo, que no admite automatización')

        documento = inyectar_ref_propia_word(Document(self.RUTA_MANUAL), 'A20')
        texto = ' '.join(p.text for p in documento.paragraphs[:4])
        self.assertIn('A20', texto)
        self.assertNotIn('PA-016', texto, 'Quedó el código propio de la plantilla')

    def test_no_se_toca_la_normativa_parecida_a_una_referencia(self):
        """'NIA-530' se parece a una referencia pero no debe sustituirse."""
        from auditoria.services.referencias import _valor_ref_para_grupo

        class Falso:
            def __init__(self, texto):
                self.text = texto

        self.assertIsNone(_valor_ref_para_grupo([Falso('NIA-530')], 'A-1'))
        self.assertEqual(_valor_ref_para_grupo([Falso('PA-016')], 'A-1'), 'A-1')


class EncabezadoEntidad(TestCase):
    """Punto 2 del PDF: el nombre de la entidad no llegaba a las plantillas."""

    REGLAS = [{'pattern': r'Entidad\s+([A-Za-z])\1{2,}',
               'reemplazar_por': '[ENTIDAD_ETIQUETA]'}]
    REEMPLAZOS = {'[ENTIDAD_ETIQUETA]': 'Entidad ABC123'}

    def test_hueco_con_eses_se_rellena(self):
        """'Entidad SSSSSSSS' es el hueco que no se estaba rellenando."""
        salida = replace_text('Entidad  SSSSSSSSSSSSSSSSSS',
                              self.REEMPLAZOS, self.REGLAS)
        self.assertEqual(salida, 'Entidad ABC123')

    def test_hueco_con_equis_sigue_funcionando(self):
        salida = replace_text('Entidad XXXXXXXXXXXXXXXX',
                              self.REEMPLAZOS, self.REGLAS)
        self.assertEqual(salida, 'Entidad ABC123')

    def test_no_pisa_un_nombre_real(self):
        """Una entidad real no debe confundirse con el hueco."""
        salida = replace_text('Entidad Comercial Bancadefe',
                              self.REEMPLAZOS, self.REGLAS)
        self.assertEqual(salida, 'Entidad Comercial Bancadefe')

    def test_entidad_con_barra_invertida_no_rompe(self):
        """Un nombre con '\\' rompía re.sub; ahora se inserta literal."""
        salida = replace_text('Entidad XXXXXXXX',
                              {'[ENTIDAD_ETIQUETA]': r'Entidad A\B'}, self.REGLAS)
        self.assertEqual(salida, r'Entidad A\B')


class CuentasEnOtrasSumarias(TestCase):
    """Punto 3 del PDF: las cuentas nuevas del Excel no llegaban a las cédulas."""

    FECHAS = ['2026-01-01', '2026-07-31', '2026-12-31']

    def _balances(self):
        balances = {}
        for fecha in self.FECHAS:
            for nombre, valor in [
                ('Efectivo y Equivalentes', 1000000), ('inversiones', 5000),
                ('Cuentas por Cobrar', 15000), ('Inventarios', 15000),
                ('Construcciones en Proceso', 15000),
                ('Propiedad, Planta y Equipo', 15000),
                ('Activo Intangible', 100), ('Contratos', 1000000),
            ]:
                balances[f'SEMESTRAL-{fecha}-Activo-{nombre}'] = valor
            balances[f'SEMESTRAL-{fecha}-Pasivo-Cuentas por Pagar'] = 884037246
            balances[f'SEMESTRAL-{fecha}-Patrimonio-Patrimonio'] = 390004000
        return balances

    def test_numero_de_cedula_generica(self):
        self.assertEqual(numero_de_cedula_generica('9 CEDULA_SUMARIA.xlsx'), 9)
        self.assertEqual(numero_de_cedula_generica('1 CEDULA_SUMARIA.xlsx'), 1)
        self.assertIsNone(
            numero_de_cedula_generica('2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'))

    def test_cuenta_nueva_va_a_la_primera_cedula_generica(self):
        """'Contratos' es la cuenta que el cliente agregó a su Excel."""
        pendientes = cuentas_sin_cedula_propia(self._balances(), self.FECHAS)
        self.assertEqual(pendientes[:1], ['Contratos'])

        cuentas = _cuentas_a_escribir(
            self._balances(), self.FECHAS, '1 CEDULA_SUMARIA.xlsx')
        self.assertIn('Contratos', cuentas)
        self.assertTrue(cuentas['Contratos'], 'La cuenta llegó sin importes')

    def test_las_cuentas_con_cedula_propia_no_se_reparten(self):
        """Inversiones o Caja y Bancos ya tienen su cédula: no se duplican."""
        pendientes = cuentas_sin_cedula_propia(self._balances(), self.FECHAS)
        for cuenta in ('inversiones', 'Efectivo y Equivalentes',
                       'Cuentas por Cobrar', 'Inventarios', 'Activo Intangible'):
            self.assertNotIn(cuenta, pendientes)

    def test_cedula_generica_sobrante_queda_en_blanco(self):
        """Si no hay tantas cuentas nuevas, la cédula se queda vacía."""
        cuentas = _cuentas_a_escribir(
            self._balances(), self.FECHAS, '9 CEDULA_SUMARIA.xlsx')
        self.assertEqual(cuentas, {})


class ImportacionDeCuentasNuevas(TestCase):
    """
    Punto 3 del PDF (causa raíz): la cuenta nueva ni siquiera se importaba.

    El importador exigía un código entero en la columna A, pero el propio
    archivo del cliente dice 'EL CODIGO SOLO ES REFERENCIA NO SE AUTOMATIZA':
    las cuentas que él agrega traen texto ahí y quedaban fuera.
    """

    def test_se_descartan_las_notas_del_archivo(self):
        from auditoria.imports.processors.financiera_subcuentas_importer import (
            _es_anotacion)

        for nota in ['EJEMPLO PARA AGREGAR',
                     'El mismo nombre que tiene la cuenta en sistema',
                     'Las cuentas de amarillo son cuentas fijas del sistema',
                     '']:
            self.assertTrue(_es_anotacion(nota), f'Debió descartarse: {nota!r}')

    def test_no_se_descarta_una_cuenta_real(self):
        from auditoria.imports.processors.financiera_subcuentas_importer import (
            _es_anotacion)

        for cuenta in ['Contratos', 'Efectivo y Equivalentes', 'venezuela',
                       'Impuesto corriente a las ganancias',
                       'Deudores comerciales y otras cuentas por cobrar a largo plazo']:
            self.assertFalse(_es_anotacion(cuenta), f'No debió descartarse: {cuenta!r}')


class PaginaMuestreoMUM(TestCase):
    """Punto 4: la página MUM del cliente, integrada tal cual."""

    @classmethod
    def setUpTestData(cls):
        rol = Roles.objects.create(name='audit_manager', verbose_name='Jefe')
        cls.jefe = Usuario.objects.create_user(
            username='jefe_mum', email='jefe_mum@auditapro.test',
            password='Clave.Pruebas.2026', role=rol, plan='A')
        cls.auditoria = Audit.objects.create(
            title='Auditoría Financiera', identidad='ABC123', tipoAuditoria='F',
            moneda='GTQ', audit_manager=cls.jefe,
            fechaInit='2026-07-01', fechaEnd='2026-07-31')

    def setUp(self):
        self.cliente = Client()
        self.cliente.force_login(self.jefe)

    def test_pagina_mum_abre_y_conserva_el_contenido(self):
        respuesta = self.cliente.get(
            reverse('muestreo_mum', args=[self.auditoria.id]))
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode('utf-8')

        # El contenido del HTML del cliente se mantiene intacto
        for esperado in ['Monetario (MUM) — Unidad Monetaria',
                         'Memoria de cálculo',
                         'Descargar muestra en Excel',
                         'Factor de expansión por error esperado (FE)',
                         'downloadExcel', 'XLSX.writeFile']:
            self.assertIn(esperado, html, f'Falta del HTML original: {esperado}')

        # y el encabezado muestra la auditoría real, no el ejemplo
        self.assertIn('ABC123', html)
        self.assertNotIn('Empresa ABC S.A.', html)

    def test_enlace_desde_la_pagina_de_muestreo(self):
        respuesta = self.cliente.get(
            reverse('muestreo_page', args=[self.auditoria.id]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(reverse('muestreo_mum', args=[self.auditoria.id]),
                      respuesta.content.decode('utf-8'))
