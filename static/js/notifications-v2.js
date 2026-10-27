(function () {
  "use strict";

  const page = document.querySelector("[data-notifications-page]");
  if (!page) return;

  function csrfToken() {
    return (
      document.querySelector("[name='csrfmiddlewaretoken']")?.value ||
      document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1] ||
      ""
    );
  }

  function notify(message, type) {
    const box = document.createElement("div");
    box.className = `ap-notif-toast ap-notif-toast-${type || "info"}`;
    box.textContent = message;
    page.appendChild(box);
    window.setTimeout(() => box.remove(), 3200);
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      },
      body: body instanceof URLSearchParams ? body : new URLSearchParams(body),
    });

    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      data = {};
    }

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "No se pudo completar la operación.");
    }

    return data;
  }

  function updateCounters() {
    const cards = Array.from(page.querySelectorAll("[data-notification-card]"));
    const unread = cards.filter((card) => card.dataset.read === "false").length;
    const reviewed = cards.filter((card) => card.dataset.reviewStatus && card.dataset.reviewStatus !== "pending").length;

    page.querySelector("[data-count='total']")?.replaceChildren(document.createTextNode(String(cards.length)));
    page.querySelector("[data-count='unread']")?.replaceChildren(document.createTextNode(String(unread)));
    page.querySelector("[data-count='reviewed']")?.replaceChildren(document.createTextNode(String(reviewed)));
  }

  async function handleDelete(button) {
    const url = button.dataset.url;
    if (!url) return;

    if (!window.confirm("¿Eliminar esta notificación de tu bandeja?")) return;

    button.disabled = true;
    try {
      await postJson(url, {});
      const card = button.closest("[data-notification-card]");
      const modal = document.querySelector(button.dataset.modalSelector || "");
      card?.remove();
      modal?.remove();
      updateCounters();
      if (!page.querySelector("[data-notification-card]")) {
        location.reload();
      }
    } catch (error) {
      button.disabled = false;
      notify(error.message, "danger");
    }
  }

  async function handleCleanup(button) {
    const url = button.dataset.url;
    if (!url) return;

    if (!window.confirm(button.dataset.confirm || "¿Deseas limpiar tus notificaciones?")) return;

    button.disabled = true;
    try {
      const data = await postJson(url, {});
      notify(data.message || "Bandeja actualizada.", "success");
      window.setTimeout(() => window.location.reload(), 650);
    } catch (error) {
      button.disabled = false;
      notify(error.message, "danger");
    }
  }

  async function handleReview(button) {
    const modal = button.closest(".modal");
    const url = button.dataset.url;
    const action = button.dataset.action;
    if (!modal || !url || !action) return;

    const reasonInputs = modal.querySelectorAll("input[data-review-reason]:checked");
    const reasons = Array.from(reasonInputs).map((input) => input.value);
    const comments = modal.querySelector("[data-review-comments]")?.value.trim() || "";

    if (action === "reject" && reasons.length === 0 && !comments) {
      notify("Para rechazar debes indicar al menos un motivo o comentario.", "danger");
      return;
    }

    button.disabled = true;
    const siblingButtons = modal.querySelectorAll("[data-review-action]");
    siblingButtons.forEach((item) => (item.disabled = true));

    const body = new URLSearchParams();
    body.append("action", action);
    body.append("comments", comments);
    reasons.forEach((reason) => body.append("reasons[]", reason));

    try {
      const data = await postJson(url, body);
      notify(`Revisión registrada: ${data.status || "OK"}.`, "success");
      window.setTimeout(() => window.location.reload(), 650);
    } catch (error) {
      siblingButtons.forEach((item) => (item.disabled = false));
      notify(error.message, "danger");
    }
  }

  document.addEventListener("click", (event) => {
    const deleteButton = event.target.closest("[data-delete-notification]");
    if (deleteButton) {
      handleDelete(deleteButton);
      return;
    }

    const cleanupButton = event.target.closest("[data-clean-notifications]");
    if (cleanupButton) {
      handleCleanup(cleanupButton);
      return;
    }

    const reviewButton = event.target.closest("[data-review-action]");
    if (reviewButton) {
      handleReview(reviewButton);
    }
  });

  const search = document.querySelector("[data-notification-search]");
  const cards = () => Array.from(page.querySelectorAll("[data-notification-card]"));

  search?.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;

    cards().forEach((card) => {
      const matches = !query || (card.dataset.search || "").includes(query);
      card.hidden = !matches;
      if (matches) visible += 1;
    });

    const count = page.querySelector("[data-filtered-count]");
    if (count) count.textContent = String(visible);
  });

  updateCounters();
})();
