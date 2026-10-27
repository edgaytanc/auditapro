document.addEventListener(
  "DOMContentLoaded",
  function () {

    const tableBody = document.getElementById(
      "iaTableBody"
    );

    if (!tableBody) {
      return;
    }

    const searchInput = document.getElementById(
      "iaSearch"
    );

    const statusFilter = document.getElementById(
      "iaStatusFilter"
    );

    const riskFilter = document.getElementById(
      "iaRiskFilter"
    );

    const auditorFilter = document.getElementById(
      "iaAuditorFilter"
    );

    const resultCount = document.getElementById(
      "iaResultCount"
    );

    const emptyState = document.getElementById(
      "iaEmptyState"
    );

    const exportButton = document.getElementById(
      "iaExportExcel"
    );

    const kpiTotal = document.getElementById(
      "iaKpiTotal"
    );

    const kpiProgress = document.getElementById(
      "iaKpiProgress"
    );

    const kpiHighRisk = document.getElementById(
      "iaKpiHighRisk"
    );

    const kpiAverage = document.getElementById(
      "iaKpiAverage"
    );

    const kpiClosing = document.getElementById(
      "iaKpiClosing"
    );


    function normalize(value) {
      return String(
        value || ""
      )
        .normalize("NFD")
        .replace(
          /[\u0300-\u036f]/g,
          ""
        )
        .trim()
        .toLowerCase();
    }


    function getRows() {
      return Array.from(
        tableBody.querySelectorAll(
          "[data-ia-row]"
        )
      );
    }


    function syncRow(row) {
      const field = (name) => row.querySelector('[name="'+name+'"]');
      if (!field('display_code')) return;
      const get = name => field(name)?.value || '';
      row.dataset.code = get('display_code');
      row.dataset.process = get('process_area');
      row.dataset.client = get('client');
      row.dataset.auditor = get('auditor_name');
      row.dataset.auditors = get('auditor_name');
      row.dataset.progress = get('manual_progress');
      row.dataset.close = get('manual_close_date');
      row.dataset.status = get('workflow_status');
      row.dataset.risk = get('risk_level');
      row.dataset.statusLabel = field('workflow_status')?.selectedOptions?.[0]?.textContent || '';
      row.dataset.riskLabel = field('risk_level')?.selectedOptions?.[0]?.textContent || '';
      row.dataset.search = [row.dataset.code,row.dataset.process,row.dataset.client,row.dataset.auditor].join(' ');
      if (row.dataset.close) {
        const today=new Date(); today.setHours(0,0,0,0);
        const end=new Date(row.dataset.close+'T00:00:00');
        row.dataset.days=String(Math.round((end-today)/86400000));
      } else row.dataset.days='';
    }
    tableBody.addEventListener('input', function(event){
      const row=event.target.closest('[data-ia-row]');
      if(row){syncRow(row);applyFilters();}
    });
    tableBody.addEventListener('change', function(event){
      const row=event.target.closest('[data-ia-row]');
      if(row){syncRow(row);applyFilters();}
    });
    function getVisibleRows() {
      return getRows().filter(
        function (row) {
          return !row.hidden;
        }
      );
    }


    function updateKpis(rows) {

      const total = rows.length;

      const inProgress = rows.filter(
        function (row) {
          return (
            row.dataset.status
            === "progress"
          );
        }
      ).length;

      const highRisk = rows.filter(
        function (row) {
          return (
            row.dataset.risk
            === "high"
          );
        }
      ).length;

      const progressValues = rows.map(
        function (row) {
          return Number(
            row.dataset.progress || 0
          );
        }
      );

      const average = (
        progressValues.length
          ? Math.round(
              progressValues.reduce(
                function (sum, value) {
                  return sum + value;
                },
                0
              )
              / progressValues.length
            )
          : 0
      );

      const closingSoon = rows.filter(
        function (row) {

          if (
            row.dataset.status
            === "completed"
          ) {
            return false;
          }

          if (
            row.dataset.days === ""
          ) {
            return false;
          }

          const days = Number(
            row.dataset.days
          );

          return days <= 7;
        }
      ).length;


      kpiTotal.textContent = total;

      kpiProgress.textContent = (
        inProgress
      );

      kpiHighRisk.textContent = (
        highRisk
      );

      kpiAverage.textContent = (
        average + "%"
      );

      kpiClosing.textContent = (
        closingSoon
      );
    }


    function applyFilters() {

      const query = normalize(
        searchInput.value
      );

      const status = (
        statusFilter.value
      );

      const risk = (
        riskFilter.value
      );

      const auditor = (
        auditorFilter.value
      );

      const rows = getRows();

      rows.forEach(
        function (row) {

          const matchesQuery = (
            !query
            || normalize(
              row.dataset.search
            ).includes(query)
          );

          const matchesStatus = (
            !status
            || row.dataset.status
              === status
          );

          const matchesRisk = (
            !risk
            || row.dataset.risk
              === risk
          );

          const rowAuditors = (
            row.dataset.auditors || ""
          )
            .split("|")
            .filter(Boolean);

          const matchesAuditor = (
            !auditor
            || rowAuditors.includes(
              auditor
            )
          );

          row.hidden = !(
            matchesQuery
            && matchesStatus
            && matchesRisk
            && matchesAuditor
          );
        }
      );


      const visibleRows = (
        getVisibleRows()
      );

      resultCount.textContent = (
        visibleRows.length
        + " de "
        + rows.length
        + " auditorías"
      );

      emptyState.hidden = (
        visibleRows.length > 0
      );

      updateKpis(
        visibleRows
      );
    }


    [
      searchInput,
      statusFilter,
      riskFilter,
      auditorFilter,
    ].forEach(
      function (control) {

        control.addEventListener(
          control.tagName === "INPUT"
            ? "input"
            : "change",
          applyFilters
        );

      }
    );


    let activeSort = null;
    let sortDirection = 1;


    function sortRows(key) {

      if (activeSort === key) {
        sortDirection *= -1;
      } else {
        activeSort = key;
        sortDirection = 1;
      }

      const rows = getRows();

      rows.sort(
        function (rowA, rowB) {

          let valueA;
          let valueB;

          if (key === "progress") {

            valueA = Number(
              rowA.dataset.progress || 0
            );

            valueB = Number(
              rowB.dataset.progress || 0
            );

          } else if (key === "close") {

            valueA = (
              rowA.dataset.close || ""
            );

            valueB = (
              rowB.dataset.close || ""
            );

          } else {

            valueA = normalize(
              rowA.dataset[key]
            );

            valueB = normalize(
              rowB.dataset[key]
            );
          }

          if (valueA < valueB) {
            return -1 * sortDirection;
          }

          if (valueA > valueB) {
            return 1 * sortDirection;
          }

          return 0;
        }
      );


      rows.forEach(
        function (row) {
          tableBody.appendChild(
            row
          );
        }
      );

      applyFilters();
    }


    document.querySelectorAll(
      ".ial-sort-button"
    ).forEach(
      function (button) {

        button.addEventListener(
          "click",
          function () {

            sortRows(
              button.dataset.sort
            );

          }
        );

      }
    );


    function escapeCsvCell(value) {

      const text = String(
        value || ""
      ).replace(
        /"/g,
        '""'
      );

      return '"' + text + '"';
    }


    function exportVisibleRows() {

      const rows = getVisibleRows();

      if (!rows.length) {

        window.alert(
          "No hay auditorías visibles para exportar."
        );

        return;
      }

      const headers = [
        "ID",
        "Proceso / Área",
        "Cliente",
        "Estado",
        "Riesgo",
        "Auditor asignado",
        "Avance",
        "Cierre estimado",
      ];

      const csvRows = [
        headers
          .map(escapeCsvCell)
          .join(";"),
      ];

      rows.forEach(
        function (row) {

          const values = [
            row.dataset.code,
            row.dataset.process,
            row.dataset.client,
            row.dataset.statusLabel,
            row.dataset.riskLabel,
            row.dataset.auditor,
            (
              row.dataset.progress
              + "%"
            ),
            row.dataset.close,
          ];

          csvRows.push(
            values
              .map(escapeCsvCell)
              .join(";")
          );

        }
      );


      const content = (
        "\uFEFF"
        + csvRows.join("\r\n")
      );

      const blob = new Blob(
        [content],
        {
          type: (
            "text/csv;charset=utf-8;"
          ),
        }
      );

      const url = (
        URL.createObjectURL(blob)
      );

      const today = new Date();

      const dateString = [
        today.getFullYear(),

        String(
          today.getMonth() + 1
        ).padStart(2, "0"),

        String(
          today.getDate()
        ).padStart(2, "0"),

      ].join("-");


      const link = (
        document.createElement("a")
      );

      link.href = url;

      link.download = (
        "auditorias-internas-"
        + dateString
        + ".csv"
      );

      document.body.appendChild(
        link
      );

      link.click();

      link.remove();

      URL.revokeObjectURL(
        url
      );
    }


    if (exportButton) {

      exportButton.addEventListener(
        "click",
        exportVisibleRows
      );

    }


    getRows().forEach(syncRow);
    applyFilters();

  }
);