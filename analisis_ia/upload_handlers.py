from django.core.files.uploadhandler import MemoryFileUploadHandler, StopUpload

MAX_BODY_BYTES = 6 * 1024 * 1024  # incluye campos multipart, máx. 2 archivos


class SoloMemoriaLimitada(MemoryFileUploadHandler):
    """Prohíbe crear TemporaryUploadedFile en disco para Audita Análisis."""

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        if content_length is not None and content_length > MAX_BODY_BYTES:
            raise StopUpload(connection_reset=True)
        # La clase base escribiría a disco si la solicitud > 2.5 MiB;
        # aquí mantenemos en RAM con un límite global validado en la vista.
        self.activated = True
        self._bytes_recibidos = 0

    def receive_data_chunk(self, raw_data, start):
        self._bytes_recibidos += len(raw_data)
        if self._bytes_recibidos > MAX_BODY_BYTES:
            raise StopUpload(connection_reset=True)
        return super().receive_data_chunk(raw_data, start)
