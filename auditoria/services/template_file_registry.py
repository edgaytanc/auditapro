"""
Servicio de registro de archivos de plantilla para validación de work papers.

Este servicio escanea los directorios de plantillas y mantiene un registro
de todos los archivos disponibles para matching con marcas de auditoría.
"""

import os
import re
import logging
from pathlib import Path
from django.conf import settings
from django.core.cache import cache
from auditoria.config.exclusion_rules import is_excluded

logger = logging.getLogger(__name__)


class TemplateFile:
    """Representa un archivo de plantilla en el sistema"""

    def __init__(self, filename, folder, full_path, is_internal=False):
        self.filename = filename
        self.folder = folder
        self.full_path = full_path
        self.is_internal = is_internal

        # Extraer metadatos
        self.file_type = self._get_file_extension()
        self.normalized_name = self._normalize_name()
        self.display_name = self._get_display_name()
        self.exclusion_info = is_excluded(self.filename)
        self.is_excluded = self.exclusion_info['is_excluded']

    def _get_file_extension(self):
        """Obtiene la extensión del archivo sin el punto"""
        _, ext = os.path.splitext(self.filename)
        return ext[1:].lower() if ext else ''

    def _normalize_name(self):
        """
        Normaliza el nombre del archivo para matching.

        Proceso:
        1. Eliminar números iniciales (ej: "2 " de "2 SUMARIA...")
        2. Eliminar extensiones de archivo
        3. Convertir a mayúsculas y eliminar caracteres no alfanuméricos
        """
        text = self.filename

        # Paso 1: Eliminar números iniciales (incluyendo decimales) y espacios
        # Ejemplos: "2 " → "", "4.1 " → "", "10 " → ""
        text = re.sub(r'^\d+(\.\d+)?\s*', '', text)

        # Paso 2: Eliminar extensiones
        text = re.sub(r'\.(xlsx|docx|xls|doc|pdf)$', '', text, flags=re.IGNORECASE)

        # Paso 3: Normalización estándar
        text = text.upper()
        text = re.sub(r'[^A-Z0-9]', '', text)

        return text

    def _get_display_name(self):
        """
        Obtiene nombre de visualización amigable (sin números iniciales ni extensión)
        """
        text = self.filename

        # Eliminar números iniciales (incluyendo decimales)
        text = re.sub(r'^\d+(\.\d+)?\s*', '', text)

        # Eliminar extensión
        text = re.sub(r'\.(xlsx|docx|xls|doc|pdf)$', '', text, flags=re.IGNORECASE)

        return text.strip()

    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'filename': self.filename,
            'folder': self.folder,
            'full_path': self.full_path,
            'normalized_name': self.normalized_name,
            'display_name': self.display_name,
            'file_type': self.file_type,
            'is_internal': self.is_internal,
            'is_excluded': self.is_excluded,
            'exclusion_reason': self.exclusion_info.get('reason')
        }

    def __repr__(self):
        excluded_flag = " [EXCLUDED]" if self.is_excluded else ""
        return f"<TemplateFile: {self.display_name}{excluded_flag}>"


class TemplateFileRegistry:
    """
    Registro de archivos de plantilla para el sistema de auditoría.

    Escanea y mantiene un índice de todos los archivos de plantilla disponibles.
    """

    CACHE_KEY = 'template_file_registry_cache'
    CACHE_TIMEOUT = 3600  # 1 hora

    def __init__(self, use_cache=True):
        """
        Inicializa el registro.

        Args:
            use_cache (bool): Si True, intenta usar caché; si False, fuerza re-escaneo
        """
        self.use_cache = use_cache
        self.files = []
        self.normalized_mapping = {}  # {normalized_name: [TemplateFile, ...]}
        self._load_or_scan()

    def _load_or_scan(self):
        """Carga desde caché o escanea directorios"""
        if self.use_cache:
            cached_data = cache.get(self.CACHE_KEY)
            if cached_data:
                logger.info("Cargando registro de plantillas desde caché")
                self._load_from_cache(cached_data)
                return

        logger.info("Escaneando directorios de plantillas...")
        self._scan_template_directories()
        self._build_normalized_mapping()
        self._cache_registry()

    def _load_from_cache(self, cached_data):
        """Reconstruye el registro desde datos en caché"""
        self.files = []
        for file_dict in cached_data['files']:
            template_file = TemplateFile(
                filename=file_dict['filename'],
                folder=file_dict['folder'],
                full_path=file_dict['full_path'],
                is_internal=file_dict['is_internal']
            )
            self.files.append(template_file)

        self._build_normalized_mapping()

    def _cache_registry(self):
        """Guarda el registro en caché"""
        cached_data = {
            'files': [f.to_dict() for f in self.files]
        }
        cache.set(self.CACHE_KEY, cached_data, self.CACHE_TIMEOUT)
        logger.info(f"Registro de plantillas guardado en caché ({len(self.files)} archivos)")

    def _scan_template_directories(self):
        """Escanea los directorios de plantillas y registra todos los archivos"""
        self.files = []

        # Escanear templates financieras
        financial_base = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')
        self._scan_directory(financial_base, is_internal=False)

        # Escanear templates internas
        internal_base = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')
        self._scan_directory(internal_base, is_internal=True)

        logger.info(f"Escaneo completado: {len(self.files)} archivos encontrados")

    def _scan_directory(self, base_path, is_internal=False):
        """
        Escanea recursivamente un directorio en busca de archivos de plantilla.

        Args:
            base_path (str): Ruta base del directorio
            is_internal (bool): Si es directorio de auditoría interna
        """
        if not os.path.exists(base_path):
            logger.warning(f"Directorio no existe: {base_path}")
            return

        for root, dirs, files in os.walk(base_path):
            # Calcular carpeta relativa
            relative_folder = os.path.relpath(root, base_path)
            if relative_folder == '.':
                relative_folder = ''

            for filename in files:
                # Filtrar solo archivos relevantes
                if self._is_relevant_file(filename):
                    full_path = os.path.join(root, filename)
                    template_file = TemplateFile(
                        filename=filename,
                        folder=relative_folder,
                        full_path=full_path,
                        is_internal=is_internal
                    )
                    self.files.append(template_file)

    def _is_relevant_file(self, filename):
        """
        Verifica si un archivo es relevante para el registro.

        Args:
            filename (str): Nombre del archivo

        Returns:
            bool: True si es relevante
        """
        # Extensiones válidas
        valid_extensions = ['.xlsx', '.docx', '.xls', '.doc']
        _, ext = os.path.splitext(filename)

        if ext.lower() not in valid_extensions:
            return False

        # Excluir archivos temporales de Excel/Word
        if filename.startswith('~$'):
            return False

        # Excluir archivos ocultos
        if filename.startswith('.'):
            return False

        return True

    def _build_normalized_mapping(self):
        """Construye un mapeo de nombres normalizados a archivos"""
        self.normalized_mapping = {}

        for template_file in self.files:
            normalized = template_file.normalized_name

            if normalized not in self.normalized_mapping:
                self.normalized_mapping[normalized] = []

            self.normalized_mapping[normalized].append(template_file)

    def get_all_files(self):
        """
        Obtiene todos los archivos de plantilla.

        Returns:
            list: Lista de objetos TemplateFile
        """
        return self.files

    def get_work_paper_files(self, include_excluded=False):
        """
        Obtiene archivos elegibles para matching con work papers.

        Args:
            include_excluded (bool): Si True, incluye archivos excluidos

        Returns:
            list: Lista de objetos TemplateFile
        """
        if include_excluded:
            return self.files

        return [f for f in self.files if not f.is_excluded]

    def get_normalized_names(self, include_excluded=False):
        """
        Obtiene lista de nombres normalizados.

        Args:
            include_excluded (bool): Si True, incluye nombres de archivos excluidos

        Returns:
            list: Lista de nombres normalizados únicos
        """
        files = self.get_work_paper_files(include_excluded=include_excluded)
        return sorted(set(f.normalized_name for f in files))

    def get_display_names(self, include_excluded=False):
        """
        Obtiene lista de nombres de visualización.

        Args:
            include_excluded (bool): Si True, incluye nombres de archivos excluidos

        Returns:
            list: Lista de nombres de visualización únicos
        """
        files = self.get_work_paper_files(include_excluded=include_excluded)
        return sorted(set(f.display_name for f in files))

    def find_by_normalized_name(self, normalized_name):
        """
        Busca archivos por nombre normalizado.

        Args:
            normalized_name (str): Nombre normalizado

        Returns:
            list: Lista de objetos TemplateFile que coinciden
        """
        return self.normalized_mapping.get(normalized_name, [])

    def find_by_display_name(self, display_name):
        """
        Busca archivos por nombre de visualización.

        Args:
            display_name (str): Nombre de visualización

        Returns:
            list: Lista de objetos TemplateFile que coinciden
        """
        results = []
        for template_file in self.files:
            if template_file.display_name.upper() == display_name.upper():
                results.append(template_file)
        return results

    def refresh_cache(self):
        """Fuerza un re-escaneo y actualiza el caché"""
        logger.info("Refrescando caché de registro de plantillas...")
        cache.delete(self.CACHE_KEY)
        self._scan_template_directories()
        self._build_normalized_mapping()
        self._cache_registry()
        logger.info("Caché actualizado exitosamente")

    def get_statistics(self):
        """
        Obtiene estadísticas del registro.

        Returns:
            dict: Estadísticas
        """
        total = len(self.files)
        excluded = sum(1 for f in self.files if f.is_excluded)
        valid = total - excluded

        by_type = {}
        for f in self.files:
            file_type = f.file_type
            by_type[file_type] = by_type.get(file_type, 0) + 1

        return {
            'total_files': total,
            'valid_files': valid,
            'excluded_files': excluded,
            'by_type': by_type,
            'unique_normalized_names': len(self.normalized_mapping)
        }

    def __len__(self):
        return len(self.files)

    def __repr__(self):
        stats = self.get_statistics()
        return f"<TemplateFileRegistry: {stats['valid_files']} valid, {stats['excluded_files']} excluded>"
