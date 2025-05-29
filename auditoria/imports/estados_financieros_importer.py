import openpyxl
from datetime import datetime
from django.db import transaction
from audits.models import Audit
from auditoria.models import BalanceCuentas, RegistroAuxiliar, SaldoInicial
import traceback
import io

class EstadosFinancierosImporter:
    """
    Importador unificado para archivos de estados financieros que contiene
    tanto balances anuales como semestrales en diferentes hojas.
    
    El archivo debe tener:
    - Una hoja "ESTADOS FINANCIEROS ANUAL" con balances anuales (2 fechas)
    - Una hoja "ESTADOS FINANCIEROS SEMESTRALES" con balances semestrales (4 fechas)
    - Opcionalmente, hojas para registros auxiliares y saldos iniciales
    """
    def __init__(self, file_obj, audit_id):
        """
        Inicializa el importador con un archivo en memoria y un ID de auditoría
        
        Args:
            file_obj: Un objeto InMemoryUploadedFile o similar que puede ser leído directamente
            audit_id: ID de la auditoría asociada
        """
        self.file_obj = file_obj
        self.audit_id = audit_id

    def validate_file(self):
        """Valida que el archivo contenga al menos una de las hojas requeridas"""
        try:
            # Leemos directamente desde el objeto de archivo
            file_content = io.BytesIO(self.file_obj.read())
            # Importante: restaurar el puntero para lecturas futuras
            self.file_obj.seek(0)
            
            wb = openpyxl.load_workbook(file_content, read_only=True, data_only=True)
            sheet_names_lower = [name.lower() for name in wb.sheetnames]
            
            # Verificar si existe al menos una de las hojas principales
            if not any('anual' in name or 'semestral' in name for name in sheet_names_lower):
                return False
                
            return True
        except Exception as e:
            return False

    @transaction.atomic
    def process_file(self):
        """Procesa todas las hojas relevantes del archivo"""
        try:
            # Leemos directamente desde el objeto de archivo
            file_content = io.BytesIO(self.file_obj.read())
            # Importante: restaurar el puntero para futuras operaciones
            self.file_obj.seek(0)
            
            wb = openpyxl.load_workbook(file_content, data_only=True)
            
            # Convertir nombres de hojas a minúsculas para comparación
            sheet_names_lower = {name.lower(): name for name in wb.sheetnames}
            
            # Procesamiento de hojas de estados financieros
            anual_processed = False
            semestral_processed = False
            
            # Procesar la hoja de estados financieros anuales si existe
            anual_sheet_name = next((sheet_names_lower[name] for name in sheet_names_lower 
                                    if 'anual' in name and 'semestral' not in name), None)
            if anual_sheet_name:
                self.process_annual_sheet(wb[anual_sheet_name])
                anual_processed = True
            
            # Procesar la hoja de estados financieros semestrales si existe
            semestral_sheet_name = next((sheet_names_lower[name] for name in sheet_names_lower 
                                        if 'semestral' in name), None)
            if semestral_sheet_name:
                self.process_semestral_sheet(wb[semestral_sheet_name])
                semestral_processed = True
            
            # Procesar la hoja de registros auxiliares si existe
            aux_sheet_name = next((sheet_names_lower[name] for name in sheet_names_lower 
                                  if 'auxiliar' in name), None)
            if aux_sheet_name:
                self.process_auxiliary_records(wb[aux_sheet_name])
            
            # Procesar la hoja de saldos iniciales si existe
            initial_sheet_name = next((sheet_names_lower[name] for name in sheet_names_lower 
                                      if 'saldo' in name), None)
            if initial_sheet_name:
                self.process_initial_balances(wb[initial_sheet_name])
            
            # Verificar que se haya procesado al menos una hoja principal
            if not (anual_processed or semestral_processed):
                return False, "❌ No se encontró ninguna hoja válida de estados financieros"
            
            return True, "✅ Importación completada exitosamente"
        except Exception as e:
            error_msg = f"Error procesando archivo: {str(e)}"
            traceback.print_exc()
            return False, error_msg

    def process_annual_sheet(self, sheet):
        """Procesa la hoja de estados financieros anuales (2 columnas de valores)"""
        try:
            current_section = None
            formatted_records = []
            
            audit_instance = Audit.objects.get(pk=self.audit_id)

            SECCIONES_VALIDAS = ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]
            ENCABEZADOS_A_OMITIR = [
                "CUENTA", 
                "Fecha corte año anterior", 
                "Fecha corte año actual"
            ]
            PALABRAS_TOTAL = ["TOTAL ACTIVO", "TOTAL PASIVO", "TOTAL PATRIMONIO", "TOTAL PASIVO Y PATRIMONIO"]

            # Variables para almacenar las fechas globales
            fechas_globales_anterior = None
            fechas_globales_actual = None

            for idx, row in enumerate(sheet.iter_rows(min_row=2, max_col=5, values_only=True), start=2):
                primera_columna = str(row[0]).strip() if row[0] is not None else ""

                # Saltar fila si está completamente vacía
                if all(cell is None for cell in row):
                    continue

                # Omitir filas de encabezado
                if primera_columna in ENCABEZADOS_A_OMITIR:
                    continue

                # Omitir filas de totales
                if any(total in primera_columna for total in PALABRAS_TOTAL):
                    continue

                # Actualizar la sección actual
                if primera_columna in SECCIONES_VALIDAS and (row[1] is None or isinstance(row[1], str)):
                    current_section = primera_columna
                    
                    # Solo extraer fechas si es la sección Activo
                    if current_section == "Activo":
                        if isinstance(row[1], str) and row[1].strip().lower().startswith("al "):
                            raw_date_anterior = row[1].replace("Al ", "").strip()
                            try:
                                fechas_globales_anterior = datetime.strptime(raw_date_anterior, "%d/%m/%Y").date()
                            except Exception as e:
                                pass
                        if isinstance(row[2], str) and row[2].strip().lower().startswith("al "):
                            raw_date_actual = row[2].replace("Al ", "").strip()
                            try:
                                fechas_globales_actual = datetime.strptime(raw_date_actual, "%d/%m/%Y").date()
                            except Exception as e:
                                pass
                    continue

                # Si no se ha definido la sección, se omite la fila
                if current_section is None:
                    continue

                # Verificar datos válidos
                if len(row) < 3:
                    continue

                # Verificar que los valores sean numéricos
                try:
                    valor_anterior = float(row[1]) if row[1] is not None else None
                    valor_actual = float(row[2]) if row[2] is not None else None
                    if valor_anterior is None and valor_actual is None:
                        continue
                except (ValueError, TypeError):
                    continue

                # Si llegamos aquí y tenemos valores numéricos, es una cuenta válida
                nombre_cuenta = primera_columna

                # Usar las fechas globales extraídas de la sección Activo
                if not (fechas_globales_anterior and fechas_globales_actual):
                    continue

                tipo_balance = "ANUAL"
                
                # Crear registros usando las fechas globales
                if valor_anterior is not None:
                    record_anterior = BalanceCuentas.objects.create(
                        audit=audit_instance,
                        tipo_balance=tipo_balance,
                        fecha_corte=fechas_globales_anterior,
                        seccion=current_section,
                        nombre_cuenta=nombre_cuenta,
                        valor=valor_anterior
                    )
                    formatted_records.append({
                        "audit": audit_instance.id,
                        "tipo_balance": tipo_balance,
                        "fecha_corte": fechas_globales_anterior,
                        "seccion": current_section,
                        "nombre_cuenta": nombre_cuenta,
                        "valor": valor_anterior
                    })

                if valor_actual is not None:
                    record_actual = BalanceCuentas.objects.create(
                        audit=audit_instance,
                        tipo_balance=tipo_balance,
                        fecha_corte=fechas_globales_actual,
                        seccion=current_section,
                        nombre_cuenta=nombre_cuenta,
                        valor=valor_actual
                    )
                    formatted_records.append({
                        "audit": audit_instance.id,
                        "tipo_balance": tipo_balance,
                        "fecha_corte": fechas_globales_actual,
                        "seccion": current_section,
                        "nombre_cuenta": nombre_cuenta,
                        "valor": valor_actual
                    })

            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def process_semestral_sheet(self, sheet):
        """Procesa la hoja de estados financieros semestrales (4 columnas de valores)"""
        try:
            current_section = None
            fechas_globales = []
            formatted_records = []
            
            audit_instance = Audit.objects.get(pk=self.audit_id)

            for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                # Tomar solo las primeras 5 columnas
                row5 = row[:5]
                primera_columna = str(row5[0]).strip() if row5[0] is not None else ""

                # Si la primera celda es uno de los rótulos de encabezado o totales, saltamos
                if primera_columna in [
                    "CUENTA", "Fecha corte año anterior", "Fecha corte año actual",
                    "TOTAL ACTIVO", "TOTAL PASIVO", "TOTAL PATRIMONIO"
                ]:
                    continue

                # Verificar si es una fila de sección y no tiene valores numéricos
                es_valor_numerico = any(isinstance(x, (int, float)) for x in row5[1:])
                if primera_columna in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"] and not es_valor_numerico:
                    current_section = primera_columna
                    
                    # Solo extraer fechas si es la sección Activo
                    if current_section == "Activo":
                        fechas_globales = []  # Reiniciamos la lista
                        for i, cell in enumerate(row5[1:5]):
                            if isinstance(cell, str) and cell.strip().lower().startswith("al "):
                                raw = cell.replace("Al ", "").strip()
                                try:
                                    d = datetime.strptime(raw, "%d/%m/%Y").date()
                                    fechas_globales.append(d)
                                except Exception as e:
                                    fechas_globales.append(None)
                            else:
                                fechas_globales.append(None)
                    continue

                # Si no se ha definido la sección, saltar
                if current_section is None:
                    continue

                # Verificar que los valores sean numéricos
                valores = []
                for valor in row5[1:5]:
                    try:
                        val = float(valor) if valor is not None else None
                        valores.append(val)
                    except (ValueError, TypeError):
                        valores.append(None)

                # Si no hay valores numéricos, saltamos
                if all(v is None for v in valores):
                    continue

                nombre_cuenta = primera_columna

                # Verificar que tengamos las fechas globales
                if not fechas_globales or all(f is None for f in fechas_globales):
                    continue

                tipo_balance = "SEMESTRAL"
                
                # Iteramos sobre cada valor y su fecha correspondiente
                for i, (valor, fecha) in enumerate(zip(valores, fechas_globales)):
                    if valor is not None and fecha is not None:
                        # Crear el registro en la BD
                        record = BalanceCuentas.objects.create(
                            audit=audit_instance,
                            tipo_balance=tipo_balance,
                            fecha_corte=fecha,
                            seccion=current_section,
                            nombre_cuenta=nombre_cuenta,
                            valor=valor
                        )
                        rec_summary = {
                            "audit": audit_instance.id,
                            "tipo_balance": tipo_balance,
                            "fecha_corte": fecha,
                            "seccion": current_section,
                            "nombre_cuenta": nombre_cuenta,
                            "valor": valor
                        }
                        formatted_records.append(rec_summary)

            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def process_auxiliary_records(self, sheet):
        """Procesa la hoja de registros auxiliares"""
        records_created = 0
        
        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not any(cell for cell in row):  # Skip empty rows
                continue
                
            cuenta = str(row[1]).strip() if row[1] else None
            saldo = row[2] if isinstance(row[2], (int, float)) else None
            
            # Ignorar filas que son totales
            if cuenta and cuenta.upper().startswith('TOTAL'):
                continue
            
            # Procesar cuenta normal
            if cuenta and saldo is not None:
                try:
                    RegistroAuxiliar.objects.create(
                        audit_id=self.audit_id,
                        cuenta=cuenta,
                        saldo=saldo
                    )
                    records_created += 1
                except Exception as e:
                    pass
            else:
                pass
        
        return records_created > 0

    def process_initial_balances(self, sheet):
        """Procesa la hoja de saldos iniciales"""
        records_created = 0
        
        # Obtener fecha para usar en los saldos iniciales
        fecha_corte = datetime.now().date()
        # Intentar obtener la fecha del balance más reciente si está disponible
        try:
            balances = BalanceCuentas.objects.filter(audit_id=self.audit_id).order_by('-fecha_corte')
            if balances.exists():
                fecha_corte = balances.first().fecha_corte
        except Exception as e:
            pass
        
        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not any(cell for cell in row):  # Skip empty rows
                continue
                
            cuenta = str(row[1]).strip() if row[1] else None
            saldo = row[2] if isinstance(row[2], (int, float)) else None
            
            # Ignorar filas que son totales
            if cuenta and cuenta.upper().startswith('TOTAL'):
                continue
            
            # Procesar cuenta normal
            if cuenta and saldo is not None:
                try:
                    SaldoInicial.objects.create(
                        audit_id=self.audit_id,
                        cuenta=cuenta,
                        saldo=saldo,
                        fecha_corte=fecha_corte  # Añadimos el campo fecha_corte
                    )
                    records_created += 1
                except Exception as e:
                    pass
            else:
                pass
        
        return records_created > 0