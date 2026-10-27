/* Pestañas accesibles, encapsuladas en esta página. */
(function () {
  'use strict';
  const root = document.querySelector('.ap-planes-upgrade');
  if (!root) return;
  const tabs = root.querySelectorAll('[data-tab]');
  const panels = root.querySelectorAll('[data-view]');

  function selectView(name) {
    if (name !== 'individual' && name !== 'grupos') return;
    tabs.forEach(function (tab) {
      const active = tab.dataset.tab === name;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panels.forEach(function (panel) {
      const active = panel.dataset.view === name;
      panel.classList.toggle('active', active);
      panel.hidden = !active;
    });
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () { selectView(tab.dataset.tab); });
    tab.addEventListener('keydown', function (event) {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const selected = tab.dataset.tab === 'individual' ? 'grupos' : 'individual';
      selectView(selected);
      root.querySelector('[data-tab="' + selected + '"]').focus();
    });
  });
  const requested = new URLSearchParams(window.location.search).get('tipo');
  selectView(requested === 'grupos' ? 'grupos' : 'individual');
})();
