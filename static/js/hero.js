/* Hero slideshow (CR-11). The first slide is visible without JS; this rotates the
   others every 6 s, pauses while the pointer or focus is on the hero, and never
   runs when the visitor asks for reduced motion. Dots jump to a slide. */
(function () {
  "use strict";
  var hero = document.querySelector("[data-hero]");
  if (!hero) return;
  var slides = Array.prototype.slice.call(hero.querySelectorAll("[data-hero-slide]"));
  var dots = Array.prototype.slice.call(hero.querySelectorAll("[data-hero-dot]"));
  if (slides.length < 2) return;

  var current = 0;
  var timer = null;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function show(index) {
    current = (index + slides.length) % slides.length;
    slides.forEach(function (slide, i) {
      var on = i === current;
      slide.classList.toggle("is-active", on);
      if (on) {
        slide.removeAttribute("aria-hidden");
        var pic = slide.querySelector("img");
        if (pic) pic.loading = "eager";  // fetch it now that it is on screen
      } else {
        slide.setAttribute("aria-hidden", "true");
      }
    });
    dots.forEach(function (dot, i) { dot.setAttribute("aria-current", i === current ? "true" : "false"); });
  }

  function start() { if (!reduce && !timer) timer = window.setInterval(function () { show(current + 1); }, 6000); }
  function stop() { if (timer) { window.clearInterval(timer); timer = null; } }

  dots.forEach(function (dot, i) {
    dot.addEventListener("click", function () { stop(); show(i); start(); });
  });
  hero.addEventListener("mouseenter", stop);
  hero.addEventListener("mouseleave", start);
  hero.addEventListener("focusin", stop);
  hero.addEventListener("focusout", start);
  document.addEventListener("visibilitychange", function () { if (document.hidden) stop(); else start(); });
  start();
})();
