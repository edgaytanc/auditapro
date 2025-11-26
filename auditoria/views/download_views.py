"""
Vistas para descarga de documentos de auditoría.
Contiene funciones para descargar documentos por carpeta/archivo y por patrón.
"""

import os
import urllib.parse
import logging
from .config import (
    get_object_or_404, HttpResponse, FileResponse, mark_safe,
    Audit, login_required, io,
    modify_document_word, modify_document_excel, modify_document_excel_with_macros,
    get_file_info_from_pattern
)
from .utils import get_template_path, crear_mensaje_error
from auditoria.services.audit_mark_processor import AuditMarkProcessor

logger = logging.getLogger(__name__)

@login_required
def download_document(request, audit_id, folder, filename):
    """Vista para descargar un documento específico"""
    # Decodificar la URL (por si tiene caracteres especiales)
    folder = urllib.parse.unquote(folder)
    filename = urllib.parse.unquote(filename)
    audit = get_object_or_404(Audit, id=audit_id)
    
    # Determinar si es auditoría interna
    is_internal = audit.tipoAuditoria == 'I'
    
    template_path = get_template_path(folder, filename, is_internal=is_internal)
    if not template_path or not os.path.exists(template_path):
        return HttpResponse(f'Plantilla no encontrada: {folder}/{filename}', status=404)
    try:
        buffer = io.BytesIO()
        if filename.lower().endswith('.docx'):
            # Aplicar reemplazos estándar
            doc = modify_document_word(template_path, audit)

            # Aplicar marcas de auditoría (NUEVO)
            try:
                processor = AuditMarkProcessor(audit_id, filename)
                doc = processor.process_word_document(doc)
            except Exception as e:
                logger.warning(f"No se pudieron agregar marcas de auditoría para {filename}: {e}")
                # Continuar con la descarga incluso si las marcas fallan

            doc.save(buffer)
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif filename.lower().endswith('.xlsx'):
            # Aplicar reemplazos estándar
            wb = modify_document_excel(template_path, audit)

            # Aplicar marcas de auditoría (NUEVO)
            try:
                processor = AuditMarkProcessor(audit_id, filename)
                wb = processor.process_excel_document(wb)
            except Exception as e:
                logger.warning(f"No se pudieron agregar marcas de auditoría para {filename}: {e}")
                # Continuar con la descarga incluso si las marcas fallan

            wb.save(buffer)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.lower().endswith('.xlsm'):
            # modify_document_excel_with_macros devuelve una ruta de archivo, no un objeto workbook
            processed_file_path = modify_document_excel_with_macros(template_path, audit)
            # Leer el contenido del archivo procesado en el buffer
            # NOTA: Los archivos XLSM NO obtienen marcas de auditoría (demasiado riesgoso para macros)
            logger.info(f"Archivo XLSM: {filename} - Omitiendo procesamiento de marcas de auditoría")
            with open(processed_file_path, 'rb') as f:
                buffer.write(f.read())
            buffer.seek(0)
            content_type = 'application/vnd.ms-excel.sheet.macroEnabled.12'
        else:
            # Tipo no procesado, se devuelve el archivo tal cual
            return FileResponse(
                open(template_path, 'rb'),
                as_attachment=True,
                filename=os.path.basename(template_path)
            )

        buffer.seek(0)
        response = FileResponse(buffer, as_attachment=True, filename=os.path.basename(template_path))
        response['Content-Type'] = content_type

        return response

    except Exception as e:
        return HttpResponse(f'Error al descargar documento: {str(e)}', status=500)

@login_required
def download_document_by_pattern(request, audit_id, pattern):
    """
    Vista para manejar hipervínculos generados en documentos Word.
    Recibe un ID de auditoría y un patrón (por ejemplo, 'A-1', 'R-10', etc.)
    y descarga el archivo correspondiente.
    
    Args:
        request: La solicitud HTTP
        audit_id: ID de la auditoría
        pattern: Patrón de nomenclatura (Ej: 'A-1', 'R-10')
        
    Returns:
        FileResponse: El archivo solicitado o un mensaje de error
    """
    try:
        # Verificar primero si la auditoría existe
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            mensaje_error = crear_mensaje_error(
                "Auditoría no encontrada",
                f"La auditoría con ID {audit_id} no existe en el sistema."
            )
            return HttpResponse(mark_safe(mensaje_error), status=404)
        
        # Verificar que el usuario tenga acceso a esta auditoría
        user_role = request.user.role.name
        has_access = False
        
        if user_role == "audit_manager" and audit.audit_manager == request.user:
            # Los administradores tienen acceso a las auditorías que crearon
            has_access = True
        elif user_role != "audit_manager" and audit.assigned_users.filter(id=request.user.id).exists():
            # Los auditores tienen acceso a las auditorías que les fueron asignadas
            has_access = True
        
        # Si no tiene acceso, mostrar mensaje de error
        if not has_access:
            mensaje_error = crear_mensaje_error(
                "Acceso restringido",
                "No tiene permisos para acceder a esta auditoría. Solo puede acceder a las auditorías que le han sido asignadas."
            )
            return HttpResponse(mark_safe(mensaje_error), status=403)
        
        # Determinar si es auditoría interna
        is_internal = audit.tipoAuditoria == 'I'
        
        # Obtener información del archivo a partir del patrón
        file_info = get_file_info_from_pattern(pattern, is_internal=is_internal)
        
        if not file_info:
            mensaje_error = crear_mensaje_error(
                "Archivo no encontrado",
                f"No se pudo encontrar el archivo correspondiente al patrón: <strong>{pattern}</strong><br>Por favor, verifique que el patrón sea correcto e intente nuevamente."
            )
            return HttpResponse(mark_safe(mensaje_error), status=404)
        
        # Extraer la información del archivo
        folder = file_info['folder']
        filename = file_info['filename']
        template_path = file_info['full_path']
        
        # Verificar que el archivo existe
        if not os.path.exists(template_path):
            mensaje_error = crear_mensaje_error(
                "Plantilla no encontrada",
                f"No se encontró la plantilla: {folder}/{filename}"
            )
            return HttpResponse(mark_safe(mensaje_error), status=404)
        
        # Procesar y devolver el documento
        try:
            buffer = io.BytesIO()
            if filename.lower().endswith('.docx'):
                # Aplicar reemplazos estándar
                doc = modify_document_word(template_path, audit)

                # Aplicar marcas de auditoría (NUEVO)
                try:
                    processor = AuditMarkProcessor(audit_id, filename)
                    doc = processor.process_word_document(doc)
                except Exception as e:
                    logger.warning(f"No se pudieron agregar marcas de auditoría para {filename}: {e}")
                    # Continuar con la descarga incluso si las marcas fallan

                doc.save(buffer)
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif filename.lower().endswith('.xlsx'):
                # Aplicar reemplazos estándar
                wb = modify_document_excel(template_path, audit)

                # Aplicar marcas de auditoría (NUEVO)
                try:
                    processor = AuditMarkProcessor(audit_id, filename)
                    wb = processor.process_excel_document(wb)
                except Exception as e:
                    logger.warning(f"No se pudieron agregar marcas de auditoría para {filename}: {e}")
                    # Continuar con la descarga incluso si las marcas fallan

                wb.save(buffer)
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                # Tipo no procesado, se devuelve el archivo tal cual
                return FileResponse(
                    open(template_path, 'rb'),
                    as_attachment=True,
                    filename=os.path.basename(template_path)
                )

            buffer.seek(0)
            response = FileResponse(buffer, as_attachment=True, filename=os.path.basename(template_path))
            response['Content-Type'] = content_type

            return response

        except Exception as e:
            mensaje_error = crear_mensaje_error(
                "Error al procesar documento",
                f"Ocurrió un error al procesar el documento {pattern}: {str(e)}"
            )
            return HttpResponse(mark_safe(mensaje_error), status=500)
        
    except Exception as e:
        mensaje_error = crear_mensaje_error(
            "Error en la solicitud",
            f"Ocurrió un error al procesar su solicitud: {str(e)}"
        )
        return HttpResponse(mark_safe(mensaje_error), status=500)
