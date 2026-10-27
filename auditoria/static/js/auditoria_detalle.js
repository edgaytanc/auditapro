const { audit_id, import_url } = window.AUDIT_CTX || { audit_id: null, import_url: null };

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
    document.getElementById("importUploadTitle").innerText = "Importar Estado Financiero";
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


function csrfToken() {
    const field = document.querySelector("[name=csrfmiddlewaretoken]");
    return field ? field.value : "";
}

/* Años: usa las rutas, validaciones y reglas que ya tiene el backend actualizado. */
async function auditJson(response) {
    let data;
    try {
        data = await response.json();
    } catch (_) {
        throw new Error(`El servidor respondió ${response.status}. Compruebe su sesión y los permisos de Papeles de Trabajo.`);
    }
    if (!response.ok || !data.success) {
        throw new Error(data.message || `No se pudo completar la operación (HTTP ${response.status}).`);
    }
    return data;
}

async function openAniosModal() {
    const modal = document.getElementById("aniosModal");
    const url = window.AUDIT_CTX && window.AUDIT_CTX.anios_url;
    if (!modal || !url) {
        alert("No está disponible la configuración de años de esta auditoría.");
        return;
    }
    modal.style.display = "block";
    modal.setAttribute("aria-hidden", "false");
    const mensaje = document.getElementById("aniosMensaje");
    mensaje.textContent = "Cargando años…";
    try {
        const response = await fetch(url, { credentials: "same-origin", headers: { "Accept": "application/json" } });
        const data = await auditJson(response);
        document.getElementById("anioActual").value = data.anio_actual ?? "";
        document.getElementById("anioAnterior").value = data.anio_anterior ?? "";
        mensaje.textContent = data.manuales
            ? "Años fijados manualmente por el auditor."
            : "Años obtenidos del Excel Financiero (si está importado).";
    } catch (error) {
        mensaje.textContent = error.message || "No se pudieron consultar los años.";
    }
}

function closeAniosModal() {
    const modal = document.getElementById("aniosModal");
    if (modal) {
        modal.style.display = "none";
        modal.setAttribute("aria-hidden", "true");
    }
}

async function guardarAnios(event) {
    event.preventDefault();
    const mensaje = document.getElementById("aniosMensaje");
    const url = window.AUDIT_CTX && window.AUDIT_CTX.anios_url;
    if (!url) {
        mensaje.textContent = "No está disponible la ruta de guardado.";
        return;
    }
    mensaje.textContent = "Guardando años…";
    try {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CSRFToken": csrfToken()
            },
            body: JSON.stringify({
                anio_actual: document.getElementById("anioActual").value,
                anio_anterior: document.getElementById("anioAnterior").value
            })
        });
        const data = await auditJson(response);
        mensaje.textContent = data.message || "Años guardados correctamente.";
        document.getElementById("anioActual").value = data.anio_actual ?? "";
        document.getElementById("anioAnterior").value = data.anio_anterior ?? "";
        setTimeout(closeAniosModal, 1200);
    } catch (error) {
        mensaje.textContent = error.message || "No se pudieron guardar los años.";
    }
}

// No sustituir window.onclick (lo usa la importación y la exportación).
const auditAniosBackdrop = document.getElementById("aniosModal");
if (auditAniosBackdrop) {
    auditAniosBackdrop.addEventListener("click", event => {
        if (event.target === auditAniosBackdrop) closeAniosModal();
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && auditAniosBackdrop.style.display === "block") closeAniosModal();
    });
}

/* ------------------------------------------------------------------
 * Referencia (Ref.) de cada papel de trabajo
 *
 * El sistema la calcula desde el índice maestro. Si el auditor escribe la
 * suya, el sistema la respeta y es la que se pega en la plantilla.
 * Dejar el campo vacío devuelve el papel a la referencia automática.
 * ------------------------------------------------------------------ */

async function editarReferencia(pastilla) {
    const url = window.AUDIT_CTX && window.AUDIT_CTX.referencia_url;
    if (!url) {
        alert("No está disponible la ruta para guardar referencias.");
        return;
    }

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

    try {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CSRFToken": csrfToken()
            },
            body: JSON.stringify({ carpeta, archivo, referencia: nueva })
        });
        const data = await auditJson(response);
        pastilla.dataset.ref = data.referencia || "";
        pastilla.dataset.manual = data.manual ? "1" : "0";
        pastilla.textContent = "Ref. " + (data.referencia || "");
        pastilla.classList.toggle("ref-pill-manual", !!data.manual);
        pastilla.title = data.manual
            ? "Referencia fijada por el auditor. Clic para editarla."
            : "Referencia automática. Clic para fijar una referencia propia.";
    } catch (error) {
        alert("No se pudo guardar la referencia: " + (error.message || "error inesperado"));
    }
}

// Las pastillas ya usan onclick desde el generador existente; permitir también teclado.
document.addEventListener("keydown", event => {
    const pill = event.target;
    if (pill && pill.classList && pill.classList.contains("ref-pill") &&
        (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        editarReferencia(pill);
    }
});
