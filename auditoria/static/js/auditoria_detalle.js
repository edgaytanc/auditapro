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

function exportFile(tipo) {
    if (!audit_id) return;
    const url = `/auditoria/detalle/${audit_id}/exportar/${tipo}/`;
    window.location.href = url;
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
            console.error("Error:", error);
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
