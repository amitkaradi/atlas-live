/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — creators: application form
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

const form = document.getElementById("applyForm");
const err = document.getElementById("applyErr");

form.addEventListener("submit", async e => {
  e.preventDefault();
  err.textContent = "";
  const name = document.getElementById("applyName");
  const email = document.getElementById("applyEmail");
  const url = document.getElementById("applyUrl");

  if (!name.value.trim()) { err.textContent = "שם, כדי שנדע מי שואל."; name.focus(); return; }
  if (!email.value || !email.checkValidity()) { err.textContent = "המייל הזה לא נראה תקין."; email.focus(); return; }
  if (!url.value || !url.checkValidity()) { err.textContent = "הקישור צריך להיות כתובת מלאה — כולל //:https."; url.focus(); return; }

  const payload = {
    name: name.value.trim(),
    email: email.value.trim(),
    portfolio: url.value.trim(),
    note: document.getElementById("applyNote").value.trim()
  };
  const hp = form.querySelector(".hp");
  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  try {
    await api("apply", { ...payload, website: hp ? hp.value : "" });
  } catch (_) {
    try { localStorage.setItem("atlas-apply", JSON.stringify(payload)); } catch (_) {}
  }
  submitBtn.disabled = false;

  form.hidden = true;
  const ok = document.getElementById("applyOk");
  ok.hidden = false;
  gsap.fromTo(ok, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out" });
});

})();
