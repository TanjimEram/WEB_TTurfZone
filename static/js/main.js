/* Public site behaviour (M3.3): header state + mobile menu.
   Smooth scrolling and anchor offset are handled in CSS (scroll-behavior,
   scroll-padding-top), which already respects "reduce motion". */
(function () {
  "use strict";

  // --- header: transparent over the hero, solid once scrolled -------------
  var header = document.querySelector("[data-site-header]");
  var hero = document.querySelector(".hero");

  if (header) {
    // CR-11: transparent only over the homepage hero, and only until the first 40px of scrolling
    function updateHeader() {
      header.classList.toggle("at-top", Boolean(hero) && window.scrollY < 40);
    }

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
  }

  // --- light / dark theme (CR-11) -----------------------------------------
  // The <head> script already applied a saved choice; this button flips and saves it.
  var root = document.documentElement;
  var toggles = Array.prototype.slice.call(document.querySelectorAll("[data-theme-toggle]"));  // header + phone menu
  function isDark() { return root.getAttribute("data-theme") === "dark"; }
  function showTheme() {
    toggles.forEach(function (toggle) {
      toggle.setAttribute("aria-pressed", isDark() ? "true" : "false");
      toggle.setAttribute("aria-label", isDark() ? "Switch to light theme" : "Switch to dark theme");
    });
  }
  showTheme();
  toggles.forEach(function (toggle) {
    toggle.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("tturf-theme", next); } catch (e) { /* private mode: still switches */ }
      showTheme();
    });
  });

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
