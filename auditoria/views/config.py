"""
Configuración para las vistas de auditoría.
Contiene imports comunes para las vistas.
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

from ..word_utils import modify_document_word
from ..excel_utils import modify_document_excel, modify_document_excel_with_macros
from ..processors.shared import get_file_info_from_pattern
