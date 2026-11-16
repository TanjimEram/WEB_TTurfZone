/* CR-14: the dashboard checks for new bookings every 30 seconds while it is open.
   A new one shows a banner, puts the count in the tab title and beeps (once sound is on:
   browsers only allow sound after a tap on the page). */
(function () {
  var box = document.querySelector("[data-alerts]");
  if (!box) return;
  var known = Number(box.dataset.latest) || 0;
  var banner = box.querySelector("[data-alerts-banner]");
  var button = box.querySelector("[data-alerts-sound]");
  var title = document.title;
  var audio = null;

  function beep() {
    if (!audio) return;
    [0, 0.3].forEach(function (t) {
      var osc = audio.createOscillator(), gain = audio.createGain();
      osc.frequency.value = 880;
      gain.gain.value = 0.25;
      osc.connect(gain);
      gain.connect(audio.destination);
      osc.start(audio.currentTime + t);
      osc.stop(audio.currentTime + t + 0.18);
    });
  }

  function soundOn() {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (audio || !Ctx) return;
    audio = new Ctx();
    audio.resume();
    button.textContent = "Alert sound is on";
    button.disabled = true;
  }

  button.hidden = !(window.AudioContext || window.webkitAudioContext);
  button.addEventListener("click", function () { soundOn(); beep(); });
  document.addEventListener("pointerdown", soundOn, { once: true });

  function check() {
    fetch(box.dataset.url, { cache: "no-store", credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.latest > known) {
          known = d.latest;
          banner.hidden = false;
          document.title = "(" + d.count + ") New booking · " + title;
          beep();
        }
      })
      .catch(function () {}); /* signed out or offline: try again next time */
  }
  setInterval(check, 30000);
})();
