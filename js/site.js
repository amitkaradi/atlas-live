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

/* real order form — appears when the API (production) is available */
const orderForm = document.createElement("form");
orderForm.className = "orderform";
orderForm.hidden = true;
orderForm.noValidate = true;
orderForm.innerHTML = `
  <div class="frow">
    <input type="text" id="ordName" placeholder="השם שלכם" autocomplete="name" required aria-label="שם">
    <input type="email" id="ordEmail" placeholder="your@email.com" autocomplete="email" required aria-label="מייל">
  </div>
  <input type="tel" id="ordPhone" placeholder="טלפון (לא חובה)" autocomplete="tel" aria-label="טלפון">
  <input type="text" name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
  <p class="apply__err" id="ordErr" aria-live="polite"></p>
  <button class="btn btn--gold" type="submit">לשריין ל-48 שעות</button>`;
btn.insertAdjacentElement("afterend", orderForm);
const ordErr = orderForm.querySelector("#ordErr");

function paintActions() {
  document.getElementById("pieceBadge").innerHTML = statusBadge(site);
  renderProvenance();
  const soldNow = site.sold || site.live === "sold";
  const reservedNow = pieceReserved(site);
  const mine = apiMode() ? !!myToken(site.id) : reservedNow;

  orderForm.hidden = true;
  btn.hidden = false;
  if (soldNow) {
    btn.disabled = true;
    btn.textContent = "איננו לתמיד";
    hint.textContent = "היצירה הזו ירדה מהמדף. היוצר שלה כבר בונה את הבאה.";
    releaseBtn.hidden = true;
  } else if (reservedNow && mine) {
    btn.disabled = true;
    btn.textContent = "שמור — בדקו את המייל";
    hint.textContent = "אנחנו שומרים אותו 48 שעות בזמן שמדברים.";
    releaseBtn.hidden = false;
  } else if (reservedNow) {
    btn.disabled = true;
    btn.textContent = "שמור כרגע";
    hint.textContent = "מישהו מחזיק את היצירה ל-48 שעות. אם השמירה תשתחרר — היא תחזור לזמינה.";
    releaseBtn.hidden = true;
  } else {
    btn.disabled = false;
    btn.textContent = "לרכוש את האתר";
    hint.textContent = "שומר את היצירה ל-48 שעות. החזר מלא עד העלייה לאוויר.";
    releaseBtn.hidden = true;
  }
}

btn.addEventListener("click", () => {
  if (btn.disabled || site.sold) return;
  if (!apiMode()) { // demo mode — per-browser hold, as before
    reserve(site.id);
    paintActions();
    return;
  }
  btn.hidden = true;
  orderForm.hidden = false;
  orderForm.querySelector("#ordName").focus();
});

orderForm.addEventListener("submit", async e => {
  e.preventDefault();
  ordErr.textContent = "";
  const name = orderForm.querySelector("#ordName");
  const email = orderForm.querySelector("#ordEmail");
  if (!name.value.trim()) { ordErr.textContent = "שם, כדי שנדע עם מי מדברים."; name.focus(); return; }
  if (!email.value || !email.checkValidity()) { ordErr.textContent = "המייל הזה לא נראה תקין."; email.focus(); return; }
  const submitBtn = orderForm.querySelector("button");
  submitBtn.disabled = true;
  submitBtn.textContent = "רגע…";
  try {
    const res = await api("reserve", {
      id: site.id,
      name: name.value.trim(),
      email: email.value.trim(),
      phone: orderForm.querySelector("#ordPhone").value.trim(),
      website: orderForm.querySelector(".hp").value
    });
    saveToken(site.id, res.token);
    site.live = "reserved";
    site.liveUntil = res.until;
    paintActions();
  } catch (err) {
    if (err.status === 409) { // someone got here first
      site.live = "reserved";
      paintActions();
    } else {
      ordErr.textContent = "משהו השתבש — נסו שוב עוד רגע.";
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "לשריין ל-48 שעות";
  }
});

releaseBtn.addEventListener("click", async () => {
  if (!apiMode()) {
    release(site.id);
    paintActions();
    return;
  }
  const token = myToken(site.id);
  releaseBtn.disabled = true;
  try {
    await api("release", { id: site.id, token });
    dropToken(site.id);
    site.live = "available";
    paintActions();
  } catch (_) { /* keep state */ }
  releaseBtn.disabled = false;
});

paintActions();
fetchLiveStatuses().then(ok => { if (ok) paintActions(); });

/* ── provenance (re-rendered whenever the piece's state changes) ─ */
function renderProvenance() {
  const steps = [
    { when: site.built, what: `נבנה בידי ${site.creator}`, note: "בן יחיד, מהשורה הראשונה של הקוד." },
    { when: "עלה למדף", what: "נכנס לגלריה", note: "אמיתי, רץ וקליקבילי מהיום הראשון." }
  ];
  if (site.sold || site.live === "sold") {
    steps.push({ when: "נמכר", what: "ירד מהמדף, לתמיד", note: "הותאם ונחתם עבור הבעלים היחיד שלו.", now: true });
  } else if (pieceReserved(site)) {
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
