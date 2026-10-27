document.addEventListener("DOMContentLoaded", function () {
  const deleteForms = document.querySelectorAll(
    "[data-delete-time-record]"
  );

  deleteForms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      const appointment =
        form.dataset.appointment ||
        "este nombramiento";

      const confirmed = window.confirm(
        "¿Deseas eliminar el registro " +
        appointment +
        "?\n\nEsta acción no se puede deshacer."
      );

      if (!confirmed) {
        event.preventDefault();
      }
    });
  });
});