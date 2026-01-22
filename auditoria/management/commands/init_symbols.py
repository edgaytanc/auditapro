"""
Comando de gestión Django para inicializar la biblioteca de símbolos de auditoría.

Uso:
    python manage.py init_symbols
"""

from django.core.management.base import BaseCommand
from auditoria.services.symbol_library_service import SymbolLibraryService


class Command(BaseCommand):
    help = 'Inicializa la biblioteca de símbolos de auditoría con 35+ símbolos predeterminados'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('Iniciando inicialización de biblioteca de símbolos...')
        )

        try:
            result = SymbolLibraryService.initialize_default_symbols()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[OK] Inicializacion completada exitosamente:\n"
                    f"  - Simbolos creados: {result['created']}\n"
                    f"  - Simbolos actualizados: {result['updated']}\n"
                    f"  - Total en biblioteca: {result['total']}\n"
                )
            )

            # Mostrar conteo por categoría
            counts = SymbolLibraryService.get_category_counts()
            self.stdout.write(
                self.style.SUCCESS("\nSimbolos por categoria:")
            )
            for category, count in counts.items():
                self.stdout.write(f"  - {category}: {count} simbolos")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n[ERROR] Error durante la inicializacion: {e}")
            )
            raise
