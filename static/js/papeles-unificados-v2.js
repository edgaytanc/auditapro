/* AuditaPro v2 — circuito único de papeles de trabajo.
   Usa exclusivamente endpoints existentes: lista/carga de marcas, carpetas,
   documentos, datos de auditor y descarga que YA integra marcas y reemplazos.
   No modifica los handlers antiguos ni la URL elegida (?tipo=F/I/R). */
(function () {
  'use strict';

  const flow = document.getElementById('apPaperFlow');
  const ctx = window.AUDIT_CTX || {};
  if (!flow) return;

  const $ = id => document.getElementById(id);
  const dialog = flow.querySelector('.ap-paper-flow__dialog');
  const step1 = $('apFlowStep1');
  const step2 = $('apFlowStep2');
  const status = $('apFlowMarksStatus');
  const markMessage = $('apFlowMarkMessage');
  const downloadMessage = $('apFlowDownloadMessage');
  const uploadButton = $('apFlowUpload');
  const skipButton = $('apFlowSkip');
  const downloadButton = $('apFlowDownload');
  const folder = $('apFlowFolder');
  const documentSelect = $('apFlowDocument');
  const datePrepared = $('apFlowDatePrepared');
  const dateApproved = $('apFlowDateApproved');
  let marksCount = null;
  let uploadFeedback = '';
  let loadedDocumentForm = false;
  let lastFocused = null;
  let busy = false;
  let previousOverflow = '';

  function showMessage(target, text, kind = '') {
    target.hidden = !text;
    target.classList.remove('is-error', 'is-success');
    if (kind) target.classList.add(`is-${kind}`);
    target.textContent = text || '';
  }

  function showStep(number) {
    const first = number === 1;
    step1.hidden = !first;
    step2.hidden = first;
    const tab1 = $('apFlowStep1Tab');
    const tab2 = $('apFlowStep2Tab');
    tab1.classList.toggle('is-current', first);
    tab2.classList.toggle('is-current', !first);
    if (first) {
      tab1.setAttribute('aria-current', 'step');
      tab2.removeAttribute('aria-current');
    } else {
      tab2.setAttribute('aria-current', 'step');
      tab1.removeAttribute('aria-current');
    }
  }

  function setBusy(value) {
    busy = value;
    [uploadButton, skipButton, downloadButton, $('apFlowBack')].forEach(button => {
      button.disabled = value;
    });
  }

  async function getJson(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', ...(options.headers || {}) },
      ...options,
    });
    let data;
    try {
      data = await response.json();
    } catch (_) {
      throw new Error(`Respuesta inesperada del servidor (HTTP ${response.status}). Verifica tu sesión y permisos.`);
    }
    if (!response.ok || data.success === false) {
      throw new Error(data.error || data.message || `No se pudo completar la solicitud (HTTP ${response.status}).`);
    }
    return data;
  }

  async function refreshMarks() {
    try {
      const data = await getJson(ctx.audit_marks_list_url);
      marksCount = typeof data.total_count === 'number'
        ? data.total_count
        : Array.isArray(data.marks) ? data.marks.length : 0;
      status.textContent = marksCount
        ? `${marksCount} marca(s) activa(s) registradas en esta auditoría. No necesitas volver a subirlas.`
        : 'Aún no hay marcas registradas. Puedes cargar la plantilla o continuar y descargar el documento sin marcas.';
      updateSummary();
    } catch (error) {
      marksCount = null;
      status.textContent = `No fue posible consultar las marcas: ${error.message}. Puedes continuar si tienes permiso para descargar documentos.`;
      updateSummary();
    }
  }

  function updateSummary() {
    const target = $('apFlowSummary');
    if (!target) return;
    const countLabel = marksCount === null
      ? 'No fue posible verificar cuántas marcas hay.'
      : marksCount === 0 ? 'No hay marcas activas cargadas.'
      : `${marksCount} marca(s) activas disponibles.`;
    const isMacroFile = documentSelect.value.toLowerCase().endsWith('.xlsm');
    const suffix = isMacroFile
      ? ' Atención: los archivos XLSM mantienen sus macros, pero la ruta actual no incorpora marcas a esos archivos.'
      : documentSelect.value
        ? ` El sistema intentará incorporar las marcas que coincidan con «${documentSelect.value}».`
        : ' Las marcas se incorporan únicamente cuando coinciden con el documento elegido.';
    target.textContent = countLabel + suffix + (uploadFeedback ? ` ${uploadFeedback}` : '');
  }

  function resetSelect(select, placeholder) {
    select.replaceChildren(new Option(placeholder, ''));
  }

  async function loadDocumentForm() {
    if (loadedDocumentForm) return;
    const [modalData, foldersData] = await Promise.all([
      getJson(ctx.doc_modal_url),
      getJson(ctx.doc_carpetas_url),
    ]);

    // El modal legado sigue siendo la fuente de nombres y permisos, evitando
    // calcular por segunda vez auditor, jefe y roles en el navegador.
    const parsed = new DOMParser().parseFromString(modalData.html || '', 'text/html');
    const legacyModal = parsed.getElementById('generarDocumentoModal');
    if (!legacyModal) throw new Error('El servidor no devolvió el formulario de datos Auditor/Jefe.');
    const textInputs = legacyModal.querySelectorAll('input.no-edit');
    $('apFlowAuditor').value = textInputs[0]?.value || '';
    $('apFlowSupervisor').value = textInputs[1]?.value || '';
    const isManager = legacyModal.dataset.userRole === 'audit_manager';
    datePrepared.readOnly = isManager;
    dateApproved.readOnly = !isManager;
    datePrepared.title = isManager ? 'Solo el auditor puede diligenciar esta fecha.' : '';
    dateApproved.title = !isManager ? 'Solo el jefe de auditoría puede diligenciar esta fecha.' : '';

    resetSelect(folder, 'Seleccione una carpeta');
    (foldersData.carpetas || []).forEach(name => folder.add(new Option(name, name)));
    loadedDocumentForm = true;
  }

  async function loadDocuments() {
    resetSelect(documentSelect, 'Seleccione un documento');
    documentSelect.disabled = true;
    updateSummary();
    if (!folder.value) return;
    showMessage(downloadMessage, 'Consultando documentos…');
    try {
      const url = ctx.doc_documentos_url.replace('PLACEHOLDER', encodeURIComponent(folder.value));
      const data = await getJson(url);
      (data.documentos || []).forEach(name => documentSelect.add(new Option(name, name)));
      documentSelect.disabled = false;
      showMessage(downloadMessage, data.documentos?.length ? '' : 'Esta carpeta no tiene documentos descargables.');
    } catch (error) {
      showMessage(downloadMessage, error.message, 'error');
    }
  }

  async function nextStep() {
    showMessage(markMessage, '');
    showStep(2);
    if (loadedDocumentForm) return;
    setBusy(true);
    showMessage(downloadMessage, 'Cargando carpetas y datos de la auditoría…');
    try {
      await loadDocumentForm();
      showMessage(downloadMessage, '');
    } catch (error) {
      showMessage(downloadMessage, error.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  function getCsrfToken() {
    return flow.querySelector('#apFlowMarksForm [name=csrfmiddlewaretoken]')?.value || '';
  }

  async function uploadMarks() {
    const file = $('apFlowExcel').files?.[0];
    if (!file) {
      showMessage(markMessage, 'Selecciona un archivo Excel antes de cargar marcas. Si ya hay marcas, utiliza «Continuar sin cargar».', 'error');
      return;
    }
    const extension = file.name.toLowerCase().split('.').pop();
    if (!['xlsx', 'xlsm'].includes(extension)) {
      showMessage(markMessage, 'El archivo debe ser XLSX o XLSM.', 'error');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showMessage(markMessage, 'El archivo supera los 5 MB admitidos por el asistente.', 'error');
      return;
    }
    const form = $('apFlowMarksForm');
    const data = new FormData(form);
    setBusy(true);
    showMessage(markMessage, 'Importando marcas de auditoría…');
    try {
      const result = await getJson(ctx.audit_marks_upload_url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), Accept: 'application/json' },
        body: data,
      });
      const imported = Number(result.marks_imported ?? 0);
      const invalid = Number(result.marks_skipped_invalid ?? 0);
      const warnings = Array.isArray(result.errors) ? result.errors : [];
      uploadFeedback = `Última carga: ${imported} importadas y ${invalid} inválidas.`;
      const warningText = warnings.length ? ` Avisos: ${warnings.slice(0, 3).join(' / ')}` : '';
      showMessage(markMessage,
        `Carga procesada: ${imported} marca(s) importadas; ${invalid} inválida(s).${warningText}`,
        imported === 0 || invalid > 0 || warnings.length ? 'error' : 'success');
      $('apFlowExcel').value = '';
      await refreshMarks();
      // Si hubo filas inválidas o avisos, permitir revisarlos antes de continuar.
      if (imported > 0 && invalid === 0 && warnings.length === 0) await nextStep();
    } catch (error) {
      showMessage(markMessage, error.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  function filenameFromHeader(value, fallback) {
    if (!value) return fallback;
    const extended = /filename\*=UTF-8''([^;]+)/i.exec(value);
    if (extended) { try { return decodeURIComponent(extended[1]); } catch (_) { /* fallback */ } }
    const basic = /filename\s*=\s*"?([^";]+)"?/i.exec(value);
    return basic ? basic[1] : fallback;
  }

  async function downloadDocument() {
    if (!folder.value || !documentSelect.value) {
      showMessage(downloadMessage, 'Selecciona una carpeta y un documento para generar el archivo.', 'error');
      return;
    }
    const url = new URL(ctx.doc_descarga_url, document.baseURI);
    [
      ['carpeta', folder.value],
      ['documento', documentSelect.value],
      ['fecha_elaboracion', datePrepared.value],
      ['fecha_aprobacion', dateApproved.value],
    ].forEach(([key, value]) => url.searchParams.set(key, value));

    setBusy(true);
    showMessage(downloadMessage, 'Generando el documento con las automatizaciones disponibles…');
    try {
      const response = await fetch(url.toString(), { credentials: 'same-origin' });
      if (!response.ok) {
        const contentType = response.headers.get('Content-Type') || '';
        if (contentType.includes('json')) {
          const data = await response.json();
          throw new Error(data.error || data.message || `Error ${response.status} al generar.`);
        }
        throw new Error(`El servidor no pudo generar el documento (HTTP ${response.status}).`);
      }
      const contentType = response.headers.get('Content-Type') || '';
      if (contentType.includes('text/html') || contentType.includes('application/json')) {
        throw new Error('El servidor devolvió una página o un mensaje en lugar del documento. Comprueba tu sesión y permisos.');
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = filenameFromHeader(response.headers.get('Content-Disposition'), documentSelect.value);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
      showMessage(downloadMessage,
        documentSelect.value.toLowerCase().endsWith('.xlsm')
          ? 'Archivo XLSM descargado preservando el procesamiento actual de macros. Esta ruta no incorpora marcas a XLSM.'
          : 'Documento generado. Los datos del auditor y las marcas coincidentes se procesaron mediante la ruta existente.',
        'success');
    } catch (error) {
      showMessage(downloadMessage, error.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  function open() {
    if (busy) return;
    lastFocused = document.activeElement;
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    flow.hidden = false;
    showStep(1);
    showMessage(markMessage, '');
    showMessage(downloadMessage, '');
    $('apFlowMarksForm').reset();
    uploadFeedback = '';
    updateSummary();
    dialog.focus();
    refreshMarks();
  }

  function close() {
    if (busy) return;
    flow.hidden = true;
    document.body.style.overflow = previousOverflow;
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
  }

  // Mantener el API anterior por compatibilidad: las dos funciones heredadas
  // siguen intactas. Solo cambia la entrada visible para el usuario.
  window.openAuditDocumentPipeline = open;
  flow.querySelectorAll('[data-flow-close]').forEach(button => button.addEventListener('click', close));
  $('apFlowUpload').addEventListener('click', uploadMarks);
  $('apFlowSkip').addEventListener('click', nextStep);
  $('apFlowBack').addEventListener('click', () => showStep(1));
  $('apFlowDownload').addEventListener('click', downloadDocument);
  $('apFlowStep1Tab').addEventListener('click', () => { if (!busy) showStep(1); });
  $('apFlowStep2Tab').addEventListener('click', () => { if (!busy) nextStep(); });
  folder.addEventListener('change', loadDocuments);
  documentSelect.addEventListener('change', updateSummary);
  flow.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    // Contener el foco dentro del diálogo también al navegar por teclado.
    if (event.key !== 'Tab') return;
    const focusables = [...flow.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled])')]
      .filter(el => !el.closest('[hidden]') && el.getClientRects().length);
    if (!focusables.length) return;
    if (event.shiftKey && document.activeElement === focusables[0]) {
      event.preventDefault(); focusables[focusables.length - 1].focus();
    } else if (!event.shiftKey && document.activeElement === focusables[focusables.length - 1]) {
      event.preventDefault(); focusables[0].focus();
    }
  });
})();
