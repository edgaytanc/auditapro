"""
Configuración y logging para las vistas de auditoría.
Contiene imports comunes y configuración de logging.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings
from audits.models import Audit
from django.contrib.auth.decorators import login_required

import os
import io
import urllib.parse
import json
import logging

from ..word_utils import modify_document_word
from ..excel_utils import modify_document_excel, modify_document_excel_with_macros
from ..processors.shared import get_file_info_from_pattern

# Configurar logging
log_path = os.path.join(settings.BASE_DIR, 'logs')
if not os.path.exists(log_path):
    os.makedirs(log_path)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_path, 'auditoria.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
