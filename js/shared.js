/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — shared data + helpers (loaded first on every page)
   ═══════════════════════════════════════════════════════════════ */
"use strict";

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (REDUCED) document.documentElement.classList.add("no-motion");
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

/* ── the shelf ───────────────────────────────────────────────── */
const SITES = [
  {
    id: "maison-lumiere", name: "Maison Lumière", genre: "Patisserie & café", genreKey: "hospitality",
    price: 3400, sold: false, creator: "Noa B.", built: "June 2026",
    desc: "A warm, sugared editorial for a neighborhood patisserie — menu, ordering, and a morning-light photo journal.",
    story: "Maison Lumière was built around one idea: a bakery's website should feel like the first hour of the morning. The palette is butter and shadow, the typography sets like icing, and the menu reads as a single unhurried page. An ordering flow sits quietly behind the scenes — present when needed, invisible when not. It loads like a whisper and never raises its voice.",
    features: ["Morning-light photo journal", "Menu with quiet ordering flow", "Opening-hours ribbon that knows the day", "Owner-editable content, no dashboard maze"],
    theme: { bg: "#FBF6EE", ink: "#3A2E22", accent: "#B0793E", media: "linear-gradient(135deg,#E8CBA8,#B0793E)" },
    headline: "Baked before sunrise.", pages: 5, stack: "Static · CMS-ready"
  },
  {
    id: "verre", name: "Verre", genre: "Glassware atelier", genreKey: "commerce",
    price: 3400, sold: false, creator: "Dan K.", built: "June 2026",
    desc: "Cool, transparent, precise — a catalogue for hand-blown glass with product stories told in reflections.",
    story: "Verre treats every object like it deserves a museum plinth. Twelve pieces, twelve stories, each photographed against light instead of backdrops. The commerce flow was built for low volume and high intention: no urgency banners, no cart psychology — a considered purchase, made slowly. The glass does the selling.",
    features: ["Catalogue of twelve, told in reflections", "Quiet commerce flow — no urgency tricks", "Provenance note on every piece", "Studio-visit booking page"],
    theme: { bg: "#F2F5F6", ink: "#22303A", accent: "#5E8CA7", media: "linear-gradient(135deg,#C9DAE3,#5E8CA7)" },
    headline: "Shaped by breath.", pages: 6, stack: "Static · Commerce"
  },
  {
    id: "solstice", name: "Solstice", genre: "Wellness retreat", genreKey: "hospitality",
    price: 3400, sold: false, creator: "Maya R.", built: "May 2026",
    desc: "A slow-scrolling retreat site — schedule, rooms, and a booking inquiry flow wrapped in dune tones.",
    story: "Solstice scrolls at the pace of the place it describes. Rooms are shown in natural light only. The schedule breathes — one retreat at a time, never a grid of urgency. The booking flow asks three questions and then gets out of the way. Built for a retreat that fills by word of mouth and wants a website that behaves the same way.",
    features: ["Slow-scroll room tour", "One-retreat-at-a-time schedule", "Three-question booking inquiry", "Dune-tone palette, zero stock photography"],
    theme: { bg: "#F5F1E8", ink: "#3D3A2E", accent: "#8A8B5C", media: "linear-gradient(135deg,#D9D4B8,#8A8B5C)" },
    headline: "Arrive slowly.", pages: 7, stack: "Static · Booking"
  },
  {
    id: "cartograph", name: "Cartograph", genre: "Travel journal", genreKey: "editorial",
    price: 3400, sold: false, creator: "Noa B.", built: "April 2026",
    desc: "An editorial travel journal with route maps drawn as engravings and photo essays that breathe on scroll.",
    story: "Cartograph is for a writer who travels, not a traveler who posts. Routes are drawn as engravings, essays are set in long measure, and photographs breathe as the reader scrolls. A newsletter lives at the end of every piece — reader-supported, no paywall theatrics. The site's only metric is whether people finish the essays.",
    features: ["Engraving-style route maps", "Long-form essay layout, built to be finished", "Reader-supported newsletter flow", "Offline reading mode"],
    theme: { bg: "#F4EFE6", ink: "#2E2A24", accent: "#A0563B", media: "linear-gradient(135deg,#DBC3AE,#A0563B)" },
    headline: "Roads, annotated.", pages: 8, stack: "Static · Newsletter"
  },
  {
    id: "meridian", name: "Meridian", genre: "Architecture practice", genreKey: "portfolio",
    price: 3400, sold: false, creator: "Dan K.", built: "June 2026",
    desc: "A drafting-table portfolio for a small architecture practice — projects shown in plan, section, and light.",
    story: "Meridian shows buildings the way architects think about them: plan first, photograph second. Each project opens as a folio — drawings, then models, then the finished light. Type is set on a strict grid that never announces itself. A practice page lists people and principles in the same breath, because in a small office they are the same thing.",
    features: ["Folio layout: plan → model → light", "Strict modular grid, quietly kept", "Practice & principles page", "Print-ready project sheets"],
    theme: { bg: "#F1F0EC", ink: "#2B2B28", accent: "#6E6A5E", media: "linear-gradient(135deg,#CFCCC2,#6E6A5E)" },
    headline: "Drawn, then built.", pages: 6, stack: "Static · Folio"
  },
  {
    id: "atelier-noir", name: "Atelier Noir", genre: "Photography studio", genreKey: "portfolio",
    price: 3400, sold: true, creator: "Maya R.", built: "March 2026",
    desc: "Sold. A charcoal-dark portfolio with film-grain galleries and a private client room.",
    story: "Atelier Noir was the first piece to leave the shelf. A charcoal-dark portfolio where photographs are the only light source — film-grain galleries, a private client room behind a single key, and typography that stays out of the frame. It belongs to one photographer now, personalized down to the letterhead. This page remains as provenance.",
    features: ["Film-grain galleries, dark-room pacing", "Private client rooms", "Single-key access, no accounts", "Personalized and sealed for its owner"],
    theme: { bg: "#191817", ink: "#EDEAE4", accent: "#C9A45C", media: "linear-gradient(135deg,#3B3835,#C9A45C)" },
    headline: "Light, kept.", pages: 5, stack: "Static · Client rooms"
  },
  {
    id: "ledger-vine", name: "Ledger & Vine", genre: "Boutique counsel", genreKey: "professional",
    price: 3400, sold: true, creator: "Noa B.", built: "February 2026",
    desc: "Sold. A paper-and-ink presence for a two-partner firm — practice notes and a considered contact ritual.",
    story: "Ledger & Vine reads like good stationery. Practice notes instead of service pages, engagements instead of testimonials, and a contact ritual that filters for seriousness without saying so. It was bought within a week of listing by the firm it now belongs to — personalized, sealed, and off the shelf forever.",
    features: ["Practice notes, not service pages", "Considered contact ritual", "Secure document handoff", "Sealed for a two-partner firm"],
    theme: { bg: "#F0EDE6", ink: "#26303B", accent: "#7A6A45", media: "linear-gradient(135deg,#C8CCC9,#7A6A45)" },
    headline: "Counsel, quietly.", pages: 4, stack: "Static · Secure forms"
  },
  {
    id: "umbra", name: "Umbra", genre: "Perfumery", genreKey: "commerce",
    price: 3400, sold: true, creator: "Maya R.", built: "January 2026",
    desc: "Sold. A dusk-toned maison for a small-batch perfumery — scent stories told before products.",
    story: "Umbra sells scent by telling you where it comes from. Each fragrance opens as a place — a season, an hour, a memory — before it ever shows a bottle. The shop is three pages deep and feels like a private viewing. It was acquired by the perfumery it was imagined for, which is exactly how Atlas is supposed to work.",
    features: ["Scent stories before products", "Three-page private-viewing shop", "Batch provenance per bottle", "Sealed for its maison"],
    theme: { bg: "#1E1A20", ink: "#EAE3EE", accent: "#A98BC4", media: "linear-gradient(135deg,#4A3F52,#A98BC4)" },
    headline: "Worn after dark.", pages: 5, stack: "Static · Commerce"
  }
];

const siteById = id => SITES.find(s => s.id === id) || null;
const money = n => "$" + n.toLocaleString();

/* ── reservations (functional storefront state) ──────────────── */
const RES_KEY = "atlas-reserved";
function getReserved() {
  try { return JSON.parse(localStorage.getItem(RES_KEY)) || []; } catch (_) { return []; }
}
function isReserved(id) { return getReserved().includes(id); }
function reserve(id) {
  const r = getReserved();
  if (!r.includes(id)) { r.push(id); try { localStorage.setItem(RES_KEY, JSON.stringify(r)); } catch (_) {} }
}
function release(id) {
  const r = getReserved().filter(x => x !== id);
  try { localStorage.setItem(RES_KEY, JSON.stringify(r)); } catch (_) {}
}

/* ── card / preview markup ───────────────────────────────────── */
function previewHTML(site) {
  const t = site.theme;
  return `
  <div class="card__frame">
    <div class="card__bar"><i></i><i></i><i></i><em>${site.id}.one — live</em></div>
    <div class="preview" style="background:${t.bg};color:${t.ink}">
      <div class="p-cursor" aria-hidden="true"></div>
      <div class="p-nav">
        <span class="p-logo">${site.name}</span>
        <span class="p-links"><b></b><b></b><b></b></span>
      </div>
      <div class="p-hero">
        <div class="p-head"><span class="p-type">${site.headline}</span></div>
        <div class="p-sub"></div>
        <span class="p-btn" style="background:${t.accent};color:${t.bg}">Enter</span>
        <span class="p-media" style="--m:${t.media}"></span>
      </div>
      <div class="p-row"><b></b><b></b><b></b></div>
    </div>
    ${site.sold ? '<span class="card__seal" title="Sold — sealed">A</span>' : ""}
  </div>`;
}

function statusBadge(site) {
  if (site.sold) return '<span class="badge badge--sold">Sold</span>';
  if (isReserved(site.id)) return '<span class="badge badge--reserved">Reserved</span>';
  return '<span class="badge badge--live">Available now</span>';
}

function cardHTML(site) {
  return `
  <a class="card reveal${site.sold ? " card--sold" : ""}" href="site.html?id=${site.id}"
     data-id="${site.id}" aria-label="${site.name} — ${site.sold ? "sold" : "available"}">
    ${previewHTML(site)}
    <div class="card__meta">
      <h3 class="card__name">${site.name}</h3>
      <span class="card__price">${site.sold ? "—" : money(site.price)}</span>
    </div>
    <div class="card__foot">
      <span class="card__genre">${site.genre}</span>
      ${statusBadge(site)}
    </div>
  </a>`;
}

function bindCardHighlights(root) {
  (root || document).querySelectorAll(".card").forEach(el => {
    el.addEventListener("pointermove", e => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${((e.clientX - r.left) / r.width) * 100}%`);
      el.style.setProperty("--my", `${((e.clientY - r.top) / r.height) * 100}%`);
    });
  });
}

/* ── media helpers ───────────────────────────────────────────── */
function loadImage(src) {
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function scrubVideo(videoEl, triggerEl) {
  if (!videoEl) return;
  videoEl.muted = true;
  if (REDUCED) {
    videoEl.loop = true; videoEl.autoplay = true;
    videoEl.play().catch(() => {});
    return;
  }
  const apply = p => {
    if (!videoEl.duration || !isFinite(videoEl.duration)) return;
    const t = Math.min(videoEl.duration - 0.05, p * videoEl.duration);
    if (Math.abs((videoEl.currentTime || 0) - t) > 0.01) videoEl.currentTime = t;
  };
  ScrollTrigger.create({
    trigger: triggerEl, start: "top top", end: "bottom bottom", scrub: 0.5,
    onUpdate: self => apply(self.progress)
  });
  videoEl.addEventListener("loadedmetadata", () => ScrollTrigger.refresh(), { once: true });
  videoEl.addEventListener("error", () => { videoEl.style.display = "none"; }, { once: true });
}
