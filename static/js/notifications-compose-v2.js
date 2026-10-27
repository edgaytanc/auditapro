(function () {
  "use strict";

  const data = window.AUDITA_NOTIFICATION_DATA || { audits: [], notifieds: [] };
  const audits = Array.isArray(data.audits) ? data.audits : [];
  const notifieds = Array.isArray(data.notifieds) ? data.notifieds : [];

  const auditSelect = document.getElementById("audit_id");
  const notifiedsSelect = $("#notifieds_users");
  const form = document.getElementById("notificationCreateForm");
  const preview = document.getElementById("recipientPreviewValue");
  const fileInput = document.getElementById("archivos");
  const fileList = document.getElementById("archivosLista");
  const principalMailButton = document.getElementById("btnPrincipalCorreo");
  const currentUser = data.currentUser || "AuditaPro";
  const currentEmail = data.currentEmail || "";

  if (!auditSelect || !form || !notifiedsSelect.length) return;

  function userLabel(user) {
    const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
    return `${name || user.username || "Usuario"} - ${user.role?.verbose_name || user.role?.name || ""}`;
  }

  function selectedUsers() {
    const ids = notifiedsSelect.val() || [];
    return notifieds.filter((user) => ids.map(String).includes(String(user.id)));
  }

  function refreshPreview() {
    const users = selectedUsers();
    if (!users.length) {
      preview.textContent = "Selecciona una auditoría y uno o más destinatarios.";
      return;
    }

    preview.textContent = users
      .map((user) => user.email ? `${userLabel(user)} · ${user.email}` : userLabel(user))
      .join(" · ");
  }

  function initSelect2() {
    if ($.fn.select2 && notifiedsSelect.hasClass("select2-hidden-accessible")) {
      notifiedsSelect.select2("destroy");
    }

    if ($.fn.select2) {
      notifiedsSelect.select2({
        width: "100%",
        placeholder: "Usuarios que serán notificados",
        allowClear: true,
        closeOnSelect: false,
        language: {
          noResults: function () { return "No hay usuarios disponibles"; }
        }
      });
    }
  }

  function updateRecipients(auditId) {
    notifiedsSelect.empty();
    const audit = audits.find((item) => String(item.id) === String(auditId));

    if (!audit) {
      initSelect2();
      refreshPreview();
      return;
    }

    const assignedIds = (audit.assigned_users || []).map((user) => String(user.id));
    if (audit.audit_manager?.id != null) assignedIds.push(String(audit.audit_manager.id));

    notifieds.forEach((user) => {
      if (!assignedIds.includes(String(user.id))) return;

      const option = new Option(userLabel(user), user.id, false, false);
      option.dataset.email = user.email || "";
      notifiedsSelect.append(option);
    });

    initSelect2();
    refreshPreview();
  }

  function getSelectedAuditText() {
    return $(auditSelect).find("option:selected").text().trim() || "Auditoría";
  }

  function getRecipientEmails() {
    return selectedUsers()
      .map((user) => user.email)
      .filter(Boolean);
  }

  function getRecipientNames() {
    return selectedUsers()
      .map((user) => `${user.first_name || ""} ${user.last_name || ""}`.trim())
      .filter(Boolean);
  }

  function buildSubject() {
    return `Comunicación AuditaPro — ${getSelectedAuditText()}`;
  }

  function buildBody() {
    const note = document.getElementById("note")?.value.trim() || "";
    const names = getRecipientNames().join(", ");
    const files = Array.from(fileInput?.files || []).map((file) => `• ${file.name}`).join("\n");

    return [
      names ? `Estimado/a ${names},` : "Estimado/a,",
      "",
      `En relación con la auditoría ${getSelectedAuditText()}, comparto la siguiente comunicación:`,
      "",
      note || "(Sin nota adicional)",
      "",
      "Archivos seleccionados para adjuntar:",
      files || "• No se seleccionaron archivos",
      "",
      `Saludos,\n${currentUser}`
    ].join("\n");
  }

  function ensureRecipients() {
    const emails = getRecipientEmails();
    if (!emails.length) {
      window.alert("Selecciona al menos un destinatario antes de preparar el correo.");
      return false;
    }
    return true;
  }

  function openMailto() {
    if (!ensureRecipients()) return;
    const to = getRecipientEmails().join(",");
    const url = `mailto:${to}?subject=${encodeURIComponent(buildSubject())}&body=${encodeURIComponent(buildBody())}`;
    window.location.href = url;
  }

  function openGmail() {
    if (!ensureRecipients()) return;
    const to = getRecipientEmails().join(",");
    const url = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}&su=${encodeURIComponent(buildSubject())}&body=${encodeURIComponent(buildBody())}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function openOutlook() {
    if (!ensureRecipients()) return;
    const to = getRecipientEmails().join(";");
    const url = `https://outlook.office.com/mail/deeplink/compose?to=${encodeURIComponent(to)}&subject=${encodeURIComponent(buildSubject())}&body=${encodeURIComponent(buildBody())}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function configurePrimaryMailButton() {
    if (!principalMailButton) return;

    const email = currentEmail.toLowerCase();
    if (email.endsWith("@gmail.com") || email.includes("@google")) {
      principalMailButton.innerHTML = '<i class="bi bi-google"></i> Preparar en Gmail';
      principalMailButton.dataset.provider = "gmail";
    } else if (email.includes("@outlook") || email.includes("@hotmail") || email.includes("@office")) {
      principalMailButton.innerHTML = '<i class="bi bi-microsoft"></i> Preparar en Outlook';
      principalMailButton.dataset.provider = "outlook";
    } else {
      principalMailButton.innerHTML = '<i class="bi bi-envelope"></i> Abrir cliente de correo';
      principalMailButton.dataset.provider = "mailto";
    }
  }

  auditSelect.addEventListener("change", (event) => {
    updateRecipients(event.target.value);
  });

  notifiedsSelect.on("change", refreshPreview);

  fileInput?.addEventListener("change", () => {
    if (!fileList) return;
    fileList.innerHTML = "";

    Array.from(fileInput.files || []).forEach((file) => {
      const item = document.createElement("li");
      item.innerHTML = '<i class="bi bi-file-earmark"></i><span></span>';
      item.querySelector("span").textContent = `${file.name} · ${Math.max(1, Math.round(file.size / 1024))} KB`;
      fileList.appendChild(item);
    });
  });

  principalMailButton?.addEventListener("click", () => {
    const provider = principalMailButton.dataset.provider;
    if (provider === "gmail") openGmail();
    else if (provider === "outlook") openOutlook();
    else openMailto();
  });

  document.getElementById("btnGmail")?.addEventListener("click", openGmail);
  document.getElementById("btnOutlookWeb")?.addEventListener("click", openOutlook);
  document.getElementById("btnMailto")?.addEventListener("click", openMailto);

  form.addEventListener("submit", (event) => {
    if (!auditSelect.value) {
      event.preventDefault();
      window.alert("Selecciona la auditoría relacionada.");
      return;
    }

    if (!(notifiedsSelect.val() || []).length) {
      event.preventDefault();
      window.alert("Selecciona al menos un destinatario.");
    }
  });

  configurePrimaryMailButton();
  initSelect2();
})();
