/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — common page engine (loaded LAST on every page)
   Lenis · nav · reveals · counters · waitlist forms
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

gsap.registerPlugin(ScrollTrigger);

/* ── Lenis ───────────────────────────────────────────────────── */
let lenis = null;
if (!REDUCED) {
  lenis = new Lenis({ duration: 1.25, easing: t => 1 - Math.pow(1 - t, 3), smoothWheel: true });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add(t => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  // home has a loader; it will start lenis itself when ready
  if (document.getElementById("loader")) lenis.stop();
}
window.ATLAS = { lenis };

/* ── nav ─────────────────────────────────────────────────────── */
const nav = document.getElementById("nav");
const page = document.body.dataset.page || "";
document.querySelectorAll(".nav__links a[data-nav]").forEach(a => {
  if (a.dataset.nav === page) a.classList.add("is-active");
});
ScrollTrigger.create({
  start: 60, end: "max",
  onEnter: () => nav.classList.add("scrolled"),
  onLeaveBack: () => nav.classList.remove("scrolled")
});
if (window.scrollY > 60) nav.classList.add("scrolled");

/* mobile menu */
const burger = document.getElementById("navBurger");
if (burger) {
  burger.addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    burger.setAttribute("aria-expanded", open);
    if (lenis) open ? lenis.stop() : lenis.start();
  });
  document.querySelectorAll(".nav__links a").forEach(a =>
    a.addEventListener("click", () => {
      document.body.classList.remove("menu-open");
      burger.setAttribute("aria-expanded", "false");
      if (lenis) lenis.start();
    }));
}

/* smooth same-page anchors */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener("click", e => {
    const target = document.querySelector(a.getAttribute("href"));
    if (!target) return;
    e.preventDefault();
    if (lenis) lenis.scrollTo(target, { duration: 1.6 });
    else target.scrollIntoView({ behavior: "smooth" });
  });
});

/* ── subpage entrance (home runs its own loader intro) ───────── */
if (!document.getElementById("loader")) {
  document.body.classList.add("page-enter");
  requestAnimationFrame(() => requestAnimationFrame(() =>
    document.body.classList.add("page-enter-done")));
}

/* ── shared reveals — after every page script has built its DOM ─ */
if (!REDUCED) {
  ScrollTrigger.batch(".reveal", {
    start: "top 86%",
    once: true,
    onEnter: els => gsap.to(els, {
      opacity: 1, y: 0, duration: 1.15, ease: "power3.out", stagger: 0.12
    })
  });
  // anything already above the fold on load
  ScrollTrigger.refresh();
}

/* ── counters ────────────────────────────────────────────────── */
document.querySelectorAll(".counter strong").forEach(el => {
  const target = parseInt(el.dataset.count, 10) || 0;
  if (REDUCED) { el.textContent = target; return; }
  const obj = { v: 0 };
  ScrollTrigger.create({
    trigger: el, start: "top 88%", once: true,
    onEnter: () => gsap.to(obj, {
      v: target, duration: 2, ease: "power2.out",
      onUpdate: () => { el.textContent = Math.round(obj.v); }
    })
  });
});

/* ── waitlist forms (any page) ───────────────────────────────── */
document.querySelectorAll("form[data-waitlist]").forEach(form => {
  form.addEventListener("submit", e => {
    e.preventDefault();
    const email = form.querySelector('input[type="email"]');
    if (!email || !email.value || !email.checkValidity()) { email && email.focus(); return; }
    try { localStorage.setItem("atlas-waitlist", email.value); } catch (_) {}
    form.hidden = true;
    const ok = document.querySelector(form.dataset.waitlist);
    if (ok) {
      ok.hidden = false;
      gsap.fromTo(ok, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out" });
    }
  });
});

/* ── ambient videos: hide cleanly when missing ───────────────── */
document.querySelectorAll("video[data-ambient]").forEach(v => {
  v.addEventListener("error", () => { v.style.display = "none"; }, { once: true });
  v.play && v.play().catch(() => {});
});

/* card hover highlights for any server-rendered cards */
bindCardHighlights(document);

/* ── mock-site notice — the shelf is illustrative for now ────── */
const mocknote = document.createElement("div");
mocknote.className = "mocknote";
mocknote.setAttribute("role", "note");
mocknote.innerHTML = "<b>אתר הדגמה</b> · היצירות והמחירים להמחשה בלבד";
document.body.appendChild(mocknote);

})();
