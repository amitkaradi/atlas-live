/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — piece detail: ?id=, reserve/release, provenance,
   related pieces
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

const id = new URLSearchParams(location.search).get("id");
const site = siteById(id);
if (!site) { location.replace("gallery.html"); return; }

document.title = `${site.name} — אטלס`;

/* ── media column — a live demo gets the real, interactive site ─ */
document.getElementById("pieceFrame").innerHTML = site.demo
  ? `<div class="piece__livehint">
       <span class="badge badge--live">חי</span>
       זהו אתר אמיתי — גללו בתוכו, לחצו, נסו הכול.
     </div>
     <div class="piece__liveframe">
       <iframe src="${site.demo}" title="${site.name} — אתר חי"></iframe>
     </div>`
  : previewHTML(site);
const pal = document.getElementById("piecePalette");
pal.innerHTML =
  [site.theme.bg, site.theme.ink, site.theme.accent]
    .map(c => `<i style="background:${c}" title="${c}"></i>`).join("") +
  `<span>הפלטה של היצירה</span>`;

/* ── body ────────────────────────────────────────────────────── */
document.getElementById("crumbName").textContent = site.name;
document.getElementById("pieceName").textContent = site.name;
document.getElementById("pieceSub").textContent =
  `${site.genre} · מאת ${site.creator} · מהדורה 1 מתוך 1`;
document.getElementById("piecePrice").textContent = site.sold ? "נמכר" : money(site.price);
document.getElementById("pieceBadge").innerHTML = statusBadge(site);
document.getElementById("pieceStory").textContent = site.story;
document.getElementById("pieceFeatures").innerHTML =
  site.features.map(f => `<li>${f}</li>`).join("");
document.getElementById("pieceMeta").innerHTML = `
  <div><dt>ז׳אנר</dt><dd>${site.genre}</dd></div>
  <div><dt>עמודים</dt><dd>${site.pages}</dd></div>
  <div><dt>בנייה</dt><dd>${site.stack}</dd></div>
  <div><dt>יוצר/ת</dt><dd>${site.creator}</dd></div>
  <div><dt>נבנה</dt><dd>${site.built}</dd></div>
  <div><dt>מהדורות</dt><dd>1 — זו שכאן</dd></div>`;

/* ── acquire / reserve / release ─────────────────────────────── */
const btn = document.getElementById("pieceAcquire");
const hint = document.getElementById("pieceHint");
const releaseBtn = document.getElementById("pieceRelease");

function paintActions() {
  document.getElementById("pieceBadge").innerHTML = statusBadge(site);
  renderProvenance();
  if (site.sold) {
    btn.disabled = true;
    btn.textContent = "איננו לתמיד";
    hint.textContent = "היצירה הזו ירדה מהמדף. היוצר שלה כבר בונה את הבאה.";
    releaseBtn.hidden = true;
  } else if (isReserved(site.id)) {
    btn.disabled = true;
    btn.textContent = "שמור — בדקו את המייל";
    hint.textContent = "אנחנו שומרים אותו 48 שעות בזמן שמדברים.";
    releaseBtn.hidden = false;
  } else {
    btn.disabled = false;
    btn.textContent = "לרכוש את האתר";
    hint.textContent = "שומר את היצירה ל-48 שעות. החזר מלא עד העלייה לאוויר.";
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
    { when: site.built, what: `נבנה בידי ${site.creator}`, note: "בן יחיד, מהשורה הראשונה של הקוד." },
    { when: "עלה למדף", what: "נכנס לגלריה", note: "אמיתי, רץ וקליקבילי מהיום הראשון." }
  ];
  if (site.sold) {
    steps.push({ when: "נמכר", what: "ירד מהמדף, לתמיד", note: "הותאם ונחתם עבור הבעלים היחיד שלו.", now: true });
  } else if (isReserved(site.id)) {
    steps.push({ when: "עכשיו", what: "בשמירה — 48 שעות", note: "שמור בזמן שמדברים. החזר מלא עד העלייה לאוויר.", now: true });
  } else {
    steps.push({ when: "עכשיו", what: "זמין — עדיין נושם", note: "הבעלים הבא יסיים את ציר הזמן הזה.", now: true });
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
