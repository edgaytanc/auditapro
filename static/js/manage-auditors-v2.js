document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("auditorSearch");
  const statusFilter = document.getElementById(
    "auditorStatusFilter"
  );
  const cards = Array.from(
    document.querySelectorAll("[data-auditor-card]")
  );
  const resultsCount = document.getElementById(
    "auditorResultsCount"
  );
  const noResults = document.getElementById(
    "auditorsNoResults"
  );

  if (!cards.length) {
    return;
  }

  function normalizeText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function applyFilters() {
    const searchValue = normalizeText(
      searchInput ? searchInput.value : ""
    );

    const selectedStatus = statusFilter
      ? statusFilter.value
      : "all";

    let visibleCards = 0;

    cards.forEach(function (card) {
      const cardSearchText = normalizeText(
        card.dataset.search
      );

      const cardStatus = card.dataset.status || "";

      const matchesSearch =
        !searchValue ||
        cardSearchText.includes(searchValue);

      const matchesStatus =
        selectedStatus === "all" ||
        cardStatus === selectedStatus;

      const shouldShow =
        matchesSearch && matchesStatus;

      card.hidden = !shouldShow;

      if (shouldShow) {
        visibleCards += 1;
      }
    });

    if (resultsCount) {
      resultsCount.textContent = String(visibleCards);
    }

    if (noResults) {
      noResults.hidden = visibleCards !== 0;
    }
  }

  if (searchInput) {
    searchInput.addEventListener(
      "input",
      applyFilters
    );
  }

  if (statusFilter) {
    statusFilter.addEventListener(
      "change",
      applyFilters
    );
  }

  applyFilters();
});