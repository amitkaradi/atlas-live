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
const FRAME_COUNT = 383;
// small screens get the 880px set — a third of the bytes, same motion
const FRAME_DIR = window.matchMedia("(max-width: 900px)").matches ? "frames-sm" : "frames";
const framePath = i => `assets/${FRAME_DIR}/orbit_${String(i + 1).padStart(4, "0")}.webp`;

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

function drawImageCover(img, clear) {
  if (!img) return;
  const cw = canvas.width, ch = canvas.height;
  const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
  if (!iw || !ih || !cw || !ch) return;
  const scale = Math.max(cw / iw, ch / ih);
  const w = iw * scale, h = ih * scale;
  if (clear) ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
}

// nearest loaded frame at or below idx, so partial loads still render
function nearestLoaded(idx) {
  for (let i = idx; i >= 0; i--) if (frames[i]) return frames[i];
  return null;
}

let drawQueued = false;
function drawFrame() {
  if (drawQueued) return;
  drawQueued = true;
  requestAnimationFrame(() => {
    drawQueued = false;
    if (!framesReady) { drawImageCover(fallbackImg, true); return; }
    const f = Math.max(0, Math.min(FRAME_COUNT - 1, state.frame));
    const idx = Math.floor(f);
    const frac = f - idx;
    const a = nearestLoaded(idx) || fallbackImg;
    const b = frames[idx + 1];
    drawImageCover(a, true);
    // sub-frame crossfade: fractional positions blend into the next frame
    if (frac > 0.01 && b && b !== a) {
      ctx.globalAlpha = frac;
      drawImageCover(b, false);
      ctx.globalAlpha = 1;
    }
  });
}

// Progressive streaming: a coarse pass (every 8th frame) covers the whole
// orbit and gates the loader — the page opens after ~50 small files. The
// remaining passes (4th, 2nd, all) stream in the background and the scrub
// sharpens silently; nearestLoaded() renders whatever has arrived.
function buildLoadOrder() {
  const seen = new Set();
  const order = [];
  for (const stride of [8, 4, 2, 1]) {
    for (let i = 0; i < FRAME_COUNT; i += stride) {
      if (!seen.has(i)) { seen.add(i); order.push(i); }
    }
  }
  return order;
}

async function loadIndices(indices, concurrency, onEach) {
  let next = 0;
  await Promise.all(Array.from({ length: concurrency }, async () => {
    while (next < indices.length) {
      const i = indices[next++];
      if (!frames[i]) frames[i] = await loadImage(framePath(i));
      onEach && onEach(i);
    }
  }));
}

async function preloadFrames(onProgress) {
  const probe = await loadImage(framePath(0));
  if (!probe) { onProgress(1); return; }
  frames[0] = probe;
  framesReady = true;
  const order = buildLoadOrder();
  const coarseCount = Math.ceil(FRAME_COUNT / 8);
  let loaded = 1;
  // coarse pass — this is all the loader waits for
  await loadIndices(order.slice(0, coarseCount), 8, i => {
    loaded++;
    onProgress(Math.min(1, loaded / coarseCount));
    if (i % 16 === 0) drawFrame();
  });
  onProgress(1);
  drawFrame();
  // the rest streams behind the open page, gentler on bandwidth
  loadIndices(order.slice(coarseCount), 5, i => { if (i % 24 === 0) drawFrame(); })
    .then(drawFrame);
}

/* ══ LOADER → INTRO ══════════════════════════════════════════ */
const loader = document.getElementById("loader");
const loaderBar = document.getElementById("loaderBar");

async function boot() {
  fallbackImg = await loadImage("assets/hero-still.webp");
  sizeCanvas();
  window.addEventListener("resize", sizeCanvas);
  // the canvas can be laid out at 0×0 (hidden/backgrounded tab at boot) —
  // re-size the backing store whenever its CSS box actually changes
  if ("ResizeObserver" in window) new ResizeObserver(sizeCanvas).observe(canvas);
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
  // slightly heavier scrub smoothing = GSAP eases toward the target frame,
  // emitting many sub-frame updates the crossfade renderer turns into motion
  ScrollTrigger.create({
    trigger: "#hero",
    start: "top top",
    end: "bottom bottom",
    scrub: 0.8,
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
