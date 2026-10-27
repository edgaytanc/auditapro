(function () {
  "use strict";

  const templates = {
    auditor: {
      audits: [
        "view",
        "create",
        "edit"
      ],
      clients: [
        "view",
        "create",
        "edit"
      ],
      workpapers: [
        "view",
        "create",
        "edit"
      ],
      findings: [
        "view",
        "create",
        "edit"
      ],
      reports: [
        "view",
        "create"
      ],
      users: []
    },

    supervisor: {
      audits: [
        "view"
      ],
      clients: [
        "view"
      ],
      workpapers: [
        "view",
        "edit"
      ],
      findings: [
        "view",
        "edit"
      ],
      reports: [
        "view",
        "edit"
      ],
      users: []
    },

    readonly: {
      audits: [
        "view"
      ],
      clients: [
        "view"
      ],
      workpapers: [
        "view"
      ],
      findings: [
        "view"
      ],
      reports: [
        "view"
      ],
      users: []
    }
  };

  const roleLabels = {
    auditor: "Auditor",
    supervisor: "Supervisor",
    readonly: "Solo Lectura"
  };

  const roleSelector = document.getElementById(
    "permissionRoleSelector"
  );

  const templateSelector = document.getElementById(
    "permissionTemplateSelector"
  );

  const applyButton = document.getElementById(
    "applyPermissionTemplateButton"
  );

  const notice = document.getElementById(
    "permissionTemplateNotice"
  );

  const noticeText = document.getElementById(
    "permissionTemplateNoticeText"
  );

  function applyTemplate(templateName) {
    const selectedTemplate =
      templates[templateName];

    if (!selectedTemplate) {
      return;
    }

    document
      .querySelectorAll(
        "#permissionMatrixBody tr"
      )
      .forEach(function (row) {
        const moduleName =
          row.dataset.module;

        const allowedActions =
          selectedTemplate[moduleName] || [];

        row
          .querySelectorAll(
            ".permission-checkbox"
          )
          .forEach(function (checkbox) {
            const action =
              checkbox.dataset.action;

            checkbox.checked =
              allowedActions.includes(action);

            const cell =
              checkbox.closest("td");

            if (!cell) {
              return;
            }

            cell.classList.add(
              "permission-just-set"
            );

            window.setTimeout(
              function () {
                cell.classList.remove(
                  "permission-just-set"
                );
              },
              500
            );
          });
      });

    if (notice && noticeText) {
      noticeText.textContent =
        "Matriz llenada automáticamente con la plantilla \"" +
        roleLabels[templateName] +
        "\".";

      notice.classList.remove("show");

      void notice.offsetWidth;

      notice.classList.add("show");
    }
  }

  if (roleSelector) {
    roleSelector.addEventListener(
      "change",
      function () {
        const matrixUrl =
          roleSelector.dataset.matrixUrl;

        if (!matrixUrl) {
          return;
        }

        window.location.href =
          matrixUrl +
          "?role=" +
          encodeURIComponent(
            roleSelector.value
          );
      }
    );
  }

  if (applyButton && templateSelector) {
    applyButton.addEventListener(
      "click",
      function () {
        applyTemplate(
          templateSelector.value
        );
      }
    );
  }

  if (
    templateSelector &&
    roleSelector &&
    templates[roleSelector.value]
  ) {
    templateSelector.value =
      roleSelector.value;
  }
})();