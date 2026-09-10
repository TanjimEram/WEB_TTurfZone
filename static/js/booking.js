/* Date + slot picker (M4.2).
   Reads the booking window from server-rendered date chips, fetches
   /api/availability for the chosen date, and shows the 12 slot states.
   No framework. Every picker on the page is wired independently. */
(function () {
  "use strict";

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
    var selectedSlot = null;
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
      el.innerHTML =
        '<span class="slot__time">' +
        slot.label +
        '</span><span class="slot__meta">' +
        metaText(slot) +
        "</span>";

      if (!open) {
        el.disabled = true;
      } else {
        el.addEventListener("click", function () {
          selectedSlot = slot.time;
          grid.querySelectorAll(".slot").forEach(function (s) {
            s.classList.toggle("slot--selected", s === el);
            if (s.hasAttribute("data-slot"))
              s.setAttribute("aria-pressed", s === el ? "true" : "false");
          });
          updateSelection();
        });
        el.setAttribute("aria-pressed", "false");
      }
      return el;
    }

    function metaText(slot) {
      if (slot.state === "available")
        return slot.price_bdt != null ? "৳" + slot.price_bdt : "Select";
      if (slot.state === "past") return "Past";
      if (slot.state === "blocked") return "Unavailable";
      return "Booked";
    }

    function updateSelection() {
      var chip = root.querySelector('[data-date][aria-pressed="true"]');
      var dateLabel = chip ? chip.textContent.trim() : selectedDate;

      if (selectedSlot && summary) {
        var slotEl = grid.querySelector('[data-slot="' + selectedSlot + '"]');
        var slotLabel = slotEl
          ? slotEl.querySelector(".slot__time").textContent
          : selectedSlot;
        summary.textContent = "Selected: " + dateLabel + ", " + slotLabel;
        summary.hidden = false;
      } else if (summary) {
        summary.hidden = true;
        summary.textContent = "";
      }

      if (continueBtn) {
        if (selectedSlot) {
          continueBtn.href =
            bookUrl +
            "?date=" +
            encodeURIComponent(selectedDate) +
            "&slot=" +
            encodeURIComponent(selectedSlot);
          continueBtn.removeAttribute("aria-disabled");
        } else {
          continueBtn.href = bookUrl;
          continueBtn.setAttribute("aria-disabled", "true");
        }
      }

      root.dispatchEvent(
        new CustomEvent("slotpicker:change", {
          detail: { date: selectedDate, slot: selectedSlot },
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
