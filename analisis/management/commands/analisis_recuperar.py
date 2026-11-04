from django.core.management.base import BaseCommand

from analisis import jobs
from analisis.models import CorridaAnalisis


class Command(BaseCommand):
    help = "Marca con error las corridas de Audita Análisis que quedaron activas sin avance (p. ej. tras un reinicio)."

    def handle(self, *args, **options):
        marcadas = jobs.mark_stale()
        activas = CorridaAnalisis.objects.filter(estado__in=CorridaAnalisis.ACTIVAS).count()
        self.stdout.write(f"Corridas interrumpidas marcadas: {marcadas}. Activas ahora: {activas}.")
