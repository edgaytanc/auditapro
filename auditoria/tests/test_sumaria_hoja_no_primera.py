"""
Revisión del cliente: en los papeles de Revisoría la cédula sumaria NO es la
primera hoja del libro (p. ej. 'A-SUM' es la cuarta hoja de
'3.1 EFECTIVO_Y_EQUIVALENTES.xlsx'). Al importar un Estado Financiero, los
nombres de cuenta y los montos deben pegarse en esa hoja, esté donde esté.

Esas cédulas además rotulan la columna de cuenta 'Subcuenta' / 'Sub Cuenta' y
dejan en blanco los rótulos de fecha bajo la banda 'SALDOS S/ BALANCE GENERAL',
porque las fechas salen del Excel que se importe.
"""
import os

from django.conf import settings
from django.test import SimpleTestCase
from openpyxl import load_workbook

from auditoria.processors.excel.sumaria import process_sumaria_file
from auditoria.processors.excel.sumaria.layout import detectar_layout

EJECUCION = os.path.join(
    settings.BASE_DIR, 'static', 'templates_base_revisoria', '2 EJECUCION')

CORTES = ('2024-12-31', '2025-06-30', '2025-12-31')


def _plantilla(nombre):
    return load_workbook(os.path.join(EJECUCION, nombre))


def _balances(cuenta, seccion='Activo'):
    """Balances con los tres cortes semestrales de una cuenta."""
    return {
        f'SEMESTRAL-{fecha}-{seccion}-{cuenta}': 1000 * (indice + 1)
        for indice, fecha in enumerate(CORTES)
    }


def _fila_de(hoja, layout, texto):
    """Fila cuya columna de cuenta contiene *texto*, o None."""
    for fila in range(layout.fila_datos, (layout.fila_total or layout.fila_datos + 20)):
        valor = hoja.cell(row=fila, column=layout.col_cuenta).value
        if isinstance(valor, str) and texto.lower() in valor.lower():
            return fila
    return None


class LayoutEnHojaNoPrimera(SimpleTestCase):
    """La cuadrícula se localiza aunque la sumaria no sea la primera hoja."""

    def test_a_sum_es_la_cuarta_hoja_y_se_detecta(self):
        libro = _plantilla('3.1 EFECTIVO_Y_EQUIVALENTES.xlsx')
        self.assertGreater(libro.sheetnames.index('A-SUM'), 0,
                           'A-SUM debe ser una hoja posterior a la primera')

        detectadas = [h.title for h in libro.worksheets if detectar_layout(h)]
        self.assertIn('A-SUM', detectadas)

    def test_columna_subcuenta_y_banda_de_saldos(self):
        """'Subcuenta' vale como columna de cuenta; la banda marca los cortes."""
        hoja = _plantilla('3.1 EFECTIVO_Y_EQUIVALENTES.xlsx')['A-SUM']
        layout = detectar_layout(hoja)
        self.assertIsNotNone(layout)

        etiqueta = hoja.cell(row=layout.fila_encabezado,
                             column=layout.col_cuenta).value
        self.assertEqual(str(etiqueta).strip().lower(), 'subcuenta')
        self.assertEqual(len(layout.cols_saldo), 3)
        self.assertIsNotNone(layout.col_debe)
        self.assertIsNotNone(layout.col_haber)

    def test_la_fila_de_totales_no_se_toma_como_primera_fila_de_datos(self):
        """
        D-SUM viene sin filas de muestra: la búsqueda llegaba hasta 'Suma ' y
        la primera cuenta se habría escrito encima de los totales.
        """
        hoja = _plantilla('3.4 INVENTARIOS.xlsx')['D-SUM']
        layout = detectar_layout(hoja)
        self.assertIsNotNone(layout)
        self.assertLess(layout.fila_datos, layout.fila_total)


class EscrituraEnHojaNoPrimera(SimpleTestCase):
    """Las cuentas y los montos del Excel importado llegan a la hoja correcta."""

    def test_cuenta_y_montos_en_la_cuarta_hoja(self):
        libro = _plantilla('3.1 EFECTIVO_Y_EQUIVALENTES.xlsx')
        process_sumaria_file(libro, _balances('Caja y Bancos'), {},
                             '3.1 EFECTIVO_Y_EQUIVALENTES.xlsx')

        hoja = libro['A-SUM']
        layout = detectar_layout(hoja)
        fila = _fila_de(hoja, layout, 'Caja y Bancos')
        self.assertIsNotNone(fila, 'la cuenta no se escribió en A-SUM')

        importes = [hoja.cell(row=fila, column=col).value
                    for col in layout.cols_saldo]
        self.assertEqual(importes, [1000, 2000, 3000])

    def test_las_hojas_previas_quedan_intactas(self):
        """El índice y el programa no reciben los saldos de la sumaria."""
        libro = _plantilla('3.1 EFECTIVO_Y_EQUIVALENTES.xlsx')
        antes = {
            hoja.title: [c.value for fila in hoja.iter_rows() for c in fila]
            for hoja in libro.worksheets if hoja.title != 'A-SUM'
        }
        process_sumaria_file(libro, _balances('Caja y Bancos'), {},
                             '3.1 EFECTIVO_Y_EQUIVALENTES.xlsx')

        for titulo, valores in antes.items():
            actuales = [c.value for fila in libro[titulo].iter_rows() for c in fila]
            self.assertEqual(actuales, valores, f'se modificó la hoja {titulo}')

    def test_inventarios_se_escribe_sin_pisar_los_totales(self):
        libro = _plantilla('3.4 INVENTARIOS.xlsx')
        process_sumaria_file(libro, _balances('Inventarios'), {},
                             '3.4 INVENTARIOS.xlsx')

        hoja = libro['D-SUM']
        layout = detectar_layout(hoja)
        fila = _fila_de(hoja, layout, 'Inventarios')
        self.assertIsNotNone(fila, 'la cuenta no se escribió en D-SUM')
        self.assertLess(fila, layout.fila_total)
        self.assertIn('suma', str(hoja.cell(row=layout.fila_total,
                                            column=layout.col_cuenta).value).lower())

    def test_los_cortes_quedan_rotulados_con_su_fecha(self):
        libro = _plantilla('3.4 INVENTARIOS.xlsx')
        process_sumaria_file(libro, _balances('Inventarios'), {},
                             '3.4 INVENTARIOS.xlsx')

        hoja = libro['D-SUM']
        layout = detectar_layout(hoja)
        rotulos = [str(hoja.cell(row=layout.fila_rotulos_fecha, column=col).value)
                   for col in layout.cols_saldo]
        self.assertEqual(rotulos,
                         ['Al 31/12/2024', 'Al 30/06/2025', 'Al 31/12/2025'])
