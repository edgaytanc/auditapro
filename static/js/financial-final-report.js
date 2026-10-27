(function () {
  "use strict";

  const opinionTemplates = {
    limpia: {
      label: "Opinión no modificada",
      className: "",
      text:
        "En nuestra opinión, los estados financieros adjuntos presentan " +
        "razonablemente, en todos los aspectos materiales, la situación " +
        "financiera de la entidad al 31 de diciembre " +
        "del período auditado, así como su desempeño financiero y sus flujos de efectivo " +
        "correspondientes al período terminado en esa fecha, de conformidad " +
        "con el marco de información financiera aplicable."
    },

    salvedades: {
      label: "Opinión con salvedades",
      className: "salvedades",
      text:
        "En nuestra opinión, excepto por los posibles efectos de los asuntos " +
        "descritos en la sección Fundamento de la opinión con salvedades, " +
        "los estados financieros adjuntos presentan razonablemente, en todos " +
        "los aspectos materiales, la situación financiera de la entidad al " +
        "cierre del período auditado."
    },

    adversa: {
      label: "Opinión adversa",
      className: "adversa",
      text:
        "En nuestra opinión, debido a la importancia y generalización de los " +
        "asuntos descritos en la sección Fundamento de la opinión adversa, " +
        "los estados financieros adjuntos no presentan razonablemente la " +
        "situación financiera de la entidad al cierre del período auditado."
    },

    abstencion: {
      label: "Abstención de opinión",
      className: "abstencion",
      text:
        "No expresamos una opinión sobre los estados financieros adjuntos. " +
        "Debido a la importancia de los asuntos descritos en la sección " +
        "Fundamento de la abstención de opinión, no pudimos obtener evidencia " +
        "de auditoría suficiente y adecuada para proporcionar una base para " +
        "una opinión de auditoría."
    }
  };

  document.addEventListener("financial-company-saved", function(event) {
    const name = event.detail?.company_name || "";
    const entityField = document.getElementById("reportEntityInput");
    const preview = document.querySelector(".financial-report-company");
    if (entityField) entityField.value = name;
    if (preview) preview.textContent = name;
  });

  const entityInput = document.getElementById("reportEntityInput");
  const yearInput = document.getElementById("reportYearInput");
  const applyIdentity = document.getElementById("applyReportIdentity");
  applyIdentity?.addEventListener("click", function () {
    const name = (entityInput.value || "").trim();
    const year = Number(yearInput.value);
    if (!name || !Number.isInteger(year) || year < 2000 || year > 2200) {
      window.alert("Indica una empresa y un año válido."); return;
    }
    const company = document.querySelector(".financial-report-company");
    const period = document.querySelector(".financial-report-period");
    if (company) company.textContent = name;
    if (period) period.textContent = "Estados financieros al 31 de diciembre de " + year;
    showStatus("Encabezado actualizado; puedes seguir editando el documento.", false);
  });
  document.getElementById("reportAddFindingRow")?.addEventListener("click", function () {
    const section = document.querySelector('[data-report-section="hallazgos"]');
    const tbody = section?.querySelector("tbody");
    if (!tbody) { showStatus("No se encontró la tabla de hallazgos.",true); return; }
    const row = document.createElement("tr");
    for (let idx=0; idx < (tbody.closest("table")?.querySelectorAll("thead th").length || 4); idx++) {
      const cell=document.createElement("td"); cell.contentEditable="true"; cell.textContent=""; row.appendChild(cell);
    }
    tbody.appendChild(row);
    row.firstElementChild?.focus();
  });

  const opinionSelect = document.getElementById(
    "financialReportOpinionSelect"
  );

  const opinionBadge = document.getElementById(
    "financialReportOpinionBadge"
  );

  const opinionText = document.getElementById(
    "financialReportOpinionText"
  );

  const preparedByInput = document.getElementById(
    "financialReportPreparedBy"
  );

  const reviewedByInput = document.getElementById(
    "financialReportReviewedBy"
  );

  const reportDateInput = document.getElementById(
    "financialReportDate"
  );

  function updateOpinion() {
    if (!opinionSelect || !opinionText) {
      return;
    }

    const template =
      opinionTemplates[opinionSelect.value] ||
      opinionTemplates.limpia;

    opinionText.textContent = template.text;

    showStatus(
      "Se actualizó el texto sugerido de la opinión. Puedes editarlo manualmente.",
      false
    );
  }

  function updateSectionVisibility(checkbox) {
    const sectionName = checkbox.dataset.reportToggle;

    const section = document.querySelector(
      `[data-report-section="${sectionName}"]`
    );

    if (!section) {
      return;
    }

    section.classList.toggle(
      "is-disabled",
      !checkbox.checked
    );
  }

  function formatDate(dateValue) {
    if (!dateValue) {
      return "";
    }

    const parts = dateValue.split("-");

    if (parts.length !== 3) {
      return dateValue;
    }

    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  function updateSignatures() {
    const preparedPreview = document.getElementById(
      "financialReportPreparedByPreview"
    );

    const reviewedPreview = document.getElementById(
      "financialReportReviewedByPreview"
    );

    const datePreview = document.getElementById(
      "financialReportDatePreview"
    );

    if (preparedPreview && preparedByInput) {
      preparedPreview.textContent =
        preparedByInput.value || "Sin asignar";
    }

    if (reviewedPreview && reviewedByInput) {
      reviewedPreview.textContent =
        reviewedByInput.value || "Sin asignar";
    }

    if (datePreview && reportDateInput) {
      datePreview.textContent =
        formatDate(reportDateInput.value) ||
        "Sin fecha";
    }
  }

  function prepareReportClone() {
    const report = document.getElementById(
      "financialReportPrintArea"
    );

    if (!report) {
      return null;
    }

    const clone = report.cloneNode(true);

    clone.removeAttribute("id");
    clone.querySelector("#reportAddFindingRow")?.remove();

    clone.querySelectorAll(".is-disabled").forEach(
      function (section) {
        section.remove();
      }
    );

    clone.querySelectorAll("[contenteditable]").forEach(
      function (element) {
        element.removeAttribute("contenteditable");
        element.removeAttribute("spellcheck");
      }
    );

    return clone;
  }

  function exportToWord() {
    const clone = prepareReportClone();

    if (!clone) {
      showStatus(
        "No fue posible encontrar el contenido del informe.",
        true
      );

      return;
    }

    const wordDocument = `
      <!DOCTYPE html>
      <html
        xmlns:o="urn:schemas-microsoft-com:office:office"
        xmlns:w="urn:schemas-microsoft-com:office:word"
        xmlns="http://www.w3.org/TR/REC-html40"
      >
        <head>
          <meta charset="UTF-8">

          <title>
            Informe Final de Auditoría Financiera
          </title>

          <style>
            @page {
              size: A4;
              margin: 2cm;
            }

            body {
              color: #202738;
              font-family: Georgia, "Times New Roman", serif;
              font-size: 11pt;
              line-height: 1.65;
            }

            .financial-report-document {
              width: 100%;
            }

            .financial-report-document-header {
              padding-bottom: 24px;
              border-bottom: 1px solid #cccccc;
              text-align: center;
            }

            .financial-report-brand {
              margin-bottom: 18px;
              color: #0d9488;
              font-family: Arial, sans-serif;
              font-size: 9pt;
              font-weight: bold;
            }

            h1 {
              font-size: 22pt;
            }

            h2 {
              margin-top: 26px;
              font-size: 14pt;
            }

            .financial-report-company {
              color: #566078;
              font-size: 12pt;
            }

            .financial-report-period {
              color: #7a8299;
              font-family: Arial, sans-serif;
              font-size: 9pt;
            }

            .financial-report-section {
              padding: 18px 0;
              border-bottom: 1px solid #e4e4e4;
            }

            .financial-report-opinion-badge {
              display: inline-block;
              margin-bottom: 12px;
              padding: 4px 8px;
              background: #e1f7ec;
              color: #168451;
              font-family: Arial, sans-serif;
              font-size: 8pt;
              font-weight: bold;
            }

            .financial-report-highlight-grid {
              width: 100%;
              margin-bottom: 16px;
            }

            .financial-report-highlight {
              display: inline-block;
              width: 29%;
              margin-right: 1%;
              padding: 8px;
              border: 1px solid #dddddd;
              vertical-align: top;
            }

            .financial-report-highlight span {
              display: block;
              color: #777777;
              font-family: Arial, sans-serif;
              font-size: 7pt;
              text-transform: uppercase;
            }

            table {
              width: 100%;
              border-collapse: collapse;
              font-family: Arial, sans-serif;
              font-size: 8pt;
            }

            th {
              padding: 6px;
              border: 1px solid #cccccc;
              background: #e9eef4;
              text-align: left;
            }

            td {
              padding: 6px;
              border: 1px solid #cccccc;
              vertical-align: top;
            }

            .financial-report-signatures {
              width: 100%;
              margin-top: 55px;
            }

            .financial-report-signature {
              display: inline-block;
              width: 30%;
              margin-right: 2%;
              padding-top: 8px;
              border-top: 1px solid #555555;
              text-align: center;
              vertical-align: top;
            }

            .financial-report-signature span {
              display: block;
              color: #777777;
              font-family: Arial, sans-serif;
              font-size: 7pt;
              text-transform: uppercase;
            }
          </style>
        </head>

        <body>
          ${clone.outerHTML}
        </body>
      </html>
    `;

    const blob = new Blob(
      ["\ufeff", wordDocument],
      {
        type:
          "application/msword;charset=utf-8;"
      }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download =
      "informe-final-auditoria-financiera-af-2026-004.doc";

    document.body.appendChild(link);

    link.click();
    link.remove();

    window.setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);

    showStatus(
      "El informe fue descargado en formato Word.",
      false
    );
  }

  function exportToPdf() {
    const activeSections = document.querySelectorAll(
      ".financial-report-section:not(.is-disabled)"
    );

    if (!activeSections.length) {
      showStatus(
        "Debes activar al menos una sección antes de exportar.",
        true
      );

      return;
    }

    document.body.classList.add(
      "financial-report-printing"
    );

    showStatus(
      "Selecciona Guardar como PDF en la ventana de impresión.",
      false
    );

    window.setTimeout(function () {
      window.print();
    }, 150);
  }

  function removePrintMode() {
    document.body.classList.remove(
      "financial-report-printing"
    );
  }

  function showStatus(message, isError) {
    const status = document.getElementById(
      "financialReportStatus"
    );

    if (!status) {
      return;
    }

    status.textContent = message;
    status.classList.add("visible");

    status.style.borderColor = isError
      ? "#fecaca"
      : "#bae6fd";

    status.style.background = isError
      ? "#fef2f2"
      : "#f0f9ff";

    status.style.color = isError
      ? "#991b1b"
      : "#075985";

    window.setTimeout(function () {
      status.classList.remove("visible");
    }, 5000);
  }

  document
    .querySelectorAll("[data-report-toggle]")
    .forEach(function (checkbox) {
      checkbox.addEventListener(
        "change",
        function () {
          updateSectionVisibility(checkbox);
        }
      );

      updateSectionVisibility(checkbox);
    });

  if (opinionSelect) {
    opinionSelect.addEventListener(
      "change",
      updateOpinion
    );
  }

  if (preparedByInput) {
    preparedByInput.addEventListener(
      "input",
      updateSignatures
    );
  }

  if (reviewedByInput) {
    reviewedByInput.addEventListener(
      "input",
      updateSignatures
    );
  }

  if (reportDateInput) {
    reportDateInput.addEventListener(
      "change",
      updateSignatures
    );
  }

window.exportFinancialReportWord = function () {
  exportToWord();
};

window.exportFinancialReportPdf = function () {
  exportToPdf();
};

  window.addEventListener(
    "afterprint",
    removePrintMode
  );

  updateSignatures();
})();