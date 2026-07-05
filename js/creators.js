/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — creators: application form
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

const form = document.getElementById("applyForm");
const err = document.getElementById("applyErr");

form.addEventListener("submit", e => {
  e.preventDefault();
  err.textContent = "";
  const name = document.getElementById("applyName");
  const email = document.getElementById("applyEmail");
  const url = document.getElementById("applyUrl");

  if (!name.value.trim()) { err.textContent = "A name, so we know who's asking."; name.focus(); return; }
  if (!email.value || !email.checkValidity()) { err.textContent = "That email doesn't look right."; email.focus(); return; }
  if (!url.value || !url.checkValidity()) { err.textContent = "The link needs to be a full URL — https:// and all."; url.focus(); return; }

  try {
    localStorage.setItem("atlas-apply", JSON.stringify({
      name: name.value.trim(),
      email: email.value.trim(),
      portfolio: url.value.trim(),
      note: document.getElementById("applyNote").value.trim()
    }));
  } catch (_) {}

  form.hidden = true;
  const ok = document.getElementById("applyOk");
  ok.hidden = false;
  gsap.fromTo(ok, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out" });
});

})();
