/* Public site behaviour: header state, mobile menu (M3.3), and two homepage touches (CR-12):
   the night-hours line in the hero and the "One day, 24 hours" list.
   Smooth scrolling and anchor offset are handled in CSS (scroll-behavior,
   scroll-padding-top), which already respects "reduce motion". */
(function () {
  "use strict";

  document.documentElement.classList.add("js");

  // --- header: transparent over the hero, solid once scrolled -------------
  var header = document.querySelector("[data-site-header]");
  var hero = document.querySelector(".hero");

  if (header) {
    // transparent only over the homepage hero, and only until the first 40px of scrolling
    function updateHeader() {
      header.classList.toggle("at-top", Boolean(hero) && window.scrollY < 40);
    }

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
  }

  // --- hero: time until the night hours, in Dhaka time (CR-12) -------------
  var nightLine = document.querySelector("[data-night-line]");
  if (nightLine && window.Intl) {
    function dhakaNow() {
      var parts = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Dhaka", hour: "numeric", minute: "numeric", hour12: false })
        .formatToParts(new Date());
      var get = function (type) { return parseInt(parts.filter(function (p) { return p.type === type; })[0].value, 10); };
      return { hour: get("hour") % 24, minute: get("minute") };
    }
    function showNightLine() {
      var now = dhakaNow();
      if (now.hour >= 18 || now.hour < 6) {
        nightLine.innerHTML = "It's night at the ground: <b>the floodlit hours are on now</b>, until 6 AM.";
        return;
      }
      var left = 18 * 60 - (now.hour * 60 + now.minute);
      nightLine.innerHTML = "Night hours start in <b>" + Math.floor(left / 60) + " h " + (left % 60) + " min</b>, Dhaka time.";
    }
    showNightLine();
    window.setInterval(showNightLine, 30000);
  }

  // --- One day, 24 hours: the row in the middle of the screen is open and shows its photo
  var rows = Array.prototype.slice.call(document.querySelectorAll("[data-day-row]"));
  var dayPics = Array.prototype.slice.call(document.querySelectorAll(".day__img"));
  if (rows.length) {
    function openRow(index) {
      rows.forEach(function (row, i) { row.classList.toggle("is-on", i === index); });
      dayPics.forEach(function (pic, i) { pic.classList.toggle("is-on", i === index); });
    }
    rows.forEach(function (row, i) {
      var button = row.querySelector("button");
      button.addEventListener("click", function () { openRow(i); });
      button.addEventListener("focus", function () { openRow(i); });
      row.addEventListener("mouseenter", function () { openRow(i); });
    });
    if ("IntersectionObserver" in window) {
      var middle = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) { if (entry.isIntersecting) openRow(rows.indexOf(entry.target)); });
      }, { rootMargin: "-48% 0px -48% 0px" });
      rows.forEach(function (row) { middle.observe(row); });
    }
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
