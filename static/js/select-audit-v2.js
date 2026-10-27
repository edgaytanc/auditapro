document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById(
    "selectAuditForm"
  );

  const searchInput = document.getElementById(
    "selectAuditSearch"
  );

  const options = Array.from(
    document.querySelectorAll(
      "[data-select-audit-option]"
    )
  );

  const submitButton = document.getElementById(
    "selectAuditSubmit"
  );

  const selectedMessage = document.getElementById(
    "selectedAuditMessage"
  );

  const noResults = document.getElementById(
    "selectAuditNoResults"
  );

  function normalizeText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function updateSelection() {
    const selectedInput = document.querySelector(
      'input[name="audit"]:checked'
    );

    if (submitButton) {
      submitButton.disabled = !selectedInput;
    }

    if (selectedMessage) {
      selectedMessage.textContent = selectedInput
        ? "Auditoría seleccionada. Puedes continuar."
        : "Selecciona una auditoría para continuar.";
    }
  }

  function applySearch() {
    const searchValue = normalizeText(
      searchInput ? searchInput.value : ""
    );

    let visibleOptions = 0;

    options.forEach(function (option) {
      const searchContent = normalizeText(
        option.dataset.search
      );

      const shouldShow =
        !searchValue ||
        searchContent.includes(searchValue);

      option.hidden = !shouldShow;

      if (shouldShow) {
        visibleOptions += 1;
      }
    });

    if (noResults) {
      noResults.hidden = visibleOptions !== 0;
    }
  }

  options.forEach(function (option) {
    const radio = option.querySelector(
      'input[name="audit"]'
    );

    if (radio) {
      radio.addEventListener(
        "change",
        updateSelection
      );
    }
  });

  if (searchInput) {
    searchInput.addEventListener(
      "input",
      applySearch
    );
  }

  if (form && submitButton) {
    form.addEventListener("submit", function () {
      submitButton.disabled = true;

      submitButton.innerHTML =
        '<span class="spinner-border ' +
        'spinner-border-sm"></span>' +
        " Abriendo...";
    });
  }

  updateSelection();
  applySearch();
});