/* Modal AJAX para generar papeles sin tocar la navegación v2. */
(function () {
  const ctx = window.AUDIT_CTX || {};
  let modalHost = null;

  async function leer(url) {
    const response = await fetch(url, {credentials: 'same-origin'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'No fue posible cargar los datos.');
    return result;
  }

  window.abrirModalGenerarDocumento = async function () {
    if (!ctx.doc_modal_url || !window.bootstrap) {
      alert('No se puede cargar el modal de documentos.');
      return;
    }
    try {
      const data = await leer(ctx.doc_modal_url);
      if (modalHost) {
        const old = modalHost.querySelector('.modal');
        if (old) bootstrap.Modal.getInstance(old)?.dispose();
        modalHost.remove();
      }
      modalHost = document.createElement('div');
      modalHost.innerHTML = data.html;
      document.body.appendChild(modalHost);
      const modal = modalHost.querySelector('#generarDocumentoModal');
      const carpeta = modal.querySelector('select[name="carpeta"]');
      const documento = modal.querySelector('select[name="documento"]');
      const elaboracion = modal.querySelector('input[name="fecha_elaboracion"]');
      const aprobacion = modal.querySelector('input[name="fecha_aprobacion"]');
      const boton = modal.querySelector('#btnDescargar');
      const role = modal.dataset.userRole;
      if (role === 'audit_manager') elaboracion.readOnly = true;
      else aprobacion.readOnly = true;
      bootstrap.Modal.getOrCreateInstance(modal).show();

      const listado = await leer(ctx.doc_carpetas_url);
      carpeta.replaceChildren(new Option('Seleccione una carpeta', ''));
      (listado.carpetas || []).forEach(name => carpeta.add(new Option(name, name)));
      carpeta.addEventListener('change', async () => {
        documento.replaceChildren(new Option('Seleccione un documento', ''));
        if (!carpeta.value) return;
        const url = ctx.doc_documentos_url.replace('PLACEHOLDER', encodeURIComponent(carpeta.value));
        try {
          const datos = await leer(url);
          (datos.documentos || []).forEach(name => documento.add(new Option(name, name)));
        } catch (error) { alert(error.message); }
      });
      boton.addEventListener('click', () => {
        if (!carpeta.value || !documento.value) {
          alert('Seleccione una carpeta y un documento.');
          return;
        }
        const query = new URLSearchParams({
          carpeta: carpeta.value,
          documento: documento.value,
          fecha_elaboracion: elaboracion.value || '',
          fecha_aprobacion: aprobacion.value || ''
        });
        const downloadUrl = new URL(ctx.doc_descarga_url, window.location.origin);
        query.forEach((value, key) => downloadUrl.searchParams.set(key, value));
        window.location.href = downloadUrl.toString();
      });
    } catch (error) { alert(error.message); }
  };
})();
