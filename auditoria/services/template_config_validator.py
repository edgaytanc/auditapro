"""
Validador de Configuración de Plantillas - Valida configuraciones antes de generar

⚠️ PROPÓSITO:
- Validar workbook_name contra archivos existentes
- Validar estructura de columnas (mínimo 2, nombres únicos)
- Validar selección de símbolos (mínimo 30)
- Proveer mensajes de error claros y sugerencias
- Prevenir generación de plantillas inválidas
"""

from auditoria.services.work_paper_validator import WorkPaperValidator
from auditoria.services.symbol_library_service import SymbolLibraryService
import logging

logger = logging.getLogger(__name__)


class ValidationError:
    """
    Representa un error de validación individual.
    """
    def __init__(self, field, message, severity='error'):
        self.field = field
        self.message = message
        self.severity = severity  # 'error', 'warning', 'info'

    def to_dict(self):
        return {
            'field': self.field,
            'message': self.message,
            'severity': self.severity
        }


class TemplateConfigValidator:
    """
    Validador de configuración de plantillas Excel.

    Valida todos los aspectos de una configuración antes de generar:
    - Workbook name (usando WorkPaperValidator)
    - Columnas (estructura, nombres, tipos)
    - Símbolos (cantidad mínima, validez)
    - Opciones (valores permitidos)
    """

    # Constantes de validación
    MIN_COLUMNS = 2
    MAX_COLUMNS = 20
    MIN_SYMBOLS = 30
    MAX_COLUMN_NAME_LENGTH = 100
    MAX_WORKBOOK_NAME_LENGTH = 200

    VALID_DATA_TYPES = ['text', 'number', 'date', 'currency', 'percentage']

    def __init__(self, audit_id):
        """
        Inicializar validador para una auditoría específica.

        Args:
            audit_id: ID de la auditoría
        """
        self.audit_id = audit_id
        self.errors = []
        self.warnings = []

    def validate_full_configuration(self, configuration):
        """
        Valida una configuración completa de plantilla.

        Args:
            configuration: dict con estructura completa de configuración

        Returns:
            dict: {
                'is_valid': bool,
                'errors': List[dict],
                'warnings': List[dict],
                'summary': dict
            }
        """
        self.errors = []
        self.warnings = []

        logger.info(f"Iniciando validación completa para audit_id={self.audit_id}")

        # Validar cada sección
        self._validate_workbook_name(configuration.get('workbook_name'))
        self._validate_columns(configuration.get('columns', []))
        self._validate_symbols(configuration.get('symbols', []))
        self._validate_options(configuration.get('options', {}))

        # Generar resumen
        summary = {
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'workbook_name': configuration.get('workbook_name'),
            'column_count': len(configuration.get('columns', [])),
            'symbol_count': len(configuration.get('symbols', [])),
        }

        is_valid = len(self.errors) == 0

        result = {
            'is_valid': is_valid,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'summary': summary
        }

        logger.info(
            f"Validación completa: valid={is_valid}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)}"
        )

        return result

    def _validate_workbook_name(self, workbook_name):
        """
        Valida el nombre del workbook usando WorkPaperValidator.

        Args:
            workbook_name: Nombre del libro de trabajo a validar
        """
        if not workbook_name:
            self.errors.append(ValidationError(
                'workbook_name',
                'El nombre del libro de trabajo es obligatorio'
            ))
            return

        # Validar longitud
        if len(workbook_name) > self.MAX_WORKBOOK_NAME_LENGTH:
            self.errors.append(ValidationError(
                'workbook_name',
                f'El nombre no puede exceder {self.MAX_WORKBOOK_NAME_LENGTH} caracteres'
            ))
            return

        # Validar contra archivos existentes usando WorkPaperValidator
        try:
            validator = WorkPaperValidator(self.audit_id)
            result = validator.validate_work_paper_name(workbook_name)

            if result.is_excluded:
                self.errors.append(ValidationError(
                    'workbook_name',
                    f'Nombre excluido: {result.exclusion_reason}'
                ))
            elif not result.is_valid:
                # No es válido, pero proporcionar advertencia en lugar de error
                # El usuario puede querer crear un nuevo workbook
                message = f'No se encontró archivo coincidente: {workbook_name}'

                if result.suggestions:
                    message += f' Sugerencias: {", ".join(result.suggestions[:3])}'

                self.warnings.append(ValidationError(
                    'workbook_name',
                    message,
                    severity='warning'
                ))
            else:
                # Válido - archivo existe
                logger.debug(f"Workbook name válido: {workbook_name}")

        except Exception as e:
            logger.error(f"Error al validar workbook name: {e}")
            self.errors.append(ValidationError(
                'workbook_name',
                f'Error durante la validación: {str(e)}'
            ))

    def _validate_columns(self, columns):
        """
        Valida la configuración de columnas.

        Args:
            columns: Lista de configuraciones de columna
        """
        if not columns:
            self.errors.append(ValidationError(
                'columns',
                'Se requiere al menos una columna'
            ))
            return

        # Validar cantidad
        if len(columns) < self.MIN_COLUMNS:
            self.errors.append(ValidationError(
                'columns',
                f'Se requieren al menos {self.MIN_COLUMNS} columnas'
            ))

        if len(columns) > self.MAX_COLUMNS:
            self.errors.append(ValidationError(
                'columns',
                f'No se pueden crear más de {self.MAX_COLUMNS} columnas'
            ))

        # Validar nombres únicos
        column_names = []
        for idx, col in enumerate(columns):
            col_name = col.get('name', '').strip()

            if not col_name:
                self.errors.append(ValidationError(
                    f'columns[{idx}].name',
                    f'La columna {idx + 1} requiere un nombre'
                ))
                continue

            if len(col_name) > self.MAX_COLUMN_NAME_LENGTH:
                self.errors.append(ValidationError(
                    f'columns[{idx}].name',
                    f'El nombre de la columna {idx + 1} excede {self.MAX_COLUMN_NAME_LENGTH} caracteres'
                ))

            if col_name.upper() in [cn.upper() for cn in column_names]:
                self.errors.append(ValidationError(
                    f'columns[{idx}].name',
                    f'Nombre de columna duplicado: "{col_name}"'
                ))
            else:
                column_names.append(col_name)

            # Validar tipo de dato
            data_type = col.get('data_type', 'text')
            if data_type not in self.VALID_DATA_TYPES:
                self.errors.append(ValidationError(
                    f'columns[{idx}].data_type',
                    f'Tipo de dato inválido: "{data_type}". Permitidos: {", ".join(self.VALID_DATA_TYPES)}'
                ))

            # Validar ancho
            width = col.get('width', 15)
            if not isinstance(width, (int, float)) or width < 5 or width > 100:
                self.errors.append(ValidationError(
                    f'columns[{idx}].width',
                    f'Ancho de columna debe estar entre 5 y 100 (actual: {width})'
                ))

        logger.debug(f"Validadas {len(columns)} columnas")

    def _validate_symbols(self, symbols):
        """
        Valida la selección de símbolos.

        Args:
            symbols: Lista de símbolos seleccionados
        """
        if not symbols:
            self.errors.append(ValidationError(
                'symbols',
                'Se requiere al menos un símbolo'
            ))
            return

        # Validar cantidad mínima
        if len(symbols) < self.MIN_SYMBOLS:
            self.errors.append(ValidationError(
                'symbols',
                f'Se requieren al menos {self.MIN_SYMBOLS} símbolos (seleccionados: {len(symbols)})'
            ))

        # Validar estructura de cada símbolo
        seen_symbols = set()
        for idx, symbol_data in enumerate(symbols):
            if not isinstance(symbol_data, dict):
                self.errors.append(ValidationError(
                    f'symbols[{idx}]',
                    'Cada símbolo debe ser un objeto con symbol, description, category'
                ))
                continue

            symbol = symbol_data.get('symbol', '').strip()
            if not symbol:
                self.errors.append(ValidationError(
                    f'symbols[{idx}].symbol',
                    f'El símbolo {idx + 1} requiere un carácter'
                ))
                continue

            # Validar duplicados
            if symbol in seen_symbols:
                self.errors.append(ValidationError(
                    f'symbols[{idx}].symbol',
                    f'Símbolo duplicado: "{symbol}"'
                ))
            else:
                seen_symbols.add(symbol)

            # Validar descripción
            description = symbol_data.get('description', '').strip()
            if not description:
                self.warnings.append(ValidationError(
                    f'symbols[{idx}].description',
                    f'El símbolo "{symbol}" no tiene descripción',
                    severity='warning'
                ))

        logger.debug(f"Validados {len(symbols)} símbolos")

    def _validate_options(self, options):
        """
        Valida las opciones de generación.

        Args:
            options: dict de opciones booleanas
        """
        if not isinstance(options, dict):
            # Opciones son opcionales, usar defaults
            return

        valid_options = [
            'include_headers',
            'include_instructions',
            'color_code_symbols',
            'add_data_validation'
        ]

        for key, value in options.items():
            if key not in valid_options:
                self.warnings.append(ValidationError(
                    f'options.{key}',
                    f'Opción desconocida: "{key}"',
                    severity='warning'
                ))

            if not isinstance(value, bool):
                self.errors.append(ValidationError(
                    f'options.{key}',
                    f'La opción "{key}" debe ser booleana (true/false)'
                ))

        logger.debug(f"Validadas {len(options)} opciones")

    def validate_workbook_name_only(self, workbook_name):
        """
        Valida solo el nombre del workbook (para validación en tiempo real).

        Args:
            workbook_name: Nombre a validar

        Returns:
            dict: {
                'is_valid': bool,
                'message': str,
                'suggestions': List[str],
                'is_excluded': bool
            }
        """
        if not workbook_name or not workbook_name.strip():
            return {
                'is_valid': False,
                'message': 'El nombre del libro de trabajo no puede estar vacío',
                'suggestions': [],
                'is_excluded': False
            }

        try:
            validator = WorkPaperValidator(self.audit_id)
            result = validator.validate_work_paper_name(workbook_name)

            if result.is_excluded:
                return {
                    'is_valid': False,
                    'message': f'Nombre excluido: {result.exclusion_reason}',
                    'suggestions': [],
                    'is_excluded': True
                }

            if result.is_valid:
                matched_files = [f.filename for f in result.matched_files[:3]]
                return {
                    'is_valid': True,
                    'message': f'Nombre válido. Coincide con: {", ".join(matched_files)}',
                    'suggestions': [],
                    'is_excluded': False
                }
            else:
                return {
                    'is_valid': False,
                    'message': 'No se encontró archivo coincidente',
                    'suggestions': result.suggestions[:5],
                    'is_excluded': False
                }

        except Exception as e:
            logger.error(f"Error al validar workbook name: {e}")
            return {
                'is_valid': False,
                'message': f'Error durante la validación: {str(e)}',
                'suggestions': [],
                'is_excluded': False
            }
