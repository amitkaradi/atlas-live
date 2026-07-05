/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — pricing: FAQ accordion
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

document.querySelectorAll(".faq__item").forEach(item => {
  const q = item.querySelector(".faq__q");
  const a = item.querySelector(".faq__a");
  q.addEventListener("click", () => {
    const open = item.classList.contains("open");
    // one open at a time — quiet, not a wall of text
    document.querySelectorAll(".faq__item.open").forEach(other => {
      other.classList.remove("open");
      other.querySelector(".faq__q").setAttribute("aria-expanded", "false");
      other.querySelector(".faq__a").style.maxHeight = "0px";
    });
    if (!open) {
      item.classList.add("open");
      q.setAttribute("aria-expanded", "true");
      a.style.maxHeight = a.scrollHeight + "px";
    }
  });
});

})();
