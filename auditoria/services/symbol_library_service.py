"""
Servicio de Biblioteca de Símbolos - Gestiona la biblioteca de símbolos de auditoría

⚠️ FUNCIONALIDAD PRINCIPAL:
- Inicializar 30+ símbolos predeterminados del sistema
- Proveer símbolos por categoría para selección en UI
- Permitir creación de símbolos personalizados por auditoría
- Gestionar símbolos activos/inactivos
"""

from django.db import transaction
from auditoria.models import SymbolLibrary
import logging

logger = logging.getLogger(__name__)


class SymbolLibraryService:
    """
    Servicio para gestionar la biblioteca de símbolos de auditoría.

    Proporciona 30+ símbolos predeterminados del sistema organizados por categorías:
    - Verificación (10 símbolos)
    - Cálculo (8 símbolos)
    - Documentación (7 símbolos)
    - Revisión (5 símbolos)
    - Análisis (5 símbolos)

    Total: 35 símbolos del sistema
    """

    # Biblioteca de 35 símbolos predeterminados del sistema
    DEFAULT_SYMBOLS = [
        # Categoría: Verificación (10 símbolos)
        {
            'symbol': '✓',
            'description': 'Verificado: Documento o dato verificado contra fuente original',
            'category': 'verification',
            'display_order': 1
        },
        {
            'symbol': '√',
            'description': 'Chequeado: Dato o cálculo revisado y confirmado como correcto',
            'category': 'verification',
            'display_order': 2
        },
        {
            'symbol': '©',
            'description': 'Comprobado: Evidencia física o documental verificada',
            'category': 'verification',
            'display_order': 3
        },
        {
            'symbol': '⊗',
            'description': 'Cotejado: Comparado con documento de respaldo',
            'category': 'verification',
            'display_order': 4
        },
        {
            'symbol': '⊕',
            'description': 'Confirmado: Confirmación recibida de terceros',
            'category': 'verification',
            'display_order': 5
        },
        {
            'symbol': '◎',
            'description': 'Inspeccionado: Inspección física realizada',
            'category': 'verification',
            'display_order': 6
        },
        {
            'symbol': '☑',
            'description': 'Validado: Validado contra normas o políticas',
            'category': 'verification',
            'display_order': 7
        },
        {
            'symbol': '✔',
            'description': 'Aprobado: Cumple con criterios de aceptación',
            'category': 'verification',
            'display_order': 8
        },
        {
            'symbol': '⊙',
            'description': 'Observado: Procedimiento observado en ejecución',
            'category': 'verification',
            'display_order': 9
        },
        {
            'symbol': '◉',
            'description': 'Auditado: Procedimiento de auditoría completo aplicado',
            'category': 'verification',
            'display_order': 10
        },

        # Categoría: Cálculo (8 símbolos)
        {
            'symbol': '∑',
            'description': 'Suma: Total calculado y verificado',
            'category': 'calculation',
            'display_order': 11
        },
        {
            'symbol': '≈',
            'description': 'Aproximado: Cálculo aproximado o estimado',
            'category': 'calculation',
            'display_order': 12
        },
        {
            'symbol': '=',
            'description': 'Igual: Saldos cuadrados o balanceados',
            'category': 'calculation',
            'display_order': 13
        },
        {
            'symbol': '≠',
            'description': 'Diferencia: Discrepancia o diferencia identificada',
            'category': 'calculation',
            'display_order': 14
        },
        {
            'symbol': '÷',
            'description': 'División: Cálculo de ratios o porcentajes',
            'category': 'calculation',
            'display_order': 15
        },
        {
            'symbol': '×',
            'description': 'Multiplicación: Cálculo de productos o extensiones',
            'category': 'calculation',
            'display_order': 16
        },
        {
            'symbol': '%',
            'description': 'Porcentaje: Cálculo porcentual aplicado',
            'category': 'calculation',
            'display_order': 17
        },
        {
            'symbol': '±',
            'description': 'Más/Menos: Ajuste o reclasificación calculada',
            'category': 'calculation',
            'display_order': 18
        },

        # Categoría: Documentación (7 símbolos)
        {
            'symbol': '§',
            'description': 'Referencia: Referenciado a otro papel de trabajo',
            'category': 'documentation',
            'display_order': 19
        },
        {
            'symbol': '¶',
            'description': 'Nota: Nota explicativa o aclaración incluida',
            'category': 'documentation',
            'display_order': 20
        },
        {
            'symbol': '※',
            'description': 'Importante: Asunto que requiere atención especial',
            'category': 'documentation',
            'display_order': 21
        },
        {
            'symbol': '→',
            'description': 'Traspaso: Dato trasladado a otro documento',
            'category': 'documentation',
            'display_order': 22
        },
        {
            'symbol': '←',
            'description': 'Origen: Dato proveniente de otro documento',
            'category': 'documentation',
            'display_order': 23
        },
        {
            'symbol': '↔',
            'description': 'Conciliación: Partidas conciliadas entre documentos',
            'category': 'documentation',
            'display_order': 24
        },
        {
            'symbol': '⇒',
            'description': 'Consecuencia: Hallazgo o recomendación derivada',
            'category': 'documentation',
            'display_order': 25
        },

        # Categoría: Revisión (5 símbolos)
        {
            'symbol': '⚠',
            'description': 'Advertencia: Situación que requiere atención',
            'category': 'review',
            'display_order': 26
        },
        {
            'symbol': '⚡',
            'description': 'Hallazgo: Hallazgo de auditoría identificado',
            'category': 'review',
            'display_order': 27
        },
        {
            'symbol': '⚑',
            'description': 'Seguimiento: Asunto pendiente de seguimiento',
            'category': 'review',
            'display_order': 28
        },
        {
            'symbol': '⊘',
            'description': 'No Aplica: Procedimiento no aplicable',
            'category': 'review',
            'display_order': 29
        },
        {
            'symbol': '?',
            'description': 'Consulta: Asunto que requiere consulta o aclaración',
            'category': 'review',
            'display_order': 30
        },

        # Categoría: Análisis (5 símbolos)
        {
            'symbol': '▲',
            'description': 'Aumento: Incremento significativo identificado',
            'category': 'analysis',
            'display_order': 31
        },
        {
            'symbol': '▼',
            'description': 'Disminución: Reducción significativa identificada',
            'category': 'analysis',
            'display_order': 32
        },
        {
            'symbol': '◆',
            'description': 'Muestra: Elemento seleccionado como muestra',
            'category': 'analysis',
            'display_order': 33
        },
        {
            'symbol': '★',
            'description': 'Crítico: Elemento o transacción crítica',
            'category': 'analysis',
            'display_order': 34
        },
        {
            'symbol': '○',
            'description': 'Circularizado: Confirmación circular enviada',
            'category': 'analysis',
            'display_order': 35
        },
    ]

    @classmethod
    @transaction.atomic
    def initialize_default_symbols(cls):
        """
        Inicializa los símbolos predeterminados del sistema en la base de datos.

        ⚠️ IMPORTANTE:
        - Solo crea símbolos que no existan
        - Actualiza símbolos existentes si la descripción ha cambiado
        - Marca todos los símbolos como is_system=True
        - Solo debe ejecutarse una vez al desplegar el sistema

        Returns:
            dict: {
                'created': int,  # Símbolos nuevos creados
                'updated': int,  # Símbolos actualizados
                'total': int     # Total de símbolos en biblioteca
            }
        """
        created_count = 0
        updated_count = 0

        logger.info("Iniciando inicialización de biblioteca de símbolos...")

        for symbol_data in cls.DEFAULT_SYMBOLS:
            try:
                # Intentar obtener símbolo existente
                symbol, created = SymbolLibrary.objects.get_or_create(
                    symbol=symbol_data['symbol'],
                    is_system=True,
                    defaults={
                        'description': symbol_data['description'],
                        'category': symbol_data['category'],
                        'display_order': symbol_data['display_order'],
                        'is_active': True,
                        'audit': None  # Símbolos del sistema no tienen audit
                    }
                )

                if created:
                    created_count += 1
                    logger.debug(f"✓ Creado: {symbol.symbol} - {symbol.description[:50]}")
                else:
                    # Actualizar si la descripción ha cambiado
                    if (symbol.description != symbol_data['description'] or
                        symbol.category != symbol_data['category'] or
                        symbol.display_order != symbol_data['display_order']):

                        symbol.description = symbol_data['description']
                        symbol.category = symbol_data['category']
                        symbol.display_order = symbol_data['display_order']
                        symbol.save()

                        updated_count += 1
                        logger.debug(f"↻ Actualizado: {symbol.symbol}")

            except Exception as e:
                logger.error(f"Error al procesar símbolo {symbol_data['symbol']}: {e}")
                continue

        total_count = SymbolLibrary.objects.filter(is_system=True, is_active=True).count()

        logger.info(
            f"Inicialización completa: "
            f"{created_count} creados, {updated_count} actualizados, "
            f"{total_count} total en biblioteca"
        )

        return {
            'created': created_count,
            'updated': updated_count,
            'total': total_count
        }

    @classmethod
    def get_all_symbols(cls, include_inactive=False):
        """
        Obtiene todos los símbolos del sistema.

        Args:
            include_inactive: Si True, incluye símbolos inactivos

        Returns:
            QuerySet: Símbolos ordenados por categoría y display_order
        """
        queryset = SymbolLibrary.objects.filter(is_system=True)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset.order_by('category', 'display_order')

    @classmethod
    def get_symbols_by_category(cls, category=None, include_inactive=False):
        """
        Obtiene símbolos filtrados por categoría.

        Args:
            category: Categoría específica o None para todas
            include_inactive: Si True, incluye símbolos inactivos

        Returns:
            QuerySet o dict: Si category es None, devuelve dict con todas las categorías
        """
        queryset = SymbolLibrary.objects.filter(is_system=True)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        if category:
            return queryset.filter(category=category).order_by('display_order')
        else:
            # Devolver diccionario organizado por categoría
            symbols_by_category = {}
            categories = SymbolLibrary.CATEGORY_CHOICES

            for cat_value, cat_label in categories:
                if cat_value == 'custom':
                    continue  # Omitir categoría personalizada para símbolos del sistema

                symbols = queryset.filter(category=cat_value).order_by('display_order')
                if symbols.exists():
                    symbols_by_category[cat_value] = {
                        'label': cat_label,
                        'symbols': list(symbols)
                    }

            return symbols_by_category

    @classmethod
    def get_symbols_for_audit(cls, audit_id, include_custom=True):
        """
        Obtiene símbolos disponibles para una auditoría específica.

        Args:
            audit_id: ID de la auditoría
            include_custom: Si True, incluye símbolos personalizados de la auditoría

        Returns:
            QuerySet: Símbolos del sistema + símbolos personalizados de la auditoría
        """
        from django.db.models import Q

        # Símbolos del sistema activos
        query = Q(is_system=True, is_active=True)

        # Agregar símbolos personalizados de esta auditoría
        if include_custom:
            query |= Q(audit_id=audit_id, is_active=True)

        return SymbolLibrary.objects.filter(query).order_by(
            'category', 'display_order', 'symbol'
        )

    @classmethod
    @transaction.atomic
    def create_custom_symbol(cls, audit_id, symbol, description, category='custom'):
        """
        Crea un símbolo personalizado para una auditoría específica.

        Args:
            audit_id: ID de la auditoría
            symbol: Carácter del símbolo (máximo 10 caracteres)
            description: Descripción del símbolo
            category: Categoría (por defecto 'custom')

        Returns:
            SymbolLibrary: Símbolo creado

        Raises:
            ValueError: Si el símbolo ya existe para esta auditoría
        """
        from django.core.exceptions import ValidationError

        # Verificar si el símbolo ya existe para esta auditoría
        if SymbolLibrary.objects.filter(
            symbol=symbol,
            audit_id=audit_id
        ).exists():
            raise ValueError(
                f"El símbolo '{symbol}' ya existe para esta auditoría"
            )

        # Verificar si es un símbolo del sistema
        if SymbolLibrary.objects.filter(
            symbol=symbol,
            is_system=True
        ).exists():
            raise ValueError(
                f"El símbolo '{symbol}' es un símbolo del sistema y no puede ser duplicado"
            )

        # Obtener el siguiente display_order para esta categoría
        last_order = SymbolLibrary.objects.filter(
            audit_id=audit_id,
            category=category
        ).order_by('-display_order').first()

        next_order = (last_order.display_order + 1) if last_order else 1000

        # Crear símbolo personalizado
        custom_symbol = SymbolLibrary.objects.create(
            symbol=symbol,
            description=description,
            category=category,
            is_system=False,
            audit_id=audit_id,
            is_active=True,
            display_order=next_order
        )

        logger.info(
            f"Símbolo personalizado creado: {symbol} para audit_id={audit_id}"
        )

        return custom_symbol

    @classmethod
    def get_category_counts(cls):
        """
        Obtiene el conteo de símbolos por categoría.

        Returns:
            dict: {'category': count}
        """
        from django.db.models import Count

        counts = SymbolLibrary.objects.filter(
            is_system=True,
            is_active=True
        ).values('category').annotate(
            count=Count('id')
        ).order_by('category')

        return {item['category']: item['count'] for item in counts}

    @classmethod
    def search_symbols(cls, query_text, audit_id=None):
        """
        Busca símbolos por texto en símbolo o descripción.

        Args:
            query_text: Texto a buscar
            audit_id: Si se proporciona, incluye símbolos personalizados de la auditoría

        Returns:
            QuerySet: Símbolos que coinciden con la búsqueda
        """
        from django.db.models import Q

        # Búsqueda en símbolos del sistema
        search_query = Q(
            is_system=True,
            is_active=True
        ) & (
            Q(symbol__icontains=query_text) |
            Q(description__icontains=query_text)
        )

        # Agregar símbolos personalizados si audit_id se proporciona
        if audit_id:
            custom_search = Q(
                audit_id=audit_id,
                is_active=True
            ) & (
                Q(symbol__icontains=query_text) |
                Q(description__icontains=query_text)
            )
            search_query |= custom_search

        return SymbolLibrary.objects.filter(search_query).order_by(
            'category', 'display_order'
        )
