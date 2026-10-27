document.addEventListener("DOMContentLoaded", function () {

  const newAuditModal = document.getElementById(
    "newAuditModal"
  );

  const newAuditForm = document.getElementById(
    "newAuditForm"
  );

  const newAuditSubmitButton = document.getElementById(
    "newAuditSubmitButton"
  );

  const openNewAuditButtons = document.querySelectorAll(
    "[data-open-new-audit]"
  );

  const closeNewAuditButtons = document.querySelectorAll(
    "[data-close-new-audit]"
  );

  const auditTypeOptions = Array.from(
    document.querySelectorAll(
      "[data-new-audit-type]"
    )
  );

  const auditTeamOptions = Array.from(
    document.querySelectorAll(
      "[data-new-audit-team-member]"
    )
  );

  const auditTypeError = document.getElementById(
    "newAuditTypeError"
  );

  const auditTeamError = document.getElementById(
    "newAuditTeamError"
  );

  const startDateInput = document.getElementById(
    "newAuditStartDate"
  );

  const endDateInput = document.getElementById(
    "newAuditEndDate"
  );

  const periodInput = document.getElementById(
    "newAuditPeriod"
  );

  const dateError = document.getElementById(
    "newAuditDateError"
  );

  const searchInput = document.getElementById(
    "auditSearch"
  );

  const typeFilter = document.getElementById(
    "auditTypeFilter"
  );

  const statusFilter = document.getElementById(
    "auditStatusFilter"
  );

  const resultsCount = document.getElementById(
    "auditResultsCount"
  );

  const noResults = document.getElementById(
    "auditsNoResults"
  );

  const exportButton = document.getElementById(
    "exportAuditsButton"
  );

  const rows = Array.from(
    document.querySelectorAll("[data-audit-row]")
  );

function cleanCellText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeCsvCell(value) {
  const normalizedValue = cleanCellText(
    value
  );

  return (
    '"' +
    normalizedValue.replace(
      /"/g,
      '""'
    ) +
    '"'
  );
}


function getSelectedOptionText(selectElement) {
  if (
    !selectElement ||
    !selectElement.selectedOptions ||
    !selectElement.selectedOptions.length
  ) {
    return "";
  }

  return cleanCellText(
    selectElement.selectedOptions[0].textContent
  );
}


function getVisibleAuditRows() {
  return rows.filter(function (row) {
    return !row.hidden;
  });
}


function getAuditRowExportData(row) {
  const teamMembers = Array.from(
    row.querySelectorAll(
      ".ap-audit-team-avatar"
    )
  )
    .map(function (member) {
      return cleanCellText(
        member.getAttribute("title")
      );
    })
    .filter(Boolean);

  const types = Array.from(
    row.querySelectorAll(
      ".ap-audit-type"
    )
  )
    .map(function (typeElement) {
      return cleanCellText(
        typeElement.textContent
      );
    })
    .filter(Boolean);

  return [
    cleanCellText(
      row.querySelector(
        ".ap-audit-code"
      )?.textContent
    ),

    cleanCellText(
      row.querySelector(
        ".ap-audit-client strong"
      )?.textContent
    ),

    cleanCellText(
      row.querySelector(
        ".ap-audit-client span"
      )?.textContent
    ),

    types.join(" / "),

    cleanCellText(
      row.querySelector(
        ".ap-audit-period"
      )?.textContent
    ),

    cleanCellText(
      row.querySelector(
        ".ap-audit-manager"
      )?.textContent
    ),

    teamMembers.length
      ? teamMembers.join(", ")
      : "Sin equipo",

    getSelectedOptionText(
      row.querySelector(
        "[data-audit-progress]"
      )
    ),

    getSelectedOptionText(
      row.querySelector(
        "[data-audit-risk]"
      )
    ),

    getSelectedOptionText(
      row.querySelector(
        "[data-audit-status], " +
      "[data-audit-findings]"
      )
    ),

    cleanCellText(
      row.querySelector(
        ".ap-audit-findings"
      )?.textContent
    ),
  ];
}


async function exportVisibleAudits() {
  const visibleRows = getVisibleAuditRows();
  if (!visibleRows.length) { window.alert("No hay auditorías visibles para exportar."); return; }
  const endpoint = exportButton?.dataset.exportUrl;
  const ids = visibleRows.map(row => Number(row.dataset.auditId)).filter(Boolean);
  try {
    if (!endpoint) throw new Error("No se configuró la ruta de Excel.");
    const response = await fetch(endpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type":"application/json", "X-CSRFToken": getCookie("csrftoken") || ""},
      body: JSON.stringify({ids})
    });
    if (!response.ok) throw new Error("Error exportando Excel: " + response.status);
    const blob=await response.blob();
    const url=URL.createObjectURL(blob);
    const anchor=document.createElement("a");
    anchor.href=url; anchor.download="proyectos_auditoria.xlsx";
    document.body.append(anchor);anchor.click();anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  } catch(error) { window.alert(error.message); }
}

  function normalizeText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function getCookie(name) {
    const cookies = document.cookie
      ? document.cookie.split(";")
      : [];

    for (let index = 0; index < cookies.length; index += 1) {
      const cookie = cookies[index].trim();

      if (
        cookie.startsWith(
          name + "="
        )
      ) {
        return decodeURIComponent(
          cookie.substring(
            name.length + 1
          )
        );
      }
    }

    return null;
  }

  function applyFilters() {
    const searchValue = normalizeText(
      searchInput ? searchInput.value : ""
    );

    const selectedType = typeFilter
      ? typeFilter.value
      : "all";

    const selectedStatus = statusFilter
      ? statusFilter.value
      : "all";

    let visibleRows = 0;

    rows.forEach(function (row) {
      const searchContent = normalizeText(
        row.dataset.search
      );

      const matchesSearch =
        !searchValue ||
        searchContent.includes(searchValue);

      const rowTypes = String(
        row.dataset.type || ""
      )
        .split(/\s+/)
        .filter(Boolean);

      const matchesType =
        selectedType === "all" ||
        rowTypes.includes(selectedType);

      const matchesStatus =
        selectedStatus === "all" ||
        row.dataset.status === selectedStatus;

      const shouldShow =
        matchesSearch &&
        matchesType &&
        matchesStatus;

      row.hidden = !shouldShow;

      if (shouldShow) {
        visibleRows += 1;
      }
    });

    if (resultsCount) {
      resultsCount.textContent = String(visibleRows);
    }

    if (noResults) {
      noResults.hidden = visibleRows !== 0;
    }
  }

  function markRowAsDirty(row) {
    const saveButton = row.querySelector(
      "[data-save-audit-row]"
    );

    const savedMessage = row.querySelector(
      "[data-row-saved-message]"
    );

    row.classList.add("ap-audit-row-dirty");

    if (saveButton) {
      saveButton.disabled = false;
    }

    if (savedMessage) {
      savedMessage.hidden = true;
    }
  }

  rows.forEach(function (row) {
    const editableFields = row.querySelectorAll(
      "[data-audit-progress], " +
      "[data-audit-risk], " +
      "[data-audit-status]"
    );

    const progressSelect = row.querySelector(
      "[data-audit-progress]"
    );

    const progressBar = row.querySelector(
      "[data-progress-bar]"
    );

    const statusSelect = row.querySelector(
      "[data-audit-status]"
    );

    const saveButton = row.querySelector(
      "[data-save-audit-row]"
    );

    const savedMessage = row.querySelector(
      "[data-row-saved-message]"
    );

    editableFields.forEach(function (field) {
      field.addEventListener("change", function () {
        markRowAsDirty(row);
      });
    });

    const findingsInput = row.querySelector("[data-audit-findings]");
    findingsInput?.addEventListener("input", () => markRowAsDirty(row));

    if (progressSelect && progressBar) {
      progressSelect.addEventListener(
        "change",
        function () {
          progressBar.style.width =
            progressSelect.value + "%";
        }
      );
    }

    if (statusSelect) {
      statusSelect.addEventListener(
        "change",
        function () {
          row.dataset.status = statusSelect.value;
        }
      );
    }

    if (saveButton) {
      saveButton.addEventListener(
        "click",
        async function () {
          const updateUrl =
            row.dataset.updateUrl;

          const progressSelect =
            row.querySelector(
              "[data-audit-progress]"
            );

          const riskSelect =
            row.querySelector(
              "[data-audit-risk]"
            );

          const statusSelect =
            row.querySelector(
              "[data-audit-status]"
            );

          if (
            !updateUrl ||
            !progressSelect ||
            !riskSelect ||
            !statusSelect
          ) {
            window.alert(
              "No fue posible obtener los datos de la auditoría."
            );

            return;
          }

          saveButton.disabled = true;
          saveButton.classList.add(
            "is-loading"
          );

          const countInput = row.querySelector("[data-audit-findings]");
          const body = new URLSearchParams({
            progress:
              progressSelect.value,

            risk_level:
              riskSelect.value,

            workflow_status:
              statusSelect.value,
          });
          if (countInput) body.set("manual_findings_count", countInput.value);

          try {
            const response = await fetch(
              updateUrl,
              {
                method: "POST",

                headers: {
                  "X-CSRFToken":
                    getCookie(
                      "csrftoken"
                    ),

                  "X-Requested-With":
                    "XMLHttpRequest",

                  "Content-Type":
                    "application/x-www-form-urlencoded;charset=UTF-8",
                },

                body: body.toString(),
              }
            );

            const result =
              await response.json();

            if (!response.ok) {
              throw new Error(
                result.message ||
                "No fue posible guardar los cambios."
              );
            }

            row.classList.remove(
              "ap-audit-row-dirty"
            );

            row.dataset.status =
              statusSelect.value;

            if (savedMessage) {
              savedMessage.textContent =
                result.message ||
                "Cambios guardados";

              savedMessage.hidden = false;

              window.setTimeout(
                function () {
                  savedMessage.hidden = true;
                },
                2200
              );
            }
          } catch (error) {
            saveButton.disabled = false;

            window.alert(
              error.message ||
              "Ocurrió un error al guardar."
            );
          } finally {
            saveButton.classList.remove(
              "is-loading"
            );
          }
        }
      );
    }
  });

  document
    .querySelectorAll(".ap-audit-delete-form")
    .forEach(function (form) {
      form.addEventListener("submit", function (event) {
        const auditName =
          form.dataset.auditName ||
          "esta auditoría";

        const confirmed = window.confirm(
          "¿Seguro que deseas eliminar la auditoría de " +
          auditName +
          "?\n\nEsta acción elimina el registro y no se puede deshacer."
        );

        if (!confirmed) {
          event.preventDefault();
        }
      });
    });

  if (searchInput) {
    searchInput.addEventListener(
      "input",
      applyFilters
    );
  }

  if (typeFilter) {
    typeFilter.addEventListener(
      "change",
      applyFilters
    );
  }

  if (statusFilter) {
    statusFilter.addEventListener(
      "change",
      applyFilters
    );
  }

  if (exportButton) {
    exportButton.addEventListener(
      "click",
      exportVisibleAudits
    );
  }

    function openNewAuditModal() {
    if (!newAuditModal) {
      return;
    }

    newAuditModal.hidden = false;
    document.body.classList.add("ap-modal-open");

    const firstInput = document.getElementById(
      "newAuditIdentity"
    );

    window.setTimeout(function () {
      if (firstInput) {
        firstInput.focus();
      }
    }, 50);
  }

  function closeNewAuditModal() {
    if (!newAuditModal) {
      return;
    }

    newAuditModal.hidden = true;
    document.body.classList.remove("ap-modal-open");
  }

  function updatePeriodFromDates() {
    if (
      !startDateInput ||
      !endDateInput ||
      !periodInput ||
      periodInput.dataset.edited === "true"
    ) {
      return;
    }

    if (!startDateInput.value || !endDateInput.value) {
      return;
    }

    const startDate = new Date(
      startDateInput.value + "T00:00:00"
    );

    const endDate = new Date(
      endDateInput.value + "T00:00:00"
    );

    const formatter = new Intl.DateTimeFormat(
      "es-ES",
      {
        month: "short",
        year: "numeric"
      }
    );

    periodInput.value =
      formatter.format(startDate) +
      " – " +
      formatter.format(endDate);
  }

  function validateAuditDates() {
    if (
      !startDateInput ||
      !endDateInput ||
      !dateError
    ) {
      return true;
    }

    if (!startDateInput.value || !endDateInput.value) {
      dateError.hidden = true;
      return true;
    }

    const datesAreValid =
      endDateInput.value >= startDateInput.value;

    dateError.hidden = datesAreValid;

    return datesAreValid;
  }

  openNewAuditButtons.forEach(function (button) {
    button.addEventListener(
      "click",
      openNewAuditModal
    );
  });

  closeNewAuditButtons.forEach(function (button) {
    button.addEventListener(
      "click",
      closeNewAuditModal
    );
  });

  auditTypeOptions.forEach(function (option) {
    option.addEventListener(
      "change",
      function () {
        if (option.checked) {
          auditTypeOptions.forEach(function (item) {
            if (item !== option) item.checked = false;
          });
        }
        if (auditTypeError) {
          auditTypeError.hidden = auditTypeOptions.filter(
            function (item) { return item.checked; }
          ).length === 1;
        }
      }
    );
  });

  auditTeamOptions.forEach(function (option) {
    option.addEventListener("change", function () {
      if (
        auditTeamError &&
        auditTeamOptions.some(function (item) {
          return item.checked;
        })
      ) {
        auditTeamError.hidden = true;
      }
    });
  });

  if (periodInput) {
    periodInput.addEventListener("input", function () {
      periodInput.dataset.edited =
        periodInput.value.trim()
          ? "true"
          : "false";
    });
  }

  if (startDateInput) {
    startDateInput.addEventListener(
      "change",
      function () {
        validateAuditDates();
        updatePeriodFromDates();
      }
    );
  }

  if (endDateInput) {
    endDateInput.addEventListener(
      "change",
      function () {
        validateAuditDates();
        updatePeriodFromDates();
      }
    );
  }


  // Nombre sugerido automáticamente: tipo + entidad + año; respeta edición manual.
  const newIdentity = document.getElementById("newAuditIdentity");
  const newTitle = document.getElementById("newAuditTitle");
  const auditStart = document.getElementById("newAuditStartDate");
  const auditPeriod = document.getElementById("newAuditPeriod");
  if (newIdentity && newTitle) {
    let generated = "";
    function suggestTitle() {
      if (newTitle.value.trim() && newTitle.value.trim() !== generated) return;
      const selected = newAuditForm?.querySelector('input[name="selected_audit_type"]:checked')?.value || "F";
      const kind = {F:"Auditoría Financiera", R:"Revisoría Fiscal", I:"Auditoría Interna"}[selected];
      const entity = newIdentity.value.trim();
      const year = (auditPeriod?.value.match(/(?:19|20)\d{2}/)?.[0]) || auditStart?.value.slice(0,4) || new Date().getFullYear();
      generated = entity ? `${kind} - ${entity} - ${year}` : "";
      newTitle.value = generated.slice(0,255);
    }
    newIdentity.addEventListener("input", suggestTitle);
    auditPeriod?.addEventListener("input", suggestTitle);
    auditStart?.addEventListener("change", suggestTitle);
    newAuditForm?.querySelectorAll('input[name="selected_audit_type"]').forEach(el => el.addEventListener("change", suggestTitle));
  }
  if (newAuditForm) {
    newAuditForm.addEventListener(
      "submit",
      function (event) {
        const hasSelectedType =
          auditTypeOptions.filter(function (option) {
            return option.checked;
          }).length === 1;

        const requiresTeam =
          auditTeamOptions.length > 0;

        const hasSelectedTeam =
          auditTeamOptions.some(function (option) {
            return option.checked;
          });

        let formIsValid = true;

        if (!hasSelectedType) {
          formIsValid = false;

          if (auditTypeError) {
            auditTypeError.hidden = false;
          }
        }

        if (
          requiresTeam &&
          !hasSelectedTeam
        ) {
          formIsValid = false;

          if (auditTeamError) {
            auditTeamError.hidden = false;
          }
        }

        if (!validateAuditDates()) {
          formIsValid = false;
        }

        if (!newAuditForm.checkValidity()) {
          formIsValid = false;
          newAuditForm.reportValidity();
        }

        if (!formIsValid) {
          event.preventDefault();
          return;
        }

        if (newAuditSubmitButton) {
          newAuditSubmitButton.disabled = true;

          newAuditSubmitButton.innerHTML =
            '<span class="spinner-border ' +
            'spinner-border-sm"></span>' +
            " Creando...";
        }
      }
    );
  }

  document.addEventListener("keydown", function (event) {
    if (
      event.key === "Escape" &&
      newAuditModal &&
      !newAuditModal.hidden
    ) {
      closeNewAuditModal();
    }
  });

  const queryParameters = new URLSearchParams(
    window.location.search
  );

  if (queryParameters.get("open") === "new") {
    openNewAuditModal();
  }

  applyFilters();
});