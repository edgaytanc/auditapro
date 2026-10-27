document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById(
    "toolsSearch"
  );

  const resultsCount = document.getElementById(
    "toolsResultsCount"
  );

  const emptyState = document.getElementById(
    "toolsEmptyState"
  );

  const cards = Array.from(
    document.querySelectorAll("[data-tool-card]")
  );

  const guideButton = document.getElementById(
    "toolsGuideButton"
  );

  const guideModal = document.getElementById(
    "toolsGuideModal"
  );

  const guideCloseButtons = document.querySelectorAll(
    "[data-close-tools-guide]"
  );

  function normalizeText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function applySearch() {
    const searchValue = normalizeText(
      searchInput ? searchInput.value : ""
    );

    let visibleCards = 0;

    cards.forEach(function (card) {
      const searchContent = normalizeText(
        card.dataset.search
      );

      const shouldShow =
        !searchValue ||
        searchContent.includes(searchValue);

      card.hidden = !shouldShow;

      if (shouldShow) {
        visibleCards += 1;
      }
    });

    if (resultsCount) {
      resultsCount.textContent = String(
        visibleCards
      );
    }

    if (emptyState) {
      emptyState.hidden = visibleCards !== 0;
    }
  }

  function openGuide() {
    if (!guideModal) {
      return;
    }

    guideModal.hidden = false;
    document.body.classList.add(
      "ap-tools-modal-open"
    );
  }

  function closeGuide() {
    if (!guideModal) {
      return;
    }

    guideModal.hidden = true;
    document.body.classList.remove(
      "ap-tools-modal-open"
    );
  }

  if (searchInput) {
    searchInput.addEventListener(
      "input",
      applySearch
    );
  }

  if (guideButton) {
    guideButton.addEventListener(
      "click",
      openGuide
    );
  }

  guideCloseButtons.forEach(function (button) {
    button.addEventListener(
      "click",
      closeGuide
    );
  });

  document.addEventListener(
    "keydown",
    function (event) {
      if (
        event.key === "Escape" &&
        guideModal &&
        !guideModal.hidden
      ) {
        closeGuide();
      }
    }
  );

  applySearch();
});
