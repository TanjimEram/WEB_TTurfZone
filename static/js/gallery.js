/* Gallery lightbox (M7.2): keyboard (arrows + Esc), swipe, close on click-out.
   Works on today's .ph placeholder blocks unchanged; the same markup and
   this same script carry over once real <img> photos replace them (M7.1). */
(function () {
  "use strict";

  var triggers = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox-item]"));
  var overlay = document.querySelector("[data-lightbox-overlay]");
  if (!triggers.length || !overlay) return;

  var stage = overlay.querySelector("[data-lightbox-stage]");
  var closeBtn = overlay.querySelector("[data-lightbox-close]");
  var prevBtn = overlay.querySelector("[data-lightbox-prev]");
  var nextBtn = overlay.querySelector("[data-lightbox-next]");
  var index = 0;
  var lastFocused = null;
  var touchStartX = null;

  function show(i) {
    index = (i + triggers.length) % triggers.length;
    stage.innerHTML = "";
    var content = triggers[index].querySelector(".ph");
    if (content) stage.appendChild(content.cloneNode(true));
  }

  function open(i) {
    lastFocused = document.activeElement;
    show(i);
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    closeBtn.focus();
  }

  function close() {
    overlay.hidden = true;
    document.body.style.overflow = "";
    if (lastFocused) lastFocused.focus();
  }

  triggers.forEach(function (trigger, i) {
    trigger.addEventListener("click", function () {
      open(i);
    });
  });

  closeBtn.addEventListener("click", close);
  prevBtn.addEventListener("click", function () {
    show(index - 1);
  });
  nextBtn.addEventListener("click", function () {
    show(index + 1);
  });

  overlay.addEventListener("click", function (event) {
    if (event.target === overlay) close();
  });

  document.addEventListener("keydown", function (event) {
    if (overlay.hidden) return;
    if (event.key === "Escape") close();
    else if (event.key === "ArrowLeft") show(index - 1);
    else if (event.key === "ArrowRight") show(index + 1);
  });

  overlay.addEventListener(
    "touchstart",
    function (event) {
      touchStartX = event.touches[0].clientX;
    },
    { passive: true }
  );

  overlay.addEventListener(
    "touchend",
    function (event) {
      if (touchStartX === null) return;
      var delta = event.changedTouches[0].clientX - touchStartX;
      if (Math.abs(delta) > 40) show(delta > 0 ? index - 1 : index + 1);
      touchStartX = null;
    },
    { passive: true }
  );
})();
