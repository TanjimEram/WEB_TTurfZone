/* Scroll reveal (M7.2). Progressive enhancement: .reveal elements are
   already fully visible by default (main.css). Only once this script adds
   `.reveal-on` to <html> and IntersectionObserver is available does content
   fade up as it enters the viewport - and it honours prefers-reduced-motion
   by simply never doing that. */
(function () {
  "use strict";

  var elements = document.querySelectorAll(".reveal");
  if (!elements.length) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion || !("IntersectionObserver" in window)) return;

  document.documentElement.classList.add("reveal-on");

  var observer = new IntersectionObserver(
    function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          obs.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  elements.forEach(function (el) {
    observer.observe(el);
  });
})();
