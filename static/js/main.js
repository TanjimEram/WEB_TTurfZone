/* Public site behaviour (M3.3): header state + mobile menu.
   Smooth scrolling and anchor offset are handled in CSS (scroll-behavior,
   scroll-padding-top), which already respects "reduce motion". */
(function () {
  "use strict";

  // --- header: transparent over the hero, solid once scrolled -------------
  var header = document.querySelector("[data-site-header]");
  var hero = document.querySelector(".hero");

  if (header) {
    var solidAfter = hero ? hero.offsetHeight - 80 : 200;

    function updateHeader() {
      var atTop = window.scrollY < Math.max(solidAfter, 40);
      header.classList.toggle("at-top", atTop);
    }

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
    window.addEventListener("resize", function () {
      solidAfter = hero ? hero.offsetHeight - 80 : 200;
      updateHeader();
    });
  }

  // --- mobile menu -------------------------------------------------------
  var openBtn = document.querySelector("[data-menu-open]");
  var closeBtn = document.querySelector("[data-menu-close]");
  var menu = document.getElementById("nav-menu");

  if (openBtn && closeBtn && menu) {
    function openMenu() {
      menu.hidden = false;
      openBtn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      closeBtn.focus();
    }

    function closeMenu() {
      menu.hidden = true;
      openBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      openBtn.focus();
    }

    openBtn.addEventListener("click", openMenu);
    closeBtn.addEventListener("click", closeMenu);

    menu.querySelectorAll("[data-menu-link]").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !menu.hidden) {
        closeMenu();
      }
    });
  }
})();
