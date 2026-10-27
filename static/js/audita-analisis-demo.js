/* Audita Análisis - respuestas solo en DOM, sin localStorage ni historial en servidor. */
(() => {
  "use strict";
  function iniciar() {
    const root = document.getElementById("auditaAnalisisDemo");
    const form = document.getElementById("aaDemoForm");
    const input = document.getElementById("aaDemoQuestion");
    const files = document.getElementById("aaFiles");
    const send = document.getElementById("aaDemoSend");
    const feedback = document.getElementById("aaDemoFeedback");
    const remaining = document.getElementById("aaRemaining");
    const used = document.getElementById("aaUsed");
    const history = document.getElementById("aaDemoHistory");
    const empty = document.getElementById("aaDemoEmpty");
    if (!root || !form || !input || !send || !feedback || !remaining || !history) return;

    let busy = false;
    const status = (message, error = false) => {
      feedback.textContent = message;
      feedback.classList.toggle("aa-error", error);
      feedback.classList.toggle("aa-success", !error);
    };
    const setBalance = (cantidad) => {
      remaining.textContent = String(cantidad);
      root.dataset.restantes = String(cantidad);
      if (Number(cantidad) <= 0) {
        send.disabled = true;
        input.disabled = true;

        status("No quedan consultas. Pide al superadministrador una recarga.", true);
      }
    };
    const bloquear = (valor) => {
      busy = valor;
      send.disabled = valor || Number(root.dataset.restantes) <= 0;
      input.readOnly = valor;

    };
    const agregarResultado = (pregunta, respuesta) => {
      if (empty) empty.remove();
      const item = document.createElement("div"); item.className = "aa-history-item";
      const q = document.createElement("div"); q.className = "aa-history-question";
      q.textContent = pregunta;
      const a = document.createElement("div"); a.className = "aa-history-reply";
      a.textContent = respuesta;
      item.append(q, a); history.prepend(item);
    };

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy) return;
      const question = input.value.trim();
      if (!question || question.length > 1800) {
        status("Escribe una pregunta de hasta 1800 caracteres.", true); return;
      }
      bloquear(true);
      status("Procesando tu consulta…");
      try {
        const payload = new FormData(form);
        // El input externo tiene form="aaDemoForm": FormData(form) ya lo incluye.
        const response = await fetch(root.dataset.url, {
          method: "POST", body: payload, credentials: "same-origin",
          headers: {"X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value, "Accept": "application/json"}
        });
        let result = {};
        try { result = await response.json(); } catch (_) { /* no response JSON */ }
        if (typeof result.restantes === "number") setBalance(result.restantes);
        if (!response.ok) { status(result.error || "No fue posible completar la consulta.", true); return; }
        agregarResultado(question, result.respuesta || "Sin respuesta.");
        if (typeof result.realizadas === "number" && used) used.textContent = String(result.realizadas);
        input.value = "";
        if (Number(root.dataset.restantes) > 0) status("Consulta completada.");
      } catch (_) {
        status("Error de conexión. Si se descontó un cupo, recarga la página para consultar el saldo real.", true);
      } finally {
        bloquear(false);
        if (Number(root.dataset.restantes) > 0) input.focus();
      }
    });
    if (Number(root.dataset.restantes) <= 0) setBalance(0);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar, {once:true});
  else iniciar();
})();
