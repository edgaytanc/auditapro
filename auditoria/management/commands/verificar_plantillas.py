"""
Verifica la coherencia entre las plantillas publicadas, los JSON de estructura
y los mapeos de referencias por área (A..J, R).

Uso:
    python manage.py verificar_plantillas

Comprueba, para Financiera e Interna:
  1. Que cada archivo del JSON de estructura exista en disco.
  2. Que cada archivo en disco esté declarado en el JSON.
  3. Que cada carpeta de PREFIX_TO_FOLDER exista.
  4. Que cada programa (PREFIX_TO_PROGRAM) y cada papel (PATTERN_TO_FILE)
     apunten a un archivo real.
  5. Que cada área tenga su cédula sumaria 'X-1' resuelta (es la que alimenta
     la columna Ref P/T de las centralizadoras).

Devuelve código de salida 1 si encuentra alguna incoherencia.
"""

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from auditoria.management.commands.sync_plantillas import es_archivo_excluido
from auditoria.processors.shared.urls_programs.financial_audit_mappings import (
    PREFIX_TO_FOLDER,
    PATTERN_TO_FILE,
)
from auditoria.processors.shared.urls_programs.special_patterns import PREFIX_TO_PROGRAM

TIPOS = {
    'F': ('Financiera', 'templates_base_financiera', 'folder_structure_financiera.json'),
    'I': ('Interna', 'templates_base_interna', 'folder_structure_interna.json'),
}


def archivos_de_json(estructura, prefijo=''):
    """Aplana el JSON de estructura a un set de rutas relativas con '/'."""
    rutas = set()
    for nombre, contenido in estructura.items():
        ruta = f'{prefijo}/{nombre}' if prefijo else nombre
        if isinstance(contenido, dict):
            rutas |= archivos_de_json(contenido, ruta)
        else:
            rutas.add(ruta)
    return rutas


def archivos_en_disco(raiz):
    rutas = set()
    for carpeta, _subcarpetas, archivos in os.walk(raiz):
        for archivo in archivos:
            if es_archivo_excluido(archivo):
                continue
            relativa = os.path.relpath(os.path.join(carpeta, archivo), raiz)
            rutas.add(relativa.replace(os.sep, '/'))
    return rutas


class Command(BaseCommand):
    help = 'Verifica plantillas, estructura JSON y mapeos de referencias.'

    def handle(self, *args, **opciones):
        errores = []

        for tipo, (etiqueta, carpeta, nombre_json) in TIPOS.items():
            raiz = os.path.join(settings.BASE_DIR, 'static', carpeta)
            ruta_json = os.path.join(settings.BASE_DIR, 'auditoria', 'config', nombre_json)

            with open(ruta_json, encoding='utf-8') as archivo:
                estructura = json.load(archivo)

            declarados = archivos_de_json(estructura)
            existentes = archivos_en_disco(raiz)

            for ruta in sorted(declarados - existentes):
                errores.append(f'[{etiqueta}] declarado en el JSON pero no existe: {ruta}')
            for ruta in sorted(existentes - declarados):
                errores.append(f'[{etiqueta}] existe en disco pero no está en el JSON: {ruta}')

            self.stdout.write(
                f'{etiqueta}: {len(existentes)} plantillas en disco, '
                f'{len(declarados)} declaradas en {nombre_json}'
            )

        # Mapeos de áreas sustantivas (solo aplican a Financiera)
        raiz_financiera = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')

        for prefijo, carpeta in PREFIX_TO_FOLDER.items():
            ruta_carpeta = os.path.join(raiz_financiera, *carpeta.split('/'))
            if not os.path.isdir(ruta_carpeta):
                errores.append(f'[Área {prefijo}] carpeta inexistente: {carpeta}')
                continue

            programa = PREFIX_TO_PROGRAM.get(prefijo)
            if programa and not os.path.isfile(os.path.join(ruta_carpeta, programa)):
                errores.append(f'[Área {prefijo}] programa inexistente: {carpeta}/{programa}')

        for patron, archivo in sorted(PATTERN_TO_FILE.items()):
            carpeta = PREFIX_TO_FOLDER.get(patron.split('-')[0])
            if not carpeta:
                errores.append(f'[{patron}] sin carpeta de área registrada')
                continue
            if not os.path.isfile(os.path.join(raiz_financiera, *carpeta.split('/'), archivo)):
                errores.append(f'[{patron}] archivo inexistente: {carpeta}/{archivo}')

        # Las 'X-1' son las sumarias que referencia la columna Ref P/T
        for prefijo in PREFIX_TO_FOLDER:
            if f'{prefijo}-1' not in PATTERN_TO_FILE:
                errores.append(f'[Área {prefijo}] falta la cédula sumaria {prefijo}-1')

        self.stdout.write(
            f'Areas sustantivas: {len(PREFIX_TO_FOLDER)} | '
            f'papeles mapeados: {len(PATTERN_TO_FILE)}'
        )

        if errores:
            self.stdout.write('')
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  [X] {error}'))
            self.stderr.write(f'\n{len(errores)} incoherencia(s) encontradas.')
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(
            '\n[OK] Plantillas, estructura y mapeos de referencias coherentes.'
        ))
