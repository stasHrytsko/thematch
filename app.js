/* ================================================================== */
/* TheMatch PWA — app.js                                               */
/* All UI logic: form handling, API calls, results rendering           */
/* ================================================================== */

"use strict";

// ------------------------------------------------------------------ //
// Constants                                                            //
// ------------------------------------------------------------------ //
const API_URL = "/api/compatibility";
const SVG_NS  = "http://www.w3.org/2000/svg";

// Ring geometry
const RING_LARGE_R  = 70;  // radius for the hero ring
const RING_LARGE_SZ = 160; // SVG viewport size

// ------------------------------------------------------------------ //
// DOM refs (resolved after DOMContentLoaded)                           //
// ------------------------------------------------------------------ //
let $formSection, $resultsSection, $date1, $date2, $calcBtn, $errorBox;
let deferredInstallPrompt = null;

// ------------------------------------------------------------------ //
// Bootstrap                                                            //
// ------------------------------------------------------------------ //
document.addEventListener("DOMContentLoaded", () => {
  $formSection    = document.getElementById("form-section");
  $resultsSection = document.getElementById("results-section");
  $date1          = document.getElementById("date1");
  $date2          = document.getElementById("date2");
  $calcBtn        = document.getElementById("calc-btn");
  $errorBox       = document.getElementById("error-box");

  // Restrict date inputs to past dates only
  const today = new Date().toISOString().split("T")[0];
  $date1.setAttribute("max", today);
  $date2.setAttribute("max", today);
  $date1.setAttribute("min", "1900-01-01");
  $date2.setAttribute("min", "1900-01-01");

  $calcBtn.addEventListener("click", handleCalculate);

  registerServiceWorker();
  listenForInstallPrompt();
});

// ------------------------------------------------------------------ //
// Service Worker registration                                          //
// ------------------------------------------------------------------ //
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .register("/sw.js")
      .catch((err) => console.warn("SW registration failed:", err));
  }
}

// ------------------------------------------------------------------ //
// PWA install prompt                                                   //
// ------------------------------------------------------------------ //
function listenForInstallPrompt() {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    showInstallBanner();
  });
}

function showInstallBanner() {
  const banner = document.createElement("div");
  banner.className = "install-banner";
  banner.innerHTML = `
    <span class="install-icon">📲</span>
    <div class="install-copy">
      <strong>Установить приложение</strong>
      <span>Работает без интернета</span>
    </div>
    <button class="btn-install" id="install-btn">Установить</button>
  `;
  $formSection.prepend(banner);

  document.getElementById("install-btn").addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    const { outcome } = await deferredInstallPrompt.userChoice;
    if (outcome === "accepted") banner.remove();
    deferredInstallPrompt = null;
  });
}

// ------------------------------------------------------------------ //
// Form handling                                                        //
// ------------------------------------------------------------------ //
function handleCalculate() {
  clearError();

  const d1 = $date1.value;
  const d2 = $date2.value;

  if (!d1) { showError("Введите вашу дату рождения"); $date1.focus(); return; }
  if (!d2) { showError("Введите дату рождения партнёра"); $date2.focus(); return; }

  if (d1 === d2) {
    showError("Даты совпадают — введите разные даты рождения");
    return;
  }

  const apiDate1 = isoToDMY(d1);
  const apiDate2 = isoToDMY(d2);

  setLoading(true);
  fetchCompatibility(apiDate1, apiDate2)
    .then((result) => {
      setLoading(false);
      renderResults(result);
    })
    .catch((err) => {
      setLoading(false);
      showError(err.message || "Ошибка расчёта. Попробуйте ещё раз.");
    });
}

async function fetchCompatibility(date1, date2) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date1, date2 }),
  });

  const json = await res.json();
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

// ------------------------------------------------------------------ //
// State helpers                                                        //
// ------------------------------------------------------------------ //
function setLoading(on) {
  $calcBtn.disabled = on;
  $calcBtn.textContent = on ? "⏳ Рассчитываем…" : "🔮 Рассчитать совместимость";
}

function showError(msg) {
  $errorBox.textContent = msg;
  $errorBox.classList.remove("hidden");
}

function clearError() {
  $errorBox.classList.add("hidden");
  $errorBox.textContent = "";
}

function resetForm() {
  $resultsSection.classList.add("hidden");
  $resultsSection.innerHTML = "";
  $formSection.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ------------------------------------------------------------------ //
// Date helpers                                                         //
// ------------------------------------------------------------------ //
function isoToDMY(iso) {
  // "2000-12-25" → "25.12.2000"
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

// ------------------------------------------------------------------ //
// Results rendering                                                    //
// ------------------------------------------------------------------ //
function renderResults(data) {
  $formSection.classList.add("hidden");

  $resultsSection.innerHTML = [
    buildHero(data),
    buildZodiacCard(data.zodiac),
    buildBiorhythmCard(data.biorhythm),
    buildNumerologyCard(data.numerology),
    `<button class="btn-secondary mt-8" onclick="resetForm()">↩️ Новый расчёт</button>`,
  ].join("");

  $resultsSection.classList.remove("hidden");

  // Trigger progress bar animations after the DOM is painted
  requestAnimationFrame(() => {
    animateRing("hero-ring", RING_LARGE_R, data.total);
    animateBars();
  });

  $resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ------------------------------------------------------------------ //
// Hero score ring                                                      //
// ------------------------------------------------------------------ //
function buildHero(data) {
  const c = 2 * Math.PI * RING_LARGE_R; // circumference ≈ 439.82
  return `
    <div class="results-hero">
      <p class="hero-label">✨ Общая совместимость</p>
      <div class="ring-wrap">
        <svg width="${RING_LARGE_SZ}" height="${RING_LARGE_SZ}"
             viewBox="0 0 ${RING_LARGE_SZ} ${RING_LARGE_SZ}"
             style="filter:drop-shadow(0 0 24px rgba(124,58,237,0.45))">
          <defs>
            <linearGradient id="grad-hero" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stop-color="#7C3AED"/>
              <stop offset="100%" stop-color="#EC4899"/>
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="${RING_LARGE_R}"
                  fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="12"/>
          <circle id="hero-ring" cx="80" cy="80" r="${RING_LARGE_R}"
                  fill="none" stroke="url(#grad-hero)" stroke-width="12"
                  stroke-linecap="round"
                  stroke-dasharray="${c.toFixed(2)}"
                  stroke-dashoffset="${c.toFixed(2)}"
                  style="transform:rotate(-90deg);transform-origin:center;
                         transition:stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)"/>
        </svg>
        <div class="ring-center">
          <span class="ring-pct">${data.total}%</span>
          <span class="ring-emoji">${data.total_emoji}</span>
        </div>
      </div>
      <p class="hero-phrase">«${data.total_phrase}»</p>
    </div>`;
}

function animateRing(id, radius, score) {
  const el = document.getElementById(id);
  if (!el) return;
  const c = 2 * Math.PI * radius;
  el.style.strokeDashoffset = (c * (1 - score / 100)).toFixed(2);
}

// ------------------------------------------------------------------ //
// Zodiac card                                                          //
// ------------------------------------------------------------------ //
function buildZodiacCard(z) {
  return `
    <div class="card">
      <div class="section-header">
        <span class="section-title">🔯 Зодиак</span>
        <span class="section-score">${z.score}%</span>
      </div>

      <div class="sign-pair">
        <div class="sign-item">
          <div class="sign-symbol">${z.sign1}</div>
          <div class="sign-name">${z.sign1_name}</div>
          <div class="sign-desc">${z.sign1_description}</div>
        </div>
        <div class="sign-sep">💕</div>
        <div class="sign-item">
          <div class="sign-symbol">${z.sign2}</div>
          <div class="sign-name">${z.sign2_name}</div>
          <div class="sign-desc">${z.sign2_description}</div>
        </div>
      </div>

      <div class="divider"></div>

      ${scoreRow("Совместимость знаков", z.signs_score, `${z.signs_emoji}`)}
      ${scoreRow(
        `${z.element1_emoji} ${z.element1} + ${z.element2_emoji} ${z.element2}`,
        z.elements_score,
        `${z.elements_emoji}`
      )}

      <p class="phrase">«${z.signs_phrase}»<br>«${z.elements_phrase}»</p>
    </div>`;
}

// ------------------------------------------------------------------ //
// Biorhythm card                                                       //
// ------------------------------------------------------------------ //
const RHYTHM_LABELS = {
  heart:     "❤️ Сердечный (эмоции)",
  intuitive: "🔮 Интуитивный (понимание)",
  higher:    "✨ Высший (духовность)",
};

function buildBiorhythmCard(b) {
  const rhythmRows = Object.entries(b.rhythms)
    .map(([key, r]) =>
      scoreRow(RHYTHM_LABELS[key] || key, r.score, r.emoji)
    )
    .join("");

  return `
    <div class="card">
      <div class="section-header">
        <span class="section-title">💫 Биоритмы</span>
        <span class="section-score">${b.score}% ${b.score_emoji}</span>
      </div>

      ${rhythmRows}

      <p class="phrase">«${b.total_description}»</p>
    </div>`;
}

// ------------------------------------------------------------------ //
// Numerology card                                                      //
// ------------------------------------------------------------------ //
function buildNumerologyCard(n) {
  const { emoji: emoji1, text: desc1 } = splitEmojiText(n.number1_description);
  const { emoji: emoji2, text: desc2 } = splitEmojiText(n.number2_description);

  return `
    <div class="card">
      <div class="section-header">
        <span class="section-title">🔢 Нумерология</span>
        <span class="section-score">${n.score}% ${n.score_emoji}</span>
      </div>

      <div class="number-pair">
        <div class="number-card">
          <div class="number-val">${emoji1 || n.number1}</div>
          <div class="number-desc">${desc1}</div>
        </div>
        <div class="number-card">
          <div class="number-val">${emoji2 || n.number2}</div>
          <div class="number-desc">${desc2}</div>
        </div>
      </div>

      <div class="partnership-box">
        <div class="partnership-label">Число союза</div>
        <div class="partnership-val">${n.partnership_number}</div>
        <div class="partnership-desc">«${n.partnership_description}»</div>
      </div>

      <p class="phrase">«${n.phrase}»</p>
    </div>`;
}

// ------------------------------------------------------------------ //
// Shared score-row builder                                             //
// ------------------------------------------------------------------ //
function scoreRow(label, score, badge) {
  return `
    <div class="score-row">
      <span class="score-label">${label}</span>
      <span class="score-val">${score}% ${badge}</span>
      <div class="score-bar-track">
        <div class="score-bar-fill" data-score="${score}"></div>
      </div>
    </div>`;
}

function animateBars() {
  document.querySelectorAll(".score-bar-fill").forEach((el) => {
    const score = parseFloat(el.dataset.score) || 0;
    el.style.width = `${Math.min(score, 100)}%`;
  });
}

// ------------------------------------------------------------------ //
// Emoji helpers                                                        //
// ------------------------------------------------------------------ //
function splitEmojiText(str) {
  if (!str) return { emoji: "", text: "" };
  const match = str.match(/^(\S+)\s+(.*)/s);
  return match ? { emoji: match[1], text: match[2].trim() } : { emoji: "", text: str };
}
