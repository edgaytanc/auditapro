document.addEventListener('DOMContentLoaded', function () {
  const openBtn = document.getElementById('openAuditaIaModal');
  const modal = document.getElementById('auditaIaModal');
  const closeBtn = document.getElementById('closeAuditaIaModal');
  const cancelBtn = document.getElementById('cancelAuditaIaModal');

  if (openBtn && modal) {
    openBtn.addEventListener('click', function (e) {
      e.preventDefault();
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
    });
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', closeModal);
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeModal);
  }

  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        closeModal();
      }
    });
  }

  document.addEventListener('keydown', function (e) {
    if (modal && e.key === 'Escape' && modal.classList.contains('show')) {
      closeModal();
    }
  });
});