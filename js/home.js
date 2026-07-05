/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — home: orbit scrub, hero choreography, pinned steps,
   featured shelf
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

gsap.registerPlugin(ScrollTrigger);

/* ══ FEATURED SHELF — first three available pieces ═══════════ */
const featured = SITES.filter(s => !s.sold).slice(0, 3);
const grid = document.getElementById("featuredGrid");
grid.innerHTML = featured.map(cardHTML).join("");
bindCardHighlights(grid);

/* ══ HERO FRAME SEQUENCE ═════════════════════════════════════ */
const FRAME_COUNT = 121;
const framePath = i => `assets/frames/orbit_${String(i + 1).padStart(4, "0")}.webp`;

const canvas = document.getElementById("orbitCanvas");
const ctx = canvas.getContext("2d");
const frames = new Array(FRAME_COUNT).fill(null);
let framesReady = false;
let fallbackImg = null;
const state = { frame: 0 };

function sizeCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  drawFrame();
}

function drawImageCover(img) {
  if (!img) return;
  const cw = canvas.width, ch = canvas.height;
  const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
  if (!iw || !ih || !cw || !ch) return;
  const scale = Math.max(cw / iw, ch / ih);
  const w = iw * scale, h = ih * scale;
  ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
}

let drawQueued = false;
function drawFrame() {
  if (drawQueued) return;
  drawQueued = true;
  requestAnimationFrame(() => {
    drawQueued = false;
    if (framesReady) {
      const idx = Math.max(0, Math.min(FRAME_COUNT - 1, Math.round(state.frame)));
      let img = null;
      for (let i = idx; i >= 0 && !img; i--) img = frames[i];
      drawImageCover(img || fallbackImg);
    } else {
      drawImageCover(fallbackImg);
    }
  });
}

async function preloadFrames(onProgress) {
  const probe = await loadImage(framePath(0));
  if (!probe) { onProgress(1); return; }
  frames[0] = probe;
  framesReady = true;
  let loaded = 1;
  const CONCURRENCY = 10;
  let next = 1;
  await Promise.all(Array.from({ length: CONCURRENCY }, async () => {
    while (next < FRAME_COUNT) {
      const i = next++;
      frames[i] = await loadImage(framePath(i));
      loaded++;
      onProgress(loaded / FRAME_COUNT);
      if (i % 8 === 0) drawFrame();
    }
  }));
  drawFrame();
}

/* ══ LOADER → INTRO ══════════════════════════════════════════ */
const loader = document.getElementById("loader");
const loaderBar = document.getElementById("loaderBar");

async function boot() {
  fallbackImg = await loadImage("assets/hero-still.png");
  sizeCanvas();
  window.addEventListener("resize", sizeCanvas);
  await preloadFrames(p => { loaderBar.style.width = `${Math.round(p * 100)}%`; });
  loaderBar.style.width = "100%";
  setTimeout(() => {
    loader.classList.add("done");
    const lenis = window.ATLAS && window.ATLAS.lenis;
    if (lenis) lenis.start();
    intro();
  }, 350);
}

function intro() {
  if (REDUCED) {
    gsap.set(["#heroKicker", "#heroTitle span", "#heroTagline"], { opacity: 1, y: 0 });
    return;
  }
  // if the page was restored mid-scroll, the scrub owns the hero — no entrance
  if (window.scrollY > 60) {
    gsap.set("#heroTitle span", { opacity: 1, y: 0 });
    ScrollTrigger.refresh();
    return;
  }
  gsap.timeline({ defaults: { ease: "power3.out" } })
    .to("#heroTitle span", { opacity: 1, y: 0, duration: 1.4, stagger: 0.09 }, 0.2)
    .to("#heroKicker", { opacity: 1, duration: 1.1 }, 0.9)
    .to("#heroTagline", { opacity: 1, duration: 1.1 }, 1.15);
}

/* ══ HERO SCROLL TIMELINE — scrub the orbit ══════════════════ */
if (!REDUCED) {
  ScrollTrigger.create({
    trigger: "#hero",
    start: "top top",
    end: "bottom bottom",
    scrub: 0.4,
    onUpdate: self => {
      state.frame = self.progress * (FRAME_COUNT - 1);
      drawFrame();
    }
  });

  // positions/durations live on a 0..1 scale so progress maps 1:1
  gsap.timeline({
    scrollTrigger: { trigger: "#hero", start: "top top", end: "bottom bottom", scrub: true },
    defaults: { ease: "none", duration: 0.12 }
  })
    .to("#heroKicker",  { opacity: 0, y: -30, duration: 0.08 }, 0.02)
    .to("#heroTitle",   { opacity: 0, y: -60, scale: 0.94 }, 0.04)
    .to("#heroTagline", { opacity: 0, y: -30, duration: 0.10 }, 0.04)
    .to("#scrollCue",   { opacity: 0, duration: 0.06 }, 0.03)
    .to("#heroLineA",   { opacity: 1 }, 0.26)
    .to("#heroLineA p", { y: 0 }, 0.26)
    .to("#heroLineA",   { opacity: 0, duration: 0.10 }, 0.50)
    .to("#heroLineB",   { opacity: 1 }, 0.64)
    .to("#heroLineB p", { y: 0 }, 0.64)
    .to("#heroLineB",   { opacity: 0, duration: 0.08 }, 0.92);
  gsap.set(["#heroLineA p", "#heroLineB p"], { y: 24 });
} else {
  drawFrame();
}

/* ══ VIDEO SCRUBS ════════════════════════════════════════════ */
scrubVideo(document.getElementById("aliveVideo"), "#alive");
scrubVideo(document.getElementById("exclVideo"), ".excl__stage");

/* ══ HOW IT WORKS — pinned horizontal steps ══════════════════ */
if (!REDUCED) {
  const track = document.getElementById("howTrack");
  const howBar = document.getElementById("howBar");
  const pin = document.getElementById("howPin");
  const getDistance = () => {
    const pad = parseFloat(getComputedStyle(pin).paddingLeft) || 0;
    return Math.max(0, track.scrollWidth - (window.innerWidth - pad * 2));
  };
  // in RTL the track lays out right-to-left, so it slides the other way
  const dirSign = document.documentElement.dir === "rtl" ? 1 : -1;
  gsap.to(track, {
    x: () => dirSign * getDistance(),
    ease: "none",
    scrollTrigger: {
      trigger: "#how",
      start: "top top",
      end: "bottom bottom",
      scrub: 0.6,
      invalidateOnRefresh: true,
      onUpdate: self => { howBar.style.width = `${self.progress * 100}%`; }
    }
  });
  gsap.utils.toArray(".step").forEach(step => {
    gsap.from(step, {
      opacity: 0.25, y: 26,
      scrollTrigger: { trigger: "#how", start: "top 60%", once: true },
      duration: 1, ease: "power2.out"
    });
  });
}

/* go */
boot();

})();
