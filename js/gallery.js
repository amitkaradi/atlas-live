/* ═══════════════════════════════════════════════════════════════
   ATLAS v2 — gallery: full storefront with status/genre filters
   ═══════════════════════════════════════════════════════════════ */
(() => {
"use strict";

const grid = document.getElementById("galleryGrid");
const countEl = document.getElementById("filterCount");
const statusGroup = document.getElementById("statusFilters");
const genreGroup = document.getElementById("genreFilters");

const state = { status: "all", genre: "all" };

/* genre chips from data */
const genres = [...new Set(SITES.map(s => s.genreKey))];
genreGroup.insertAdjacentHTML("beforeend",
  `<button class="chip is-on" data-genre="all">הכול</button>` +
  genres.map(g => `<button class="chip" data-genre="${g}">${GENRES[g] || g}</button>`).join(""));

function matches(site) {
  if (state.status === "available" && site.sold) return false;
  if (state.status === "sold" && !site.sold) return false;
  if (state.genre !== "all" && site.genreKey !== state.genre) return false;
  return true;
}

function render() {
  const list = SITES.filter(matches);
  grid.innerHTML = list.map(cardHTML).join("");
  bindCardHighlights(grid);
  // cards re-enter instantly on filter — reveal choreography is for first load only
  grid.querySelectorAll(".reveal").forEach(el => el.classList.remove("reveal"));
  if (!REDUCED) gsap.fromTo(grid.children,
    { opacity: 0, y: 22 },
    { opacity: 1, y: 0, duration: 0.7, ease: "power3.out", stagger: 0.06 });
  const avail = list.filter(s => !s.sold).length;
  const soldN = list.length - avail;
  countEl.textContent = list.length === 0
    ? "אין כאן כלום — המדף מתחדש בקרוב."
    : `${list.length} יצירות — ${avail} זמינות · ${soldN} נמכרו`;
}

function wireChips(group, key) {
  group.addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    group.querySelectorAll(".chip").forEach(c => c.classList.toggle("is-on", c === chip));
    state[key] = chip.dataset[key === "status" ? "status" : "genre"];
    render();
  });
}
wireChips(statusGroup, "status");
wireChips(genreGroup, "genre");

render();

})();
