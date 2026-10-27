document.addEventListener("DOMContentLoaded", function () {
  const shell = document.getElementById("apShell");
  const sidebarCollapse = document.getElementById("apSidebarCollapse");
  const mobileMenuButton = document.getElementById("apMobileMenuButton");
  const backdrop = document.getElementById("apSidebarBackdrop");

  const sidebarSubmenuButtons = Array.from(
    document.querySelectorAll(
      "[data-sidebar-submenu]"
    )
  );

  if (!shell) {
    return;
  }

  function isMobile() {
    return window.innerWidth <= 992;
  }

  function closeMobileSidebar() {
    shell.classList.remove("ap-mobile-sidebar-open");
  }

  if (sidebarCollapse) {
    sidebarCollapse.addEventListener("click", function () {
      if (isMobile()) {
        closeMobileSidebar();
        return;
      }

      shell.classList.toggle("ap-sidebar-collapsed");
    });
  }

  if (mobileMenuButton) {
    mobileMenuButton.addEventListener("click", function () {
      shell.classList.toggle("ap-mobile-sidebar-open");
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeMobileSidebar);
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeMobileSidebar();
    }
  });

  window.addEventListener("resize", function () {
    if (!isMobile()) {
      closeMobileSidebar();
    }
  });

  sidebarSubmenuButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      const group = button.closest(".ap-nav-group");

      if (!group) {
        return;
      }

      if (
        shell.classList.contains(
          "ap-sidebar-collapsed"
        ) &&
        !isMobile()
      ) {
        shell.classList.remove(
          "ap-sidebar-collapsed"
        );
      }

      document
        .querySelectorAll(".ap-nav-group")
        .forEach(function (otherGroup) {
          if (otherGroup !== group) {
            otherGroup.classList.remove("open");

            const otherButton =
              otherGroup.querySelector(
                "[data-sidebar-submenu]"
              );

            if (otherButton) {
              otherButton.setAttribute(
                "aria-expanded",
                "false"
              );
            }
          }
        });

      const willOpen =
        !group.classList.contains("open");

      group.classList.toggle(
        "open",
        willOpen
      );

      button.setAttribute(
        "aria-expanded",
        String(willOpen)
      );
    });
  });

});