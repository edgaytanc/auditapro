(function () {
  "use strict";

  const MATERIALIDAD_EJECUCION = 185000;

  const CONTROL_FACTOR = {
    adecuado: 0.55,
    parcial: 0.25,
    "no-existe": 0
  };

  const CONTROL_LABEL = {
    adecuado: "Adecuado",
    parcial: "Parcial",
    "no-existe": "No existe"
  };

  const initialRisks = [
    {
      cuenta: "Efectivo y equivalentes",
      asercion: "Existencia — saldos conciliados sin evidencia bancaria",
      saldo: 412000,
      prob: 2,
      impacto: 4,
      control: "adecuado",
      respuesta: ""
    },
    {
      cuenta: "Cuentas por cobrar",
      asercion: "Valuación — estimación de incobrables sin metodología documentada",
      saldo: 1180000,
      prob: 4,
      impacto: 5,
      control: "parcial",
      respuesta: ""
    },
    {
      cuenta: "Inventarios",
      asercion: "Existencia y valuación — conteo físico no supervisado por auditoría",
      saldo: 2340000,
      prob: 3,
      impacto: 5,
      control: "parcial",
      respuesta: ""
    },
    {
      cuenta: "Propiedad, planta y equipo",
      asercion: "Valuación — depreciación calculada con vidas útiles no revisadas",
      saldo: 3050000,
      prob: 2,
      impacto: 5,
      control: "adecuado",
      respuesta: ""
    },
    {
      cuenta: "Cuentas por pagar",
      asercion: "Integridad — pasivos no registrados",
      saldo: 860000,
      prob: 3,
      impacto: 4,
      control: "parcial",
      respuesta: ""
    },
    {
      cuenta: "Ingresos",
      asercion: "Corte — reconocimiento de ingresos en el período incorrecto",
      saldo: 5600000,
      prob: 3,
      impacto: 5,
      control: "no-existe",
      respuesta: ""
    }
  ];

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/"/g, "&quot;");
  }

  function classify(score) {
    if (score >= 15) {
      return "alto";
    }

    if (score >= 8) {
      return "medio";
    }

    return "bajo";
  }

  function riskLabel(level) {
    if (level === "alto") {
      return "Alto";
    }

    if (level === "medio") {
      return "Medio";
    }

    return "Bajo";
  }

  function computeRisk(risk) {
    const inherentScore = risk.prob * risk.impacto;
    const reduction = CONTROL_FACTOR[risk.control] || 0;
    const residualScore = Math.round(
      inherentScore * (1 - reduction)
    );

    return {
      ...risk,
      inherentScore,
      inherentLevel: classify(inherentScore),
      residualScore,
      residualLevel: classify(residualScore)
    };
  }

  function heatColor(score) {
    if (score >= 15) {
      return "#ef4444";
    }

    if (score >= 10) {
      return "#f59e0b";
    }

    if (score >= 5) {
      return "#eab308";
    }

    return "#22c55e";
  }

  let riskData = initialRisks.map(computeRisk);

  function renderKpis() {
    const total = riskData.length;

    const high = riskData.filter(function (risk) {
      return risk.residualLevel === "alto";
    }).length;

    const medium = riskData.filter(function (risk) {
      return risk.residualLevel === "medio";
    }).length;

    const low = riskData.filter(function (risk) {
      return risk.residualLevel === "bajo";
    }).length;

    const average = total
      ? Math.round(
          riskData.reduce(function (sum, risk) {
            return sum + risk.inherentScore;
          }, 0) / total
        )
      : 0;

    document.getElementById("financialRiskKpis").innerHTML = `
      <article class="financial-risk-kpi">
        <div class="financial-risk-kpi__label">Cuentas evaluadas</div>
        <div class="financial-risk-kpi__value financial-risk-kpi__value--blue">
          ${total}
        </div>
      </article>

      <article class="financial-risk-kpi">
        <div class="financial-risk-kpi__label">Riesgo residual alto</div>
        <div class="financial-risk-kpi__value financial-risk-kpi__value--red">
          ${high}
        </div>
      </article>

      <article class="financial-risk-kpi">
        <div class="financial-risk-kpi__label">Riesgo residual medio</div>
        <div class="financial-risk-kpi__value financial-risk-kpi__value--amber">
          ${medium}
        </div>
      </article>

      <article class="financial-risk-kpi">
        <div class="financial-risk-kpi__label">Riesgo residual bajo</div>
        <div class="financial-risk-kpi__value financial-risk-kpi__value--green">
          ${low}
        </div>
      </article>

      <article class="financial-risk-kpi">
        <div class="financial-risk-kpi__label">Materialidad de ejecución</div>
        <div class="financial-risk-kpi__value financial-risk-kpi__value--teal">
          Q${MATERIALIDAD_EJECUCION.toLocaleString("es-GT")}
        </div>
        <div class="financial-risk-kpi__sub">
          Score inherente promedio: ${average}/25
        </div>
      </article>
    `;
  }

  function renderHeatmap() {
    const counts = {};

    for (let probability = 1; probability <= 5; probability += 1) {
      for (let impact = 1; impact <= 5; impact += 1) {
        counts[`${probability}-${impact}`] = 0;
      }
    }

    riskData.forEach(function (risk) {
      counts[`${risk.prob}-${risk.impacto}`] += 1;
    });

    let html = `
      <div class="financial-risk-heatmap-corner">
        Prob. ↓
      </div>
    `;

    for (let impact = 1; impact <= 5; impact += 1) {
      html += `
        <div class="financial-risk-heatmap-column">
          ${impact}
        </div>
      `;
    }

    for (let probability = 5; probability >= 1; probability -= 1) {
      html += `
        <div class="financial-risk-heatmap-row">
          ${probability}
        </div>
      `;

      for (let impact = 1; impact <= 5; impact += 1) {
        const score = probability * impact;
        const quantity = counts[`${probability}-${impact}`];

        html += `
          <div
            class="financial-risk-heatmap-cell"
            style="
              background:${heatColor(score)};
              opacity:${quantity > 0 ? 1 : 0.35};
            "
          >
            ${quantity > 0 ? quantity : ""}
          </div>
        `;
      }
    }

    document.getElementById("financialRiskHeatmap").innerHTML = html;
  }

  function renderResidualBars() {
    const maximumScore = 25;

    document.getElementById(
      "financialRiskResidualBars"
    ).innerHTML = riskData.map(function (risk) {
      return `
        <div class="financial-risk-residual-item">

          <div class="financial-risk-residual-header">
            <span>
              ${escapeHtml(risk.cuenta || "Cuenta sin nombre")}
            </span>

            <span class="financial-risk-residual-score">
              ${risk.inherentScore} → ${risk.residualScore}
            </span>
          </div>

          <div class="financial-risk-residual-track">

            <div
              class="financial-risk-residual-inherent"
              style="width:${(risk.inherentScore / maximumScore) * 100}%"
            ></div>

            <div
              class="financial-risk-residual-value"
              style="
                width:${(risk.residualScore / maximumScore) * 100}%;
                background:${heatColor(risk.residualScore)};
              "
            ></div>

          </div>

        </div>
      `;
    }).join("");
  }

  function renderTable() {
    document.getElementById(
      "financialRiskBody"
    ).innerHTML = riskData.map(function (risk, index) {
      const probabilityOptions = [1, 2, 3, 4, 5]
        .map(function (value) {
          return `
            <option
              value="${value}"
              ${risk.prob === value ? "selected" : ""}
            >
              ${value}
            </option>
          `;
        })
        .join("");

      const impactOptions = [1, 2, 3, 4, 5]
        .map(function (value) {
          return `
            <option
              value="${value}"
              ${risk.impacto === value ? "selected" : ""}
            >
              ${value}
            </option>
          `;
        })
        .join("");

      const controlOptions = [
        "adecuado",
        "parcial",
        "no-existe"
      ]
        .map(function (value) {
          return `
            <option
              value="${value}"
              ${risk.control === value ? "selected" : ""}
            >
              ${CONTROL_LABEL[value]}
            </option>
          `;
        })
        .join("");

      return `
        <tr>

          <td>
            <input
              type="text"
              class="financial-risk-input"
              value="${escapeAttribute(risk.cuenta)}"
              placeholder="Nombre de la cuenta"
              onchange="updateFinancialRisk(
                ${index},
                'cuenta',
                this.value
              )"
            >

            <div class="financial-risk-cell-subtitle">
              Saldo Q
            </div>

            <input
              type="number"
              class="financial-risk-input financial-risk-balance"
              value="${risk.saldo}"
              onchange="updateFinancialRisk(
                ${index},
                'saldo',
                this.value
              )"
            >

            ${
              risk.saldo >= MATERIALIDAD_EJECUCION
                ? `
                  <span class="financial-risk-materiality">
                    &gt; materialidad
                  </span>
                `
                : ""
            }
          </td>

          <td>
            <textarea
              class="financial-risk-textarea"
              placeholder="Redactar riesgo o aserción afectada"
              onchange="updateFinancialRisk(
                ${index},
                'asercion',
                this.value
              )"
            >${escapeHtml(risk.asercion)}</textarea>
          </td>

          <td>
            <select
              class="financial-risk-select"
              onchange="updateFinancialRisk(
                ${index},
                'prob',
                this.value
              )"
            >
              ${probabilityOptions}
            </select>
          </td>

          <td>
            <select
              class="financial-risk-select"
              onchange="updateFinancialRisk(
                ${index},
                'impacto',
                this.value
              )"
            >
              ${impactOptions}
            </select>
          </td>

          <td>
            <span class="financial-risk-pill ${risk.inherentLevel}">
              ${riskLabel(risk.inherentLevel)}
            </span>

            <span class="financial-risk-score">
              score ${risk.inherentScore}/25
            </span>
          </td>

          <td>
            <select
              class="financial-risk-select"
              onchange="updateFinancialRisk(
                ${index},
                'control',
                this.value
              )"
            >
              ${controlOptions}
            </select>
          </td>

          <td>
            <span class="financial-risk-pill ${risk.residualLevel}">
              ${riskLabel(risk.residualLevel)}
            </span>

            <span class="financial-risk-score">
              score ${risk.residualScore}/25
            </span>
          </td>

          <td>
            <textarea
                class="financial-risk-textarea"
                placeholder="Redactar respuesta de auditoría"
                onchange="updateFinancialRisk(
                ${index},
                'respuesta',
                this.value
                )"
            >${escapeHtml(risk.respuesta)}</textarea>
            </td>

            <td>
            <button
                type="button"
                class="financial-risk-delete-button"
                onclick="deleteFinancialRisk(${index})"
                title="Eliminar cuenta"
            >
                <i class="bi bi-trash3"></i>
                Eliminar
            </button>
            </td>

            </tr>
      `;
    }).join("");
  }

  function renderAll() {
    renderKpis();
    renderHeatmap();
    renderResidualBars();
    renderTable();
  }

  window.updateFinancialRisk = function (index, field, value) {
    const current = riskData[index];

    const rawRisk = {
      cuenta: current.cuenta,
      asercion: current.asercion,
      saldo: current.saldo,
      prob: current.prob,
      impacto: current.impacto,
      control: current.control,
      respuesta: current.respuesta
    };

    if (
      field === "prob" ||
      field === "impacto" ||
      field === "saldo"
    ) {
      rawRisk[field] = Number(value) || 0;
    } else {
      rawRisk[field] = value;
    }

    riskData[index] = computeRisk(rawRisk);

    renderAll();
  };

  window.deleteFinancialRisk = function (index) {
  const risk = riskData[index];

  if (!risk) {
    return;
  }

  if (riskData.length === 1) {
  const removeLast = window.confirm(
    "Esta es la última cuenta de la matriz. Si continúas, la matriz quedará vacía. ¿Deseas eliminarla?"
  );

  if (!removeLast) {
    return;
  }
}

  const accountName =
    risk.cuenta && risk.cuenta.trim()
      ? risk.cuenta.trim()
      : "esta cuenta";

  const confirmed = window.confirm(
    `¿Deseas eliminar "${accountName}" de la matriz de riesgos?`
  );

  if (!confirmed) {
    return;
  }

  riskData.splice(index, 1);

  renderAll();

  showStatus(
    `La cuenta "${accountName}" fue eliminada de la matriz.`,
    false
  );
};

  function addRiskAccount() {
    riskData.push(
      computeRisk({
        cuenta: "Nueva cuenta",
        asercion: "",
        saldo: 0,
        prob: 1,
        impacto: 1,
        control: "no-existe",
        respuesta: ""
      })
    );

    renderAll();

    const rows = document.querySelectorAll(
      "#financialRiskBody tr"
    );

    const lastRow = rows[rows.length - 1];

    if (lastRow) {
      lastRow.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
    }
  }

  function replaceControlsWithValues(sourceTable, clonedTable) {
    const sourceControls = sourceTable.querySelectorAll(
      "input, textarea, select"
    );

    const clonedControls = clonedTable.querySelectorAll(
      "input, textarea, select"
    );

    sourceControls.forEach(function (control, index) {
      const clonedControl = clonedControls[index];

      if (!clonedControl) {
        return;
      }

      const replacement = document.createElement("span");

      if (control.tagName === "SELECT") {
        const selectedOption =
          control.options[control.selectedIndex];

        replacement.textContent = selectedOption
          ? selectedOption.text
          : "";
      } else {
        replacement.textContent = control.value || "";
      }

      clonedControl.replaceWith(replacement);
    });
  }

  async function exportRiskMatrixToExcel() {
    const table = document.getElementById("financialRiskTable");
    const url = table?.dataset.exportUrl;
    const token = document.cookie.split("; ").find(c => c.startsWith("csrftoken="))?.split("=").slice(1).join("=");
    if (!url || !token) { showStatus("No se encontró la ruta de exportación o el token CSRF.", true); return; }
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(token)},
        body: JSON.stringify({riesgos: riskData, company_name: document.getElementById("financialCompanyName")?.value?.trim() || ""})
      });
      if (!response.ok) throw new Error("La exportación no pudo completarse (" + response.status + ").");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "matriz_riesgos_y_mapa_calor.xlsx";
      document.body.append(link); link.click(); link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
      showStatus("Se descargaron las hojas Datos y Mapa de calor en Excel.", false);
    } catch (error) { showStatus(error.message, true); }
  }

  function showStatus(message, isError) {
    const status = document.getElementById(
      "financialRiskStatus"
    );

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

  const addButton = document.getElementById(
    "addRiskAccountButton"
  );

  const exportButton = document.getElementById(
    "exportRiskExcelButton"
  );

  if (addButton) {
    addButton.addEventListener(
      "click",
      addRiskAccount
    );
  }

  if (exportButton) {
    exportButton.addEventListener(
      "click",
      exportRiskMatrixToExcel
    );
  }

  renderAll();
})();