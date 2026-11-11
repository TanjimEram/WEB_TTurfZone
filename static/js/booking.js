/* Book Your Turf picker (CR-11 reference layout; 24 hourly slots CR-10).

   The date box (‹ date input ›) picks an operating day (06:00 to 06:00). For that day
   /api/availability returns every open hour with its real calendar date, period, state
   and price. The Morning / Afternoon / Night tabs show that period's cards.

   data-mode="link"  (homepage): BOOK NOW opens /book?date=<real date>&slot=HH:MM.
   data-mode="select" (/book):   BOOK NOW selects the slot into the form below and the
                                 "slotpicker:change" event fills its hidden date/slot.
   No framework. Without JS the [data-fallback] link shows instead. */
(function () {
  "use strict";

  var SLOT_MINUTES = 60;
  var BANGLA = "০১২৩৪৫৬৭৮৯";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August",
                     "September", "October", "November", "December"];
  var DAYS_LONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  var BADGE = { available: "Available", pending: "Booked", booked: "Booked", blocked: "Unavailable", past: "Past" };

  function taka(amount) {
    if (amount == null) return "On request";
    return amount.toLocaleString("en-US").replace(/\d/g, function (d) { return BANGLA[d]; }) + "৳";
  }

  function parts(iso) { var p = iso.split("-").map(Number); return { y: p[0], m: p[1], d: p[2] }; }
  function weekday(iso) { var p = parts(iso); return new Date(Date.UTC(p.y, p.m - 1, p.d)).getUTCDay(); }
  function longDate(iso) { var p = parts(iso); return DAYS_LONG[weekday(iso)] + ", " + MONTHS_LONG[p.m - 1] + " " + p.d + ", " + p.y; }
  function shortDate(iso) { var p = parts(iso); return MONTHS[p.m - 1] + " " + p.d + ", " + p.y; }
  function shiftDay(iso, days) {
    var p = parts(iso);
    var d = new Date(Date.UTC(p.y, p.m - 1, p.d + days));
    return d.toISOString().slice(0, 10);
  }
  function plainTime(label) { return label.replace(/^0/, ""); }  // "06:00 AM" -> "6:00 AM"
  function endLabel(label) {
    var m = /^(\d{2}):(\d{2}) (AM|PM)$/.exec(label);
    if (!m) return "";
    var minutes = (parseInt(m[1], 10) % 12 + (m[3] === "PM" ? 12 : 0)) * 60 + parseInt(m[2], 10) + SLOT_MINUTES;
    var h24 = Math.floor(minutes / 60) % 24;
    var h12 = h24 % 12 || 12;
    return h12 + ":" + String(minutes % 60).padStart(2, "0") + (h24 < 12 ? " AM" : " PM");
  }

  var ICON_CAL = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>';
  var ICON_CLOCK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>';

  document.querySelectorAll("[data-slotpicker]").forEach(setupPicker);
  setupBookingForm();

  /* /book: keep the details form's hidden date/slot in step with the picker,
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
      picker.addEventListener("slotpicker:change", function (event) { sync(event.detail.date, event.detail.slot); });
    }
    sync(dateField && dateField.value, slotField && slotField.value);
  }

  function setupPicker(root) {
    var fallback = root.querySelector("[data-fallback]");
    var ui = root.querySelector("[data-picker-ui]");
    var grid = root.querySelector("[data-slots]");
    var input = root.querySelector("[data-day-input]");
    if (!ui || !grid || !input) return;

    var prev = root.querySelector("[data-day-prev]");
    var next = root.querySelector("[data-day-next]");
    var label = root.querySelector("[data-day-label]");
    var countFree = root.querySelector("[data-count-free]");
    var countTaken = root.querySelector("[data-count-taken]");
    var statusLine = root.querySelector("[data-status]");
    var summary = root.querySelector("[data-summary]");
    var tabs = Array.prototype.slice.call(root.querySelectorAll("[role=tab][data-period]"));
    var linkMode = root.getAttribute("data-mode") !== "select";
    var bookUrl = root.getAttribute("data-book-url") || "/book";
    var logo = root.getAttribute("data-logo") || "";
    var brand = root.getAttribute("data-brand") || "";
    var preselect = root.getAttribute("data-preselect-slot") || "";

    var day = input.value || input.min;
    var slots = [];
    var period = tabs.length ? tabs[0].getAttribute("data-period") : "";
    var selected = null;
    var requestId = 0;

    if (fallback) fallback.hidden = true;
    ui.hidden = false;

    input.addEventListener("change", function () {
      if (input.value && input.value >= input.min && input.value <= input.max) chooseDay(input.value);
      else input.value = day;
    });
    if (prev) prev.addEventListener("click", function () { chooseDay(shiftDay(day, -1)); });
    if (next) next.addEventListener("click", function () { chooseDay(shiftDay(day, 1)); });
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { choosePeriod(tab.getAttribute("data-period")); });
      tab.addEventListener("keydown", function (event) {  // arrow keys move between tabs
        var step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
        if (!step) return;
        event.preventDefault();
        var target = tabs[(i + step + tabs.length) % tabs.length];
        target.focus();
        choosePeriod(target.getAttribute("data-period"));
      });
    });

    chooseDay(day);

    function chooseDay(iso) {
      if (iso < input.min || iso > input.max) return;
      day = iso;
      input.value = iso;
      if (label) label.textContent = longDate(iso);
      if (prev) prev.disabled = iso <= input.min;
      if (next) next.disabled = iso >= input.max;
      selected = null;
      announce();
      load(iso);
    }

    function load(iso) {
      var thisRequest = ++requestId;
      showSkeleton();
      setStatus("Loading slots…");
      fetch("/api/availability?date=" + encodeURIComponent(iso), { headers: { Accept: "application/json" } })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          if (thisRequest !== requestId) return;  // a newer day was picked
          slots = data.slots || [];
          setStatus("");
          showCounts();
          var wanted = preselect && slots.filter(function (s) { return s.time === preselect && s.state === "available"; })[0];
          choosePeriod(wanted ? wanted.period : firstUsefulPeriod());
          if (wanted) { pick(wanted); preselect = ""; }
        })
        .catch(function () {
          if (thisRequest !== requestId) return;
          grid.innerHTML = "";
          setStatus("Could not load slots.");
          var retry = document.createElement("button");
          retry.type = "button";
          retry.className = "btn btn--ghost";
          retry.textContent = "Try again";
          retry.addEventListener("click", function () { load(iso); });
          grid.appendChild(retry);
        });
    }

    function firstUsefulPeriod() {
      for (var i = 0; i < tabs.length; i++) {
        var key = tabs[i].getAttribute("data-period");
        if (slots.some(function (s) { return s.period === key && s.state === "available"; })) return key;
      }
      for (var j = 0; j < tabs.length; j++) {
        var k = tabs[j].getAttribute("data-period");
        if (slots.some(function (s) { return s.period === k; })) return k;
      }
      return period;
    }

    function showCounts() {
      var free = slots.filter(function (s) { return s.state === "available"; }).length;
      var taken = slots.filter(function (s) { return s.state === "booked" || s.state === "pending"; }).length;
      if (countFree) countFree.textContent = free;
      if (countTaken) countTaken.textContent = taken;
    }

    function choosePeriod(key) {
      period = key;
      tabs.forEach(function (tab) {
        var on = tab.getAttribute("data-period") === key;
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
        if (on) grid.setAttribute("aria-labelledby", tab.id);
      });
      render();
    }

    function render() {
      grid.innerHTML = "";
      var shown = slots.filter(function (s) { return s.period === period; });
      if (!shown.length) {
        var none = document.createElement("p");
        none.className = "slotcards__empty";
        none.textContent = "No open hours in this part of the day.";
        grid.appendChild(none);
        return;
      }
      shown.forEach(function (slot) { grid.appendChild(card(slot)); });
    }

    function card(slot) {
      var open = slot.state === "available";
      var taken = slot.state === "booked" || slot.state === "pending";
      var el = document.createElement("article");
      el.className = "slotcard" + (taken ? " slotcard--taken" : "") + (slot.state === "past" ? " slotcard--past" : "") +
        (selected && selected.date === slot.date && selected.time === slot.time ? " slotcard--selected" : "");
      var when = plainTime(slot.label) + " – " + endLabel(slot.label);
      el.innerHTML =
        '<div class="slotcard__top">' +
          '<span class="slotcard__brand">' + (logo ? '<img src="' + logo + '" alt="" width="36" height="36">' : "") + brand + "</span>" +
          '<span class="slotcard__badge slotcard__badge--' + slot.state + '">' + (BADGE[slot.state] || slot.state) + "</span>" +
        "</div>" +
        '<p class="slotcard__row">' + ICON_CAL + "<span>" + when + "</span>" + ICON_CLOCK + "<span>60 mins</span></p>" +
        '<p class="slotcard__row">' + ICON_CAL + "<span>" + shortDate(slot.date) + "</span></p>" +
        '<div class="slotcard__foot"><div><div class="slotcard__label">Price</div>' +
          '<div class="slotcard__price">' + taka(slot.price_bdt) + "</div></div></div>";

      if (open) {
        var foot = el.querySelector(".slotcard__foot");
        var aria = "Book " + when + ", " + shortDate(slot.date);
        if (linkMode) {
          var a = document.createElement("a");
          a.className = "btn btn--primary slotcard__book";
          a.href = bookUrl + "?date=" + encodeURIComponent(slot.date) + "&slot=" + encodeURIComponent(slot.time);
          a.textContent = "Book now";
          a.setAttribute("aria-label", aria);
          foot.appendChild(a);
        } else {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "btn btn--primary slotcard__book";
          b.textContent = selected && selected.date === slot.date && selected.time === slot.time ? "Selected" : "Book now";
          b.setAttribute("aria-label", aria);
          b.setAttribute("aria-pressed", b.textContent === "Selected" ? "true" : "false");
          b.addEventListener("click", function () {
            pick(slot);
            var form = document.querySelector("[data-booking-form]");
            if (form) form.scrollIntoView({ behavior: "smooth", block: "start" });
          });
          foot.appendChild(b);
        }
      }
      return el;
    }

    function pick(slot) {
      selected = slot;
      render();
      announce();
    }

    function announce() {
      if (summary) {
        if (selected) {
          summary.textContent = shortDate(selected.date) + ", " + plainTime(selected.label) + " – " + endLabel(selected.label) +
            " · " + (selected.price_bdt == null ? "Price on request" : "Total " + taka(selected.price_bdt));
          summary.hidden = false;
        } else {
          summary.hidden = true;
          summary.textContent = "";
        }
      }
      root.dispatchEvent(new CustomEvent("slotpicker:change", {
        detail: { date: selected ? selected.date : day, slot: selected ? selected.time : null },
      }));
    }

    function showSkeleton() {
      grid.innerHTML = "";
      for (var i = 0; i < 6; i++) {
        var block = document.createElement("div");
        block.className = "slotcard slotcard--skeleton";
        block.setAttribute("aria-hidden", "true");
        grid.appendChild(block);
      }
    }

    function setStatus(text) { if (statusLine) statusLine.textContent = text; }
  }
})();
