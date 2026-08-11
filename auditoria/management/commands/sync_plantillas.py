"""
Sincroniza las plantillas base y sus JSON de estructura con un árbol oficial.

Uso:
    python manage.py sync_plantillas --financiera "<ruta>" --interna "<ruta>"

Reemplaza por completo `static/templates_base_<tipo>` con el contenido del
árbol indicado (descartando temporales de Office) y regenera
`auditoria/config/folder_structure_<tipo>.json` con el orden natural del
explorador, que es el que define los códigos de referencia jerárquicos.
"""

import json
import os
import re
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Temporales de Word/Excel y restos de guardado que nunca deben publicarse
PREFIJOS_EXCLUIDOS = ('~$', '.~')
EXTENSIONES_EXCLUIDAS = ('.tmp', '.bak', '.lnk')
PATRONES_EXCLUIDOS = (re.compile(r'^~WRL\d+\.tmp$', re.IGNORECASE),)

DESTINOS = {
    'financiera': ('templates_base_financiera', 'folder_structure_financiera.json'),
    'interna': ('templates_base_interna', 'folder_structure_interna.json'),
}


def es_archivo_excluido(nombre):
    """True si el archivo es un temporal de Office o un residuo de guardado."""
    if nombre.startswith(PREFIJOS_EXCLUIDOS):
        return True
    if nombre.lower().endswith(EXTENSIONES_EXCLUIDAS):
        return True
    return any(patron.match(nombre) for patron in PATRONES_EXCLUIDOS)


def clave_natural(nombre):
    """
    Orden natural del explorador: primero por el número que encabeza el nombre
    ('2 PLANEACION' antes que '10 ...'), luego alfabético sin distinguir
    mayúsculas. Los nombres sin número van al final de su nivel.
    """
    coincidencia = re.match(r'^\s*(\d+)', nombre)
    numero = int(coincidencia.group(1)) if coincidencia else 10 ** 6
    return (numero, nombre.lower())


def construir_estructura(raiz):
    """Devuelve el dict {carpeta: {...}, archivo: []} del árbol *raiz*."""
    estructura = {}
    entradas = sorted(os.listdir(raiz), key=clave_natural)
    for nombre in entradas:
        ruta = os.path.join(raiz, nombre)
        if os.path.isdir(ruta):
            estructura[nombre] = construir_estructura(ruta)
        elif not es_archivo_excluido(nombre):
            estructura[nombre] = []
    return estructura


def copiar_arbol(origen, destino):
    """Copia *origen* en *destino* omitiendo los temporales de Office."""
    def ignorar(_directorio, nombres):
        return [nombre for nombre in nombres if es_archivo_excluido(nombre)]

    if os.path.exists(destino):
        shutil.rmtree(destino)
    shutil.copytree(origen, destino, ignore=ignorar)


def contar_archivos(estructura):
    total = 0
    for contenido in estructura.values():
        total += contar_archivos(contenido) if isinstance(contenido, dict) else 1
    return total


class Command(BaseCommand):
    help = 'Reemplaza las plantillas base y regenera los JSON de estructura.'

    def add_arguments(self, parser):
        parser.add_argument('--financiera', help='Árbol oficial de Auditoría Financiera')
        parser.add_argument('--interna', help='Árbol oficial de Auditoría Interna')
        parser.add_argument(
            '--solo-json',
            action='store_true',
            help='Regenera los JSON desde las plantillas ya publicadas, sin copiar.',
        )

    def handle(self, *args, **opciones):
        rutas = {tipo: opciones.get(tipo) for tipo in DESTINOS}
        if not opciones['solo_json'] and not any(rutas.values()):
            raise CommandError('Indique --financiera y/o --interna (o use --solo-json).')

        for tipo, (carpeta_destino, nombre_json) in DESTINOS.items():
            origen = rutas.get(tipo)
            if not origen and not opciones['solo_json']:
                continue

            destino = os.path.join(settings.BASE_DIR, 'static', carpeta_destino)

            if origen:
                if not os.path.isdir(origen):
                    raise CommandError(f'No existe el árbol de {tipo}: {origen}')
                copiar_arbol(origen, destino)
                self.stdout.write(f'Plantillas de {tipo} reemplazadas desde: {origen}')

            if not os.path.isdir(destino):
                raise CommandError(f'No existe la carpeta publicada: {destino}')

            estructura = construir_estructura(destino)
            ruta_json = os.path.join(settings.BASE_DIR, 'auditoria', 'config', nombre_json)
            with open(ruta_json, 'w', encoding='utf-8') as archivo:
                json.dump(estructura, archivo, ensure_ascii=False, indent=2)

            self.stdout.write(self.style.SUCCESS(
                f'{tipo}: {contar_archivos(estructura)} plantillas -> {nombre_json}'
            ))

        # Los índices de referencias se cachean por tipo de auditoría
        from auditoria.services.referencias import limpiar_cache
        limpiar_cache()
