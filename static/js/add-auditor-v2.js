document.addEventListener("DOMContentLoaded", function () {
  const passwordToggles = document.querySelectorAll(
    "[data-password-toggle]"
  );

  const passwordOne = document.getElementById("id_password1");
  const passwordTwo = document.getElementById("id_password2");
  const passwordMessage = document.getElementById(
    "passwordMatchMessage"
  );

  const emailInput = document.getElementById("id_email");
  const usernameInput = document.getElementById("id_username");

  const form = document.getElementById("newAuditorForm");
  const submitButton = document.getElementById(
    "createAuditorButton"
  );

  const roleSelect = document.getElementById(
    "auditorSystemRole"
  );

  const roleTitle = document.getElementById(
    "auditorRoleTitle"
  );

  const roleDescription = document.getElementById(
    "auditorRoleDescription"
  );

  let usernameWasEdited = Boolean(
    usernameInput && usernameInput.value.trim()
  );

  passwordToggles.forEach(function (button) {
    button.addEventListener("click", function () {
      const inputId = button.dataset.passwordToggle;
      const passwordInput = document.getElementById(inputId);
      const icon = button.querySelector("i");

      if (!passwordInput) {
        return;
      }

      const shouldShow = passwordInput.type === "password";

      passwordInput.type = shouldShow ? "text" : "password";

      button.setAttribute(
        "aria-label",
        shouldShow
          ? "Ocultar contraseña"
          : "Mostrar contraseña"
      );

      button.setAttribute(
        "title",
        shouldShow
          ? "Ocultar contraseña"
          : "Mostrar contraseña"
      );

      if (icon) {
        icon.className = shouldShow
          ? "bi bi-eye-slash"
          : "bi bi-eye";
      }
    });
  });

  function validatePasswordMatch() {
    if (
      !passwordOne ||
      !passwordTwo ||
      !passwordMessage
    ) {
      return;
    }

    const firstValue = passwordOne.value;
    const secondValue = passwordTwo.value;

    passwordMessage.classList.remove(
      "ap-password-match-success",
      "ap-password-match-error"
    );

    if (!secondValue) {
      passwordMessage.textContent = "";
      return;
    }

    if (firstValue === secondValue) {
      passwordMessage.textContent =
        "Las contraseñas coinciden.";

      passwordMessage.classList.add(
        "ap-password-match-success"
      );

      return;
    }

    passwordMessage.textContent =
      "Las contraseñas todavía no coinciden.";

    passwordMessage.classList.add(
      "ap-password-match-error"
    );
  }

  function buildUsernameFromEmail(email) {
    const localPart = String(email || "")
      .split("@")[0]
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9._-]/g, "")
      .toLowerCase();

    return localPart.substring(0, 150);
  }

  if (usernameInput) {
    usernameInput.addEventListener("input", function () {
      usernameWasEdited = Boolean(
        usernameInput.value.trim()
      );
    });
  }

  if (emailInput && usernameInput) {
    emailInput.addEventListener("input", function () {
      if (usernameWasEdited) {
        return;
      }

      usernameInput.value = buildUsernameFromEmail(
        emailInput.value
      );
    });
  }

  if (passwordOne) {
    passwordOne.addEventListener(
      "input",
      validatePasswordMatch
    );
  }

  if (passwordTwo) {
    passwordTwo.addEventListener(
      "input",
      validatePasswordMatch
    );
  }


  const roleInformation = {
  audit_manager: {
    title: "Jefe",
    description:
      "Delega funciones al Supervisor y a los Auditores, " +
      "administra el equipo y recibe los informes de trabajo."
  },

  auditor: {
    title: "Auditor",
    description:
      "Puede trabajar en auditorías, papeles de trabajo, " +
      "hallazgos y reportes según los permisos asignados."
  },

  supervisor: {
    title: "Supervisor",
    description:
      "Revisa papeles de trabajo, hallazgos, reportes y " +
      "el avance de las auditorías asignadas."
  },

  readonly: {
    title: "Solo Lectura",
    description:
      "Puede consultar la información existente, pero no " +
      "puede crear, editar ni eliminar registros."
  }
};

function updateRolePreview() {
  if (!roleSelect || !roleTitle || !roleDescription) {
    return;
  }

  const selectedRole =
    roleInformation[roleSelect.value] ||
    roleInformation.auditor;

  roleTitle.textContent = selectedRole.title;
  roleDescription.textContent =
    selectedRole.description;
}

if (roleSelect) {
  roleSelect.addEventListener(
    "change",
    updateRolePreview
  );

  updateRolePreview();
}

  if (form && submitButton) {
    form.addEventListener("submit", function () {
      submitButton.disabled = true;

      submitButton.innerHTML =
        '<span class="spinner-border spinner-border-sm" ' +
        'aria-hidden="true"></span>' +
        " Creando auditor...";
    });
  }
});