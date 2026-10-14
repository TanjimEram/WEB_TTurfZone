/* Admin settings (M7.7): add / remove / reorder price bands, keep the band
   checkboxes labelled with the slot times being typed, and refresh the
   price preview from the server (the same resolver the public site uses).
   Without JS the form still works: one blank band row, a "Preview prices" button. */
(function () {
  "use strict";

  var form = document.querySelector("[data-settings-form]");
  if (!form) return;
  var list = form.querySelector("[data-bands]");
  var template = document.querySelector("[data-band-template]");
  var addButton = form.querySelector("[data-band-add]");
  var preview = form.querySelector("[data-preview]");
  var previewUrl = form.getAttribute("data-preview-url");
  var maxBands = parseInt(form.getAttribute("data-max-bands"), 10) || 10;
  var timer = null;

  form.querySelectorAll("[data-js-only]").forEach(function (el) {
    el.hidden = false;
  });

  function rows() {
    return Array.prototype.slice.call(list.querySelectorAll("[data-band]"));
  }

  // band-3-label -> band-0-label (and err-band-3 -> err-band-0) after a move/add/remove
  function renumber() {
    rows().forEach(function (row, k) {
      row.querySelectorAll("[name], [id], [for], [aria-describedby]").forEach(function (el) {
        ["name", "id", "for", "aria-describedby"].forEach(function (attr) {
          var value = el.getAttribute(attr);
          if (value) el.setAttribute(attr, value.replace(/(^|err-)band-[^-\s]+/, "$1band-" + k));
        });
      });
      var legend = row.querySelector("legend");
      if (legend) legend.textContent = "Price " + (k + 1);
      var slots = row.querySelector("[data-band-slots]");
      if (slots) slots.setAttribute("aria-label", "Slots for price " + (k + 1));
    });
    if (addButton) addButton.disabled = rows().length >= maxBands;
    schedulePreview();
  }

  list.addEventListener("click", function (event) {
    var button = event.target.closest("[data-band-up], [data-band-down], [data-band-remove]");
    if (!button) return;
    var row = button.closest("[data-band]");
    if (button.hasAttribute("data-band-up") && row.previousElementSibling) {
      list.insertBefore(row, row.previousElementSibling);
    } else if (button.hasAttribute("data-band-down") && row.nextElementSibling) {
      list.insertBefore(row.nextElementSibling, row);
    } else if (button.hasAttribute("data-band-remove")) {
      row.remove();
      renumber();
      if (addButton) addButton.focus();
      return;
    }
    renumber();
    button.focus(); // moving the row in the DOM can drop focus
  });

  if (addButton) {
    addButton.addEventListener("click", function () {
      if (rows().length >= maxBands) return;
      var row = template.content.firstElementChild.cloneNode(true);
      row.querySelectorAll("[data-js-only]").forEach(function (el) {
        el.hidden = false;
      });
      list.appendChild(row);
      renumber();
      syncSlotNames();
      var first = row.querySelector("input");
      if (first) first.focus();
    });
  }

  // "18:00" -> "06:00 PM", matching the server's slot labels
  function label12(value) {
    var m = /^(\d{2}):(\d{2})/.exec(value || "");
    if (!m) return value || "";
    var h = parseInt(m[1], 10);
    var h12 = h % 12 || 12;
    return (h12 < 10 ? "0" : "") + h12 + ":" + m[2] + (h < 12 ? " AM" : " PM");
  }

  function syncSlotNames() {
    form.querySelectorAll("[data-slot-input]").forEach(function (input) {
      var i = input.getAttribute("data-slot-input");
      document.querySelectorAll('[data-slot-name="' + i + '"]').forEach(function (span) {
        span.textContent = label12(input.value);
      });
    });
  }

  function schedulePreview() {
    if (!preview || !previewUrl || !window.fetch) return;
    clearTimeout(timer);
    timer = setTimeout(function () {
      var data = new FormData(form);
      data.delete("action");
      fetch(previewUrl, { method: "POST", body: data, credentials: "same-origin" })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.text();
        })
        .then(function (html) {
          preview.innerHTML = html;
        })
        .catch(function () {
          /* keep the last preview; "Preview prices" still works */
        });
    }, 350);
  }

  form.addEventListener("input", function (event) {
    if (event.target.hasAttribute("data-slot-input")) syncSlotNames();
    schedulePreview();
  });
  form.addEventListener("change", schedulePreview);

  if (addButton) addButton.disabled = rows().length >= maxBands;
})();
