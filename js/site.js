/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — piece detail: ?id=, reserve/release, provenance,
   related pieces
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

const id = new URLSearchParams(location.search).get("id");
const site = siteById(id);
if (!site) { location.replace("gallery.html"); return; }

document.title = `${site.name} — ATLAS`;

/* ── media column ────────────────────────────────────────────── */
document.getElementById("pieceFrame").innerHTML = previewHTML(site);
const pal = document.getElementById("piecePalette");
pal.innerHTML =
  [site.theme.bg, site.theme.ink, site.theme.accent]
    .map(c => `<i style="background:${c}" title="${c}"></i>`).join("") +
  `<span>The piece's palette</span>`;

/* ── body ────────────────────────────────────────────────────── */
document.getElementById("crumbName").textContent = site.name;
document.getElementById("pieceName").textContent = site.name;
document.getElementById("pieceSub").textContent =
  `${site.genre} · by ${site.creator} · edition 1 of 1`;
document.getElementById("piecePrice").textContent = site.sold ? "Sold" : money(site.price);
document.getElementById("pieceBadge").innerHTML = statusBadge(site);
document.getElementById("pieceStory").textContent = site.story;
document.getElementById("pieceFeatures").innerHTML =
  site.features.map(f => `<li>${f}</li>`).join("");
document.getElementById("pieceMeta").innerHTML = `
  <div><dt>Genre</dt><dd>${site.genre}</dd></div>
  <div><dt>Pages</dt><dd>${site.pages}</dd></div>
  <div><dt>Build</dt><dd>${site.stack}</dd></div>
  <div><dt>Creator</dt><dd>${site.creator}</dd></div>
  <div><dt>Built</dt><dd>${site.built}</dd></div>
  <div><dt>Editions</dt><dd>1 — this one</dd></div>`;

/* ── acquire / reserve / release ─────────────────────────────── */
const btn = document.getElementById("pieceAcquire");
const hint = document.getElementById("pieceHint");
const releaseBtn = document.getElementById("pieceRelease");

function paintActions() {
  document.getElementById("pieceBadge").innerHTML = statusBadge(site);
  renderProvenance();
  if (site.sold) {
    btn.disabled = true;
    btn.textContent = "Gone forever";
    hint.textContent = "This piece left the shelf. Its creator is building the next one.";
    releaseBtn.hidden = true;
  } else if (isReserved(site.id)) {
    btn.disabled = true;
    btn.textContent = "Reserved — check your email";
    hint.textContent = "We're holding it for 48 hours while we talk.";
    releaseBtn.hidden = false;
  } else {
    btn.disabled = false;
    btn.textContent = "Acquire this site";
    hint.textContent = "Reserves the piece for 48 hours. Full refund until launch.";
    releaseBtn.hidden = true;
  }
}
btn.addEventListener("click", () => {
  if (btn.disabled || site.sold) return;
  reserve(site.id);
  paintActions();
});
releaseBtn.addEventListener("click", () => {
  release(site.id);
  paintActions();
});
paintActions();

/* ── provenance (re-rendered whenever the piece's state changes) ─ */
function renderProvenance() {
  const steps = [
    { when: site.built, what: `Built by ${site.creator}`, note: "One of one, from the first commit." },
    { when: "Listed", what: "Entered the gallery", note: "Real, running, and clickable from day one." }
  ];
  if (site.sold) {
    steps.push({ when: "Sold", what: "Left the shelf, forever", note: "Personalized and sealed for its one owner.", now: true });
  } else if (isReserved(site.id)) {
    steps.push({ when: "Now", what: "On hold — 48 hours", note: "Reserved while we talk. Full refund until launch.", now: true });
  } else {
    steps.push({ when: "Now", what: "Available — still breathing", note: "The next owner ends this timeline.", now: true });
  }
  document.getElementById("prov").innerHTML = steps.map(p => `
    <li${p.now ? ' class="is-now"' : ""}>
      <span class="prov__when">${p.when}</span>
      <div class="prov__what">${p.what}</div>
      <p class="prov__note">${p.note}</p>
    </li>`).join("");
}

/* ── related: other available pieces ─────────────────────────── */
const related = SITES.filter(s => s.id !== site.id && !s.sold).slice(0, 3);
const relGrid = document.getElementById("relatedGrid");
relGrid.innerHTML = related.map(cardHTML).join("");
bindCardHighlights(relGrid);

})();
