(function () {
  "use strict";

  const MATERIALIDAD_EJECUCION = 185000;

  const ACCOUNTS = [
    "Efectivo",
    "Cuentas por Cobrar",
    "Inventarios",
    "Propiedad, planta y equipo",
    "Cuentas por Pagar",
    "Ingresos"
  ];

  const STATES = [
    {
      value: "pendiente",
      label: "Pendiente"
    },
    {
      value: "en-proceso",
      label: "En proceso"
    },
    {
      value: "implementado",
      label: "Implementado"
    }
  ];

  let findings = [
    {
      id: "H-01",
      finding:
        "Estimación de cuentas incobrables sin metodología documentada ni respaldo histórico",
      recommendation:
        "Documentar política de estimación con base en antigüedad de saldos",
      account: "Cuentas por Cobrar",
      effect: 210000,
      responsible: "Gerencia Financiera",
      state: "implementado"
    },
    {
      id: "H-02",
      finding:
        "Conteo físico de inventario 2025 realizado sin presencia de auditoría",
      recommendation:
        "Planificar observación de conteo físico para el cierre 2026",
      account: "Inventarios",
      effect: 95000,
      responsible: "Gerencia de Operaciones",
      state: "implementado"
    },
    {
      id: "H-03",
      finding:
        "23 facturas de proveedores registradas dos veces en el mayor auxiliar",
      recommendation:
        "Conciliar y anular partidas duplicadas; activar validación de folio único en el ERP",
      account: "Cuentas por Pagar",
      effect: 238000,
      responsible: "Tesorería",
      state: "pendiente"
    },
    {
      id: "H-04",
      finding:
        "8 proveedores del mayor auxiliar no se encuentran registrados en el padrón fiscal vigente",
      recommendation:
        "Validar existencia y estado fiscal de proveedores antes del pago",
      account: "Cuentas por Pagar",
      effect: 68000,
      responsible: "Tesorería",
      state: "pendiente"
    },
    {
      id: "H-05",
      finding:
        "Reconocimiento de ingresos de cuatro facturas de diciembre registradas en enero de 2026",
      recommendation:
        "Reforzar el corte documental de ventas a fin de período",
      account: "Ingresos",
      effect: 196000,
      responsible: "Contabilidad",
      state: "en-proceso"
    },
    {
      id: "H-06",
      finding:
        "Diferencias no explicadas entre el mayor auxiliar y el saldo de conciliación bancaria",
      recommendation:
        "Investigar partidas conciliatorias pendientes y depurar",
      account: "Efectivo",
      effect: 42500,
      responsible: "Contabilidad",
      state: "pendiente"
    }
  ];

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value)
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getSeverity(effect) {
    const numericEffect = Number(effect) || 0;

    if (numericEffect >= MATERIALIDAD_EJECUCION) {
      return "significativo";
    }

    if (
      numericEffect >=
      MATERIALIDAD_EJECUCION * 0.35
    ) {
      return "moderado";
    }

    return "leve";
  }

  function getSeverityLabel(severity) {
    if (severity === "significativo") {
      return "Significativo";
    }

    if (severity === "moderado") {
      return "Moderado";
    }

    return "Leve";
  }

  function getStateLabel(state) {
    const currentState = STATES.find(function (item) {
      return item.value === state;
    });

    return currentState
      ? currentState.label
      : state;
  }

  function formatMoney(value) {
    return Number(value || 0).toLocaleString("es-GT");
  }

  function getFilteredFindings() {
    const searchInput = document.getElementById(
      "findingsSearchInput"
    );

    const severityFilter = document.getElementById(
      "findingsSeverityFilter"
    );

    const query = searchInput
      ? searchInput.value.trim().toLowerCase()
      : "";

    const selectedSeverity = severityFilter
      ? severityFilter.value
      : "";

    return findings.filter(function (finding) {
      const searchContent = [
        finding.id,
        finding.finding,
        finding.recommendation,
        finding.account,
        finding.responsible
      ]
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query || searchContent.includes(query);

      const matchesSeverity =
        !selectedSeverity ||
        getSeverity(finding.effect) ===
          selectedSeverity;

      return matchesSearch && matchesSeverity;
    });
  }

  function renderKpis(visibleFindings) {
    const significant = visibleFindings.filter(
      function (finding) {
        return (
          getSeverity(finding.effect) ===
          "significativo"
        );
      }
    ).length;

    const pending = visibleFindings.filter(
      function (finding) {
        return finding.state === "pendiente";
      }
    ).length;

    const inProgress = visibleFindings.filter(
      function (finding) {
        return finding.state === "en-proceso";
      }
    ).length;

    const implemented = visibleFindings.filter(
      function (finding) {
        return finding.state === "implementado";
      }
    ).length;

    document.getElementById(
      "financialFindingsKpis"
    ).innerHTML = `
      <article class="financial-findings-kpi">
        <div class="financial-findings-kpi__label">
          Total hallazgos
        </div>

        <div class="
          financial-findings-kpi__value
          financial-findings-kpi__value--blue
        ">
          ${visibleFindings.length}
        </div>
      </article>

      <article class="financial-findings-kpi">
        <div class="financial-findings-kpi__label">
          Significativos
        </div>

        <div class="
          financial-findings-kpi__value
          financial-findings-kpi__value--red
        ">
          ${significant}
        </div>
      </article>

      <article class="financial-findings-kpi">
        <div class="financial-findings-kpi__label">
          Pendientes
        </div>

        <div class="
          financial-findings-kpi__value
          financial-findings-kpi__value--amber
        ">
          ${pending}
        </div>
      </article>

      <article class="financial-findings-kpi">
        <div class="financial-findings-kpi__label">
          En proceso
        </div>

        <div class="
          financial-findings-kpi__value
          financial-findings-kpi__value--blue
        ">
          ${inProgress}
        </div>
      </article>

      <article class="financial-findings-kpi">
        <div class="financial-findings-kpi__label">
          Implementados
        </div>

        <div class="
          financial-findings-kpi__value
          financial-findings-kpi__value--green
        ">
          ${implemented}
        </div>
      </article>
    `;
  }

  function renderTable() {
    const visibleFindings = getFilteredFindings();

    renderKpis(visibleFindings);

    document.getElementById(
      "financialFindingsCount"
    ).textContent =
      `${visibleFindings.length} de ` +
      `${findings.length} hallazgos`;

    const body = document.getElementById(
      "financialFindingsBody"
    );

    if (!visibleFindings.length) {
      body.innerHTML = `
        <tr>
          <td
            colspan="8"
            class="financial-findings-empty"
          >
            No se encontraron hallazgos con los filtros seleccionados.
          </td>
        </tr>
      `;

      return;
    }

    body.innerHTML = visibleFindings
      .map(function (finding) {
        const index = findings.indexOf(finding);
        const severity = getSeverity(
          finding.effect
        );

        const accountOptions = ACCOUNTS
          .map(function (account) {
            return `
              <option
                value="${escapeAttribute(account)}"
                ${
                  finding.account === account
                    ? "selected"
                    : ""
                }
              >
                ${escapeHtml(account)}
              </option>
            `;
          })
          .join("");

        const stateOptions = STATES
          .map(function (state) {
            return `
              <option
                value="${state.value}"
                ${
                  finding.state === state.value
                    ? "selected"
                    : ""
                }
              >
                ${state.label}
              </option>
            `;
          })
          .join("");

        return `
          <tr>

            <td class="financial-findings-id">
              ${escapeHtml(finding.id)}
            </td>

            <td>
              <label class="financial-findings-field-label">
                Hallazgo
              </label>

              <textarea
                class="financial-findings-textarea"
                onchange="updateFinancialFinding(
                  ${index},
                  'finding',
                  this.value
                )"
              >${escapeHtml(finding.finding)}</textarea>

              <label class="financial-findings-field-label">
                Recomendación
              </label>

              <textarea
                class="financial-findings-textarea"
                onchange="updateFinancialFinding(
                  ${index},
                  'recommendation',
                  this.value
                )"
              >${escapeHtml(finding.recommendation)}</textarea>
            </td>

            <td>
              <select
                class="financial-findings-select"
                onchange="updateFinancialFinding(
                  ${index},
                  'account',
                  this.value
                )"
              >
                ${accountOptions}
              </select>
            </td>

            <td>
              <input
                type="number"
                min="0"
                class="
                  financial-findings-input
                  financial-findings-effect
                "
                value="${finding.effect}"
                onchange="updateFinancialFinding(
                  ${index},
                  'effect',
                  this.value
                )"
              >
            </td>

            <td>
              <span
                class="
                  financial-findings-badge
                  ${severity}
                "
              >
                ${getSeverityLabel(severity)}
              </span>
            </td>

            <td>
              <input
                type="text"
                class="financial-findings-input"
                value="${escapeAttribute(
                  finding.responsible
                )}"
                placeholder="Asignar responsable"
                onchange="updateFinancialFinding(
                  ${index},
                  'responsible',
                  this.value
                )"
              >
            </td>

            <td>
              <select
                class="financial-findings-select"
                onchange="updateFinancialFinding(
                  ${index},
                  'state',
                  this.value
                )"
              >
                ${stateOptions}
              </select>
            </td>

            <td>
              <button
                type="button"
                class="financial-findings-delete"
                onclick="deleteFinancialFinding(${index})"
              >
                <i class="bi bi-trash3"></i>
                Eliminar
              </button>
            </td>

          </tr>
        `;
      })
      .join("");
  }

  window.updateFinancialFinding = function (
    index,
    field,
    value
  ) {
    const finding = findings[index];

    if (!finding) {
      return;
    }

    if (field === "effect") {
      finding[field] = Number(value) || 0;
    } else {
      finding[field] = value;
    }

    renderTable();
  };

  function getNextFindingId() {
    const maximumId = findings.reduce(
      function (maximum, finding) {
        const number = Number(
          String(finding.id).replace(/\D/g, "")
        );

        return Number.isFinite(number)
          ? Math.max(maximum, number)
          : maximum;
      },
      0
    );

    return `H-${String(maximumId + 1).padStart(
      2,
      "0"
    )}`;
  }

  function addFinding() {
    const searchInput = document.getElementById(
      "findingsSearchInput"
    );

    const severityFilter = document.getElementById(
      "findingsSeverityFilter"
    );

    if (searchInput) {
      searchInput.value = "";
    }

    if (severityFilter) {
      severityFilter.value = "";
    }

    findings.push({
      id: getNextFindingId(),
      finding: "",
      recommendation: "",
      account: ACCOUNTS[0],
      effect: 0,
      responsible: "",
      state: "pendiente"
    });

    renderTable();

    const rows = document.querySelectorAll(
      "#financialFindingsBody tr"
    );

    const lastRow = rows[rows.length - 1];

    if (lastRow) {
      lastRow.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
    }

    showStatus(
      "Se agregó un nuevo hallazgo editable.",
      false
    );
  }

  window.deleteFinancialFinding = function (index) {
    const finding = findings[index];

    if (!finding) {
      return;
    }

    const message =
      findings.length === 1
        ? `Este es el último hallazgo. Si eliminas ${finding.id}, la tabla quedará vacía. ¿Deseas continuar?`
        : `¿Deseas eliminar el hallazgo ${finding.id}?`;

    if (!window.confirm(message)) {
      return;
    }

    findings.splice(index, 1);

    renderTable();

    showStatus(
      `El hallazgo ${finding.id} fue eliminado.`,
      false
    );
  };

  function exportFindingsToExcel() {
    const visibleFindings = getFilteredFindings();

    if (!visibleFindings.length) {
      showStatus(
        "No hay hallazgos visibles para exportar.",
        true
      );

      return;
    }

    const rows = visibleFindings
      .map(function (finding) {
        const severity = getSeverity(
          finding.effect
        );

        return `
          <tr>
            <td>${escapeHtml(finding.id)}</td>
            <td>${escapeHtml(finding.finding)}</td>
            <td>${escapeHtml(
              finding.recommendation
            )}</td>
            <td>${escapeHtml(finding.account)}</td>
            <td>Q${formatMoney(finding.effect)}</td>
            <td>${getSeverityLabel(severity)}</td>
            <td>${escapeHtml(
              finding.responsible
            )}</td>
            <td>${getStateLabel(finding.state)}</td>
          </tr>
        `;
      })
      .join("");

    const excelDocument = `
      <!DOCTYPE html>
      <html
        xmlns:o="urn:schemas-microsoft-com:office:office"
        xmlns:x="urn:schemas-microsoft-com:office:excel"
        xmlns="http://www.w3.org/TR/REC-html40"
      >
        <head>
          <meta charset="UTF-8">

          <style>
            body {
              font-family: Arial, sans-serif;
            }

            h1 {
              color: #0f766e;
            }

            table {
              width: 100%;
              border-collapse: collapse;
            }

            th {
              background: #0f766e;
              color: #ffffff;
            }

            th,
            td {
              padding: 7px;
              border: 1px solid #cbd5e1;
              vertical-align: top;
            }
          </style>
        </head>

        <body>
          <h1>
            Hallazgos y Recomendaciones
          </h1>

          <p>Empresa: ${escapeHtml(document.getElementById("financialCompanyName")?.value?.trim() || "Sin especificar")}</p>

          <p>
            Materialidad de ejecución:
            Q${formatMoney(MATERIALIDAD_EJECUCION)}
          </p>

          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Hallazgo</th>
                <th>Recomendación</th>
                <th>Cuenta</th>
                <th>Efecto</th>
                <th>Severidad</th>
                <th>Responsable</th>
                <th>Estado</th>
              </tr>
            </thead>

            <tbody>
              ${rows}
            </tbody>
          </table>
        </body>
      </html>
    `;

    const blob = new Blob(
      ["\ufeff", excelDocument],
      {
        type:
          "application/vnd.ms-excel;" +
          "charset=utf-8;"
      }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download =
      "hallazgos-recomendaciones-af-2026-004.xls";

    document.body.appendChild(link);

    link.click();
    link.remove();

    window.setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);

    showStatus(
      `Se exportaron ${visibleFindings.length} hallazgos visibles.`,
      false
    );
  }

  function showStatus(message, isError) {
    const status = document.getElementById(
      "financialFindingsStatus"
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

  const searchInput = document.getElementById(
    "findingsSearchInput"
  );

  const severityFilter = document.getElementById(
    "findingsSeverityFilter"
  );

  const addButton = document.getElementById(
    "addFindingButton"
  );

  const exportButton = document.getElementById(
    "exportFindingsExcelButton"
  );

  if (searchInput) {
    searchInput.addEventListener(
      "input",
      renderTable
    );
  }

  if (severityFilter) {
    severityFilter.addEventListener(
      "change",
      renderTable
    );
  }

  if (addButton) {
    addButton.addEventListener(
      "click",
      addFinding
    );
  }

  if (exportButton) {
    exportButton.addEventListener(
      "click",
      exportFindingsToExcel
    );
  }

  renderTable();
})();