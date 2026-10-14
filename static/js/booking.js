/* Date + slot picker (M4.2, prices M4.7).
   Reads the booking window from server-rendered date chips, fetches
   /api/availability for the chosen date, and shows the 12 slots with their
   prices. No framework. Every picker on the page is wired independently. */
(function () {
  "use strict";

  var SLOT_MINUTES = 90;
  var STATE_TEXT = {
    available: "available",
    pending: "being booked, not available",
    booked: "booked",
    blocked: "unavailable",
    past: "already started",
  };

  function taka(amount) {
    return amount == null ? "On request" : "\u09F3" + amount.toLocaleString("en-US");
  }

  document.querySelectorAll("[data-slotpicker]").forEach(setupPicker);
  setupBookingForm();

  /* M4.3: keep the details form's hidden date/slot in step with the picker,
     and only enable submit once a slot is chosen. */
  function setupBookingForm() {
    var form = document.querySelector("[data-booking-form]");
    if (!form) return;
    var picker = document.querySelector("[data-slotpicker]");
    var dateField = form.querySelector("[data-field-date]");
    var slotField = form.querySelector("[data-field-slot]");
    var submit = form.querySelector("[data-submit]");

    function sync(date, slot) {
      if (dateField) dateField.value = date || "";
      if (slotField) slotField.value = slot || "";
      if (submit) submit.disabled = !(date && slot);
    }

    if (picker) {
      picker.addEventListener("slotpicker:change", function (event) {
        sync(event.detail.date, event.detail.slot);
      });
    }
    sync(dateField && dateField.value, slotField && slotField.value);
  }

  function setupPicker(root) {
    var fallback = root.querySelector("[data-fallback]");
    var ui = root.querySelector("[data-picker-ui]");
    var grid = root.querySelector("[data-slots]");
    var statusLine = root.querySelector("[data-status]");
    var summary = root.querySelector("[data-summary]");
    var continueBtn = root.querySelector("[data-continue]");
    var chips = Array.prototype.slice.call(root.querySelectorAll("[data-date]"));
    var bookUrl = root.getAttribute("data-book-url") || "/book";
    var preselectSlot = root.getAttribute("data-preselect-slot") || "";

    if (!ui || !grid || chips.length === 0) return;

    var selectedDate = null;
    var selectedSlot = null; // the slot object from the API: {time, label, state, price_bdt}
    var requestId = 0; // guards against out-of-order responses

    // Switch from the no-JS fallback to the interactive picker.
    if (fallback) fallback.hidden = true;
    ui.hidden = false;

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        chooseDate(chip);
      });
    });

    if (continueBtn) {
      continueBtn.addEventListener("click", function (event) {
        if (continueBtn.getAttribute("aria-disabled") === "true") {
          event.preventDefault();
        }
      });
    }

    var startChip =
      root.querySelector('[data-date][aria-pressed="true"]') || chips[0];
    chooseDate(startChip);

    function chooseDate(chip) {
      chips.forEach(function (c) {
        c.setAttribute("aria-pressed", c === chip ? "true" : "false");
      });
      selectedDate = chip.getAttribute("data-date");
      selectedSlot = null;
      updateSelection();
      loadSlots(selectedDate);
    }

    function loadSlots(isoDate) {
      var thisRequest = ++requestId;
      showSkeleton();
      setStatus("Loading slots…");

      fetch("/api/availability?date=" + encodeURIComponent(isoDate), {
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          if (thisRequest !== requestId) return; // a newer date was picked
          renderSlots(data.slots || []);
          setStatus("");
        })
        .catch(function () {
          if (thisRequest !== requestId) return;
          grid.innerHTML = "";
          setStatus("Could not load slots.");
          addRetryButton(isoDate);
        });
    }

    function showSkeleton() {
      grid.innerHTML = "";
      for (var i = 0; i < 12; i++) {
        var block = document.createElement("div");
        block.className = "slot slot--skeleton";
        block.setAttribute("aria-hidden", "true");
        grid.appendChild(block);
      }
    }

    function renderSlots(slots) {
      grid.innerHTML = "";
      slots.forEach(function (slot) {
        grid.appendChild(buildSlot(slot));
      });
      if (preselectSlot) {
        var match = grid.querySelector(
          '[data-slot="' + preselectSlot + '"]:not([disabled])'
        );
        if (match) match.click();
        preselectSlot = ""; // only auto-select once
      }
    }

    function buildSlot(slot) {
      var open = slot.state === "available";
      var el = document.createElement("button");
      el.type = "button";
      el.className = "slot slot--" + slot.state;
      el.setAttribute("data-slot", slot.time);
      // time + price only; the state is the card's styling (+ a word for screen readers)
      el.innerHTML =
        '<span class="slot__time">' + slot.label + "</span>" +
        '<span class="slot__price">' + taka(slot.price_bdt) + "</span>" +
        '<span class="sr-only">, ' + (STATE_TEXT[slot.state] || slot.state) + "</span>";

      if (!open) {
        el.disabled = true;
      } else {
        el.addEventListener("click", function () {
          selectedSlot = slot;
          grid.querySelectorAll(".slot").forEach(function (s) {
            s.classList.toggle("slot--selected", s === el);
            if (s.hasAttribute("data-slot") && !s.disabled)
              s.setAttribute("aria-pressed", s === el ? "true" : "false");
          });
          updateSelection();
        });
        el.setAttribute("aria-pressed", "false");
      }
      return el;
    }

    function endLabel(label) {
      // "06:00 PM" + 90 min -> "07:30 PM"
      var m = /^(\d{2}):(\d{2}) (AM|PM)$/.exec(label);
      if (!m) return "";
      var minutes = (parseInt(m[1], 10) % 12 + (m[3] === "PM" ? 12 : 0)) * 60 + parseInt(m[2], 10) + SLOT_MINUTES;
      var h24 = Math.floor(minutes / 60) % 24;
      var h12 = h24 % 12 || 12;
      return (h12 < 10 ? "0" : "") + h12 + ":" + String(minutes % 60).padStart(2, "0") + (h24 < 12 ? " AM" : " PM");
    }

    function updateSelection() {
      var chip = root.querySelector('[data-date][aria-pressed="true"]');
      var dateLabel = chip ? chip.textContent.trim() : selectedDate;

      if (selectedSlot && summary) {
        var end = endLabel(selectedSlot.label);
        summary.innerHTML =
          '<span class="slotpicker__summary-what">' + dateLabel + ", " + selectedSlot.label +
          (end ? " – " + end : "") + "</span>" +
          '<span class="slotpicker__summary-total">' +
          (selectedSlot.price_bdt == null ? "Price on request" : "Total " + taka(selectedSlot.price_bdt)) +
          "</span>";
        summary.hidden = false;
      } else if (summary) {
        summary.hidden = true;
        summary.textContent = "";
      }

      var slotTime = selectedSlot ? selectedSlot.time : null;
      if (continueBtn) {
        if (selectedSlot) {
          continueBtn.href =
            bookUrl +
            "?date=" +
            encodeURIComponent(selectedDate) +
            "&slot=" +
            encodeURIComponent(slotTime);
          continueBtn.removeAttribute("aria-disabled");
        } else {
          continueBtn.href = bookUrl;
          continueBtn.setAttribute("aria-disabled", "true");
        }
      }

      root.dispatchEvent(
        new CustomEvent("slotpicker:change", {
          detail: { date: selectedDate, slot: slotTime },
        })
      );
    }

    function addRetryButton(isoDate) {
      var retry = document.createElement("button");
      retry.type = "button";
      retry.className = "btn btn--ghost";
      retry.textContent = "Try again";
      retry.addEventListener("click", function () {
        loadSlots(isoDate);
      });
      grid.appendChild(retry);
    }

    function setStatus(text) {
      if (statusLine) statusLine.textContent = text;
    }
  }
})();
