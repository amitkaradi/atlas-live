/* ═══════════════════════════════════════════════════════════════
   אטלס v2 — נתונים משותפים + עזרים (נטען ראשון בכל עמוד)
   ═══════════════════════════════════════════════════════════════ */
"use strict";

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (REDUCED) document.documentElement.classList.add("no-motion");
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

/* ── המדף ────────────────────────────────────────────────────── */
const GENRES = {
  hospitality: "אירוח",
  commerce: "מסחר",
  editorial: "מגזין",
  portfolio: "פורטפוליו",
  professional: "משרדים"
};

const SITES = [
  {
    id: "maison-lumiere", name: "לומייר", genre: "קונדיטוריה וקפה", genreKey: "hospitality",
    price: 12900, sold: false, creator: "נועה ב׳", built: "יוני 2026", demo: "demos/maison-lumiere/",
    desc: "מגזין חם ומסוכר לקונדיטוריה שכונתית — תפריט, הזמנות ויומן צילום באור של בוקר.",
    story: "לומייר נבנה סביב רעיון אחד: אתר של מאפייה צריך להרגיש כמו השעה הראשונה של הבוקר. הפלטה היא חמאה וצל, הטיפוגרפיה מתייצבת כמו זילוף, והתפריט נקרא כעמוד אחד רגוע. מערכת ההזמנות יושבת בשקט מאחורי הקלעים — נוכחת כשצריך, בלתי נראית כשלא. הוא נטען כמו לחישה ולעולם לא מרים את הקול.",
    features: ["יומן צילום באור בוקר", "תפריט עם הזמנה שקטה", "רצועת שעות פתיחה שיודעת איזה יום היום", "תוכן שהבעלים עורכים לבד — בלי מבוך של דשבורדים"],
    theme: { bg: "#FBF6EE", ink: "#3A2E22", accent: "#B0793E", media: "linear-gradient(135deg,#E8CBA8,#B0793E)" },
    headline: "נאפה לפני הזריחה.", pages: 5, stack: "סטטי · מוכן ל-CMS"
  },
  {
    id: "verre", name: "ורר", genre: "סטודיו זכוכית", genreKey: "commerce",
    price: 12900, sold: false, creator: "דן ק׳", built: "יוני 2026", demo: "demos/verre/",
    desc: "קריר, שקוף, מדויק — קטלוג לזכוכית מנופחת ביד, עם סיפורי מוצר שמסופרים בהשתקפויות.",
    story: "ורר מתייחס לכל חפץ כאילו מגיע לו כן תצוגה במוזיאון. שתים־עשרה יצירות, שנים־עשר סיפורים, כל אחת מצולמת מול אור במקום מול רקע. תהליך הרכישה נבנה לנפח נמוך ולכוונה גבוהה: בלי באנרים של דחיפות, בלי פסיכולוגיית עגלה — קנייה שקולה, שנעשית לאט. הזכוכית היא זו שמוכרת.",
    features: ["קטלוג של שתים־עשרה, מסופר בהשתקפויות", "רכישה שקטה — בלי טריקים של דחיפות", "תעודת מקור לכל יצירה", "עמוד תיאום ביקור בסטודיו"],
    theme: { bg: "#F2F5F6", ink: "#22303A", accent: "#5E8CA7", media: "linear-gradient(135deg,#C9DAE3,#5E8CA7)" },
    headline: "מעוצב בנשימה.", pages: 6, stack: "סטטי · מסחר"
  },
  {
    id: "solstice", name: "סולסטיס", genre: "ריטריט", genreKey: "hospitality",
    price: 12900, sold: false, creator: "מאיה ר׳", built: "מאי 2026", demo: "demos/solstice/",
    desc: "אתר שנגלל לאט — לוח מפגשים, חדרים וטופס הזמנה עטופים בגווני דיונה.",
    story: "סולסטיס נגלל בקצב של המקום שהוא מתאר. החדרים מוצגים באור טבעי בלבד. הלוח נושם — ריטריט אחד בכל פעם, אף פעם לא רשת של דחיפות. טופס ההזמנה שואל שלוש שאלות ואז זז מהדרך. נבנה לריטריט שמתמלא מפה לאוזן, ורוצה אתר שמתנהג בדיוק כך.",
    features: ["סיור חדרים בגלילה איטית", "לוח של ריטריט אחד בכל פעם", "טופס הזמנה של שלוש שאלות", "פלטת דיונות, אפס תמונות סטוק"],
    theme: { bg: "#F5F1E8", ink: "#3D3A2E", accent: "#8A8B5C", media: "linear-gradient(135deg,#D9D4B8,#8A8B5C)" },
    headline: "מגיעים לאט.", pages: 7, stack: "סטטי · הזמנות"
  },
  {
    id: "cartograph", name: "קרטוגרף", genre: "יומן מסעות", genreKey: "editorial",
    price: 12900, sold: false, creator: "נועה ב׳", built: "אפריל 2026",
    desc: "יומן מסע מגזיני — מפות מסלול מצוירות כתחריטים ומסות צילום שנושמות בגלילה.",
    story: "קרטוגרף נועד לסופרת שנוסעת, לא לנוסעת שמפרסמת. המסלולים מצוירים כתחריטים, המסות מסודרות בשורות ארוכות, והצילומים נושמים בזמן שהקוראים גוללים. ניוזלטר יושב בסוף כל טקסט — נתמך קוראים, בלי תיאטרון של חומות תשלום. המדד היחיד של האתר: האם מסיימים לקרוא.",
    features: ["מפות מסלול בסגנון תחריט", "פריסת מסות ארוכות, בנויה כדי שיסיימו אותן", "ניוזלטר נתמך־קוראים", "מצב קריאה לא מקוון"],
    theme: { bg: "#F4EFE6", ink: "#2E2A24", accent: "#A0563B", media: "linear-gradient(135deg,#DBC3AE,#A0563B)" },
    headline: "דרכים, עם הערות.", pages: 8, stack: "סטטי · ניוזלטר"
  },
  {
    id: "meridian", name: "מרידיאן", genre: "משרד אדריכלות", genreKey: "portfolio",
    price: 12900, sold: false, creator: "דן ק׳", built: "יוני 2026", demo: "demos/meridian/",
    desc: "פורטפוליו של שולחן שרטוט למשרד אדריכלות קטן — פרויקטים בתכנית, בחתך ובאור.",
    story: "מרידיאן מציג בניינים כמו שאדריכלים חושבים עליהם: קודם תכנית, אחר כך צילום. כל פרויקט נפתח כתיק עבודות — שרטוטים, אחר כך מודלים, ולבסוף האור הבנוי. הטיפוגרפיה יושבת על גריד קפדני שאף פעם לא מכריז על עצמו. עמוד המשרד מציג אנשים ועקרונות באותה נשימה, כי במשרד קטן הם אותו הדבר.",
    features: ["תיק עבודות: תכנית ← מודל ← אור", "גריד מודולרי קפדני, שנשמר בשקט", "עמוד משרד ועקרונות", "גיליונות פרויקט מוכנים להדפסה"],
    theme: { bg: "#F1F0EC", ink: "#2B2B28", accent: "#6E6A5E", media: "linear-gradient(135deg,#CFCCC2,#6E6A5E)" },
    headline: "משורטט. ואז נבנה.", pages: 6, stack: "סטטי · תיק עבודות"
  },
  {
    id: "atelier-noir", name: "אטלייה נואר", genre: "סטודיו צילום", genreKey: "portfolio",
    price: 12900, sold: true, creator: "מאיה ר׳", built: "מרץ 2026",
    desc: "נמכר. פורטפוליו כהה כפחם עם גלריות בגרעין פילם וחדר לקוחות פרטי.",
    story: "אטלייה נואר היה היצירה הראשונה שירדה מהמדף. פורטפוליו כהה כפחם שבו הצילומים הם מקור האור היחיד — גלריות בגרעין פילם, חדר לקוחות פרטי מאחורי מפתח אחד, וטיפוגרפיה שנשארת מחוץ לפריים. היום הוא שייך לצלם אחד, מותאם עד לנייר המכתבים. העמוד הזה נשאר כאן כתיעוד בלבד.",
    features: ["גלריות בגרעין פילם, בקצב של חדר חושך", "חדרי לקוחות פרטיים", "כניסה במפתח אחד, בלי חשבונות", "הותאם ונחתם עבור בעליו"],
    theme: { bg: "#191817", ink: "#EDEAE4", accent: "#C9A45C", media: "linear-gradient(135deg,#3B3835,#C9A45C)" },
    headline: "אור, שנשמר.", pages: 5, stack: "סטטי · חדרי לקוחות"
  },
  {
    id: "ledger-vine", name: "לדג׳ר את וויין", genre: "משרד עו״ד בוטיק", genreKey: "professional",
    price: 12900, sold: true, creator: "נועה ב׳", built: "פברואר 2026",
    desc: "נמכר. נוכחות של נייר ודיו למשרד של שני שותפים — רשימות פרקטיקה וטקס יצירת קשר שקול.",
    story: "לדג׳ר את וויין נקרא כמו נייר מכתבים טוב. רשימות פרקטיקה במקום עמודי שירותים, תיקים שנוהלו במקום המלצות, וטקס יצירת קשר שמסנן רצינות בלי להגיד את זה. הוא נקנה בתוך שבוע מהרגע שעלה למדף — על ידי המשרד שהוא שייך לו היום. מותאם, חתום, ומחוץ למדף לתמיד.",
    features: ["רשימות פרקטיקה, לא עמודי שירותים", "טקס יצירת קשר שקול", "מסירת מסמכים מאובטחת", "נחתם עבור משרד של שני שותפים"],
    theme: { bg: "#F0EDE6", ink: "#26303B", accent: "#7A6A45", media: "linear-gradient(135deg,#C8CCC9,#7A6A45)" },
    headline: "ייעוץ, בשקט.", pages: 4, stack: "סטטי · טפסים מאובטחים"
  },
  {
    id: "umbra", name: "אומברה", genre: "בית בושם", genreKey: "commerce",
    price: 12900, sold: true, creator: "מאיה ר׳", built: "ינואר 2026",
    desc: "נמכר. מזון בגווני בין־ערביים לבית בושם בייצור קטן — סיפורי ריח לפני מוצרים.",
    story: "אומברה מוכר ריח דרך המקום שממנו הוא מגיע. כל בושם נפתח כמקום — עונה, שעה, זיכרון — לפני שהוא בכלל מראה בקבוק. החנות עמוקה שלושה עמודים ומרגישה כמו תצוגה פרטית. הוא נרכש על ידי בית הבושם שעבורו הוא נחלם — וכך בדיוק אטלס אמור לעבוד.",
    features: ["סיפורי ריח לפני מוצרים", "חנות של שלושה עמודים, כמו תצוגה פרטית", "תיעוד אצווה לכל בקבוק", "נחתם עבור הבית שלו"],
    theme: { bg: "#1E1A20", ink: "#EAE3EE", accent: "#A98BC4", media: "linear-gradient(135deg,#4A3F52,#A98BC4)" },
    headline: "נלבש אחרי רדת החשיכה.", pages: 5, stack: "סטטי · מסחר"
  }
];

const siteById = id => SITES.find(s => s.id === id) || null;
const money = n => "₪" + n.toLocaleString();

/* ── שמירות (מצב חנות פונקציונלי) ────────────────────────────── */
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

/* ── תבניות כרטיס / תצוגה חיה ────────────────────────────────── */
function previewHTML(site) {
  // pieces with a real demo embed the actual running site, scaled down
  if (site.demo) {
    return `
  <div class="card__frame card__frame--real">
    <div class="card__bar"><i></i><i></i><i></i><em>${site.id}.one · חי</em></div>
    <div class="livewrap">
      <iframe src="${site.demo}" loading="lazy" tabindex="-1" scrolling="no"
              title="${site.name} — אתר חי" aria-hidden="true"></iframe>
    </div>
    <button class="card__live-btn" data-demo="${site.id}">◉ תצוגה חיה</button>
  </div>`;
  }
  const t = site.theme;
  return `
  <div class="card__frame">
    <div class="card__bar"><i></i><i></i><i></i><em>${site.id}.one · חי</em></div>
    <div class="preview" style="background:${t.bg};color:${t.ink}">
      <div class="p-cursor" aria-hidden="true"></div>
      <div class="p-nav">
        <span class="p-logo">${site.name}</span>
        <span class="p-links"><b></b><b></b><b></b></span>
      </div>
      <div class="p-hero">
        <div class="p-head"><span class="p-type">${site.headline}</span></div>
        <div class="p-sub"></div>
        <span class="p-btn" style="background:${t.accent};color:${t.bg}">כניסה</span>
        <span class="p-media" style="--m:${t.media}"></span>
      </div>
      <div class="p-row"><b></b><b></b><b></b></div>
    </div>
    ${site.sold ? '<span class="card__seal" title="נמכר — נחתם">א</span>' : ""}
  </div>`;
}

function statusBadge(site) {
  if (site.sold) return '<span class="badge badge--sold">נמכר</span>';
  if (isReserved(site.id)) return '<span class="badge badge--reserved">שמור</span>';
  return '<span class="badge badge--live">זמין עכשיו</span>';
}

function cardHTML(site) {
  return `
  <a class="card reveal${site.sold ? " card--sold" : ""}" href="site.html?id=${site.id}"
     data-id="${site.id}" aria-label="${site.name} — ${site.sold ? "נמכר" : "זמין"}">
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

/* ── עזרי מדיה ───────────────────────────────────────────────── */
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
    trigger: triggerEl, start: "top top", end: "bottom bottom", scrub: 0.8,
    onUpdate: self => apply(self.progress)
  });
  videoEl.addEventListener("loadedmetadata", () => ScrollTrigger.refresh(), { once: true });
  videoEl.addEventListener("error", () => { videoEl.style.display = "none"; }, { once: true });
}
