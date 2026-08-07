const { audit_id, import_url, anios_url, referencia_url } =
    window.AUDIT_CTX || { audit_id: null, import_url: null, anios_url: null, referencia_url: null };

function csrfToken() {
    const campo = document.querySelector("[name=csrfmiddlewaretoken]");
    return campo ? campo.value : "";
}

function toggleFolder(folderId) {
    const element = document.getElementById(folderId);
    if (element) {
        const isVisible = element.style.display === "block";
        element.style.display = isVisible ? "none" : "block";
    }
}

function openImportModal() {
    document.getElementById("importModal").style.display = "block";
    document.getElementById("import-main-section").style.display = "block";
    document.getElementById("import-upload-section").style.display = "none";
}

function closeImportModal() {
    document.getElementById("importModal").style.display = "none";
    goBackToImportMain();
}

function goBackToImportMain() {
    document.getElementById("import-main-section").style.display = "block";
    document.getElementById("import-upload-section").style.display = "none";
}

function goToImportUpload(tipo) {
    document.getElementById("importUploadTitle").innerText = "Importar Excel Financiero";
    document.getElementById("import-main-section").style.display = "none";
    document.getElementById("import-upload-section").style.display = "block";
}

function handleExportCuentas() {
    document.getElementById("exportModal").style.display = "block";
}

function closeExportModal() {
    document.getElementById("exportModal").style.display = "none";
}

function exportFile(tipo) {
    if (!audit_id) return;
    const url = `/auditoria/detalle/${audit_id}/exportar/${tipo}/`;
    window.location.href = url;
    closeExportModal(); // Close modal after triggering export
}

function submitImportForm(event) {
    event.preventDefault();
    const form = document.getElementById("uploadForm");
    const formData = new FormData(form);

    fetch(import_url, {
        method: "POST",
        headers: {
            "X-CSRFToken": form.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("✅ " + data.message);
                closeImportModal();
                // Los años de los cuadros comparativos se toman del Excel:
                // se recarga para que el panel muestre los recién importados.
                window.location.reload();
            } else {
                alert("❌ Error: " + data.message);
            }
        })
        .catch(error => {
            alert("❌ Error inesperado al subir el archivo.");
        });
}

window.onclick = function (event) {
    const importModal = document.getElementById("importModal");
    const exportModal = document.getElementById("exportModal");

    if (event.target === importModal) {
        importModal.style.display = "none";
    }
    if (event.target === exportModal) {
        exportModal.style.display = "none";
    }
};

/* ------------------------------------------------------------------
 * Años de la auditoría (cuadros comparativos)
 *
 * Se llenan solos al importar el Excel Financiero y el auditor puede
 * corregirlos aquí; su valor manda sobre el del archivo.
 * ------------------------------------------------------------------ */

function openAniosModal() {
    const modal = document.getElementById("aniosModal");
    if (!modal || !anios_url) return;
    modal.style.display = "block";
    document.getElementById("aniosMensaje").textContent = "Cargando…";

    fetch(anios_url)
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            document.getElementById("anioActual").value = data.anio_actual || "";
            document.getElementById("anioAnterior").value = data.anio_anterior || "";
            document.getElementById("aniosMensaje").textContent = data.manuales
                ? "Años fijados manualmente por el auditor."
                : "Años tomados del Excel Financiero importado.";
        })
        .catch(() => {
            document.getElementById("aniosMensaje").textContent =
                "No se pudieron cargar los años.";
        });
}

function closeAniosModal() {
    const modal = document.getElementById("aniosModal");
    if (modal) modal.style.display = "none";
}

function guardarAnios(event) {
    event.preventDefault();
    const mensaje = document.getElementById("aniosMensaje");
    mensaje.textContent = "Guardando…";

    fetch(anios_url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({
            anio_actual: document.getElementById("anioActual").value,
            anio_anterior: document.getElementById("anioAnterior").value
        })
    })
        .then(r => r.json())
        .then(data => {
            mensaje.textContent = data.message || "";
            if (data.success) setTimeout(closeAniosModal, 1200);
        })
        .catch(() => { mensaje.textContent = "Error inesperado al guardar los años."; });
}

/* ------------------------------------------------------------------
 * Referencia (Ref.) de cada papel de trabajo
 *
 * El sistema la calcula desde el índice maestro. Si el auditor escribe la
 * suya, el sistema la respeta y es la que se pega en la plantilla.
 * Dejar el campo vacío devuelve el papel a la referencia automática.
 * ------------------------------------------------------------------ */

function editarReferencia(pastilla) {
    if (!referencia_url) return;

    const carpeta = pastilla.dataset.carpeta || "";
    const archivo = pastilla.dataset.archivo || "";
    const actual = pastilla.dataset.ref || "";

    const nueva = window.prompt(
        `Referencia para:\n${archivo}\n\n` +
        "Escriba la referencia que quiera usar (el sistema no la sobrescribirá).\n" +
        "Déjela vacía para volver a la referencia automática.",
        actual
    );
    if (nueva === null) return;

    fetch(referencia_url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ carpeta: carpeta, archivo: archivo, referencia: nueva })
    })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                alert("❌ " + (data.message || "No se pudo guardar la referencia."));
                return;
            }
            pastilla.dataset.ref = data.referencia || "";
            pastilla.dataset.manual = data.manual ? "1" : "0";
            pastilla.textContent = "Ref. " + (data.referencia || "");
            pastilla.classList.toggle("ref-pill-manual", !!data.manual);
            pastilla.title = data.manual
                ? "Referencia fijada por el auditor. Clic para editarla."
                : "Referencia automática. Clic para fijar una referencia propia.";
        })
        .catch(() => alert("❌ Error inesperado al guardar la referencia."));
}
