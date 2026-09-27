let sessionId = null;
let rounds = 0;
let roundScore = 0;
let isBusy = false;

const scenarioSelect = document.getElementById("scenario-select");
const chatBox = document.getElementById("chat-box");
const setupCard = document.getElementById("setup-card");
const chatCard = document.getElementById("chat-card");
const feedbackCard = document.getElementById("feedback-card");
const opponentBriefText = document.getElementById("opponent-brief-text");
const moodFace = document.getElementById("mood-face");
const typingRow = document.getElementById("typing-row");
const startBtn = document.getElementById("start-btn");
const sendBtn = document.getElementById("send-btn");
const finishBtn = document.getElementById("finish-btn");
const msgInput = document.getElementById("msg-input");

function esc(s) {
  return (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function setBusy(busy, label) {
  isBusy = busy;
  [startBtn, sendBtn, finishBtn].forEach(b => { if (b) b.disabled = busy; });
  if (msgInput) msgInput.disabled = busy;
  if (busy && label && sendBtn) {
    sendBtn.dataset.originalText = sendBtn.textContent;
    sendBtn.textContent = label;
  } else if (!busy && sendBtn && sendBtn.dataset.originalText) {
    sendBtn.textContent = sendBtn.dataset.originalText;
  }
}

function getXP() { return parseInt(localStorage.getItem("arena_xp") || "0", 10); }
function setXP(v) { localStorage.setItem("arena_xp", String(v)); }
function levelFromXP(xp) { return Math.floor(xp / 100) + 1; }
function rankName(level) {
  if (level <= 2) return "Новичок";
  if (level <= 4) return "Практик";
  if (level <= 7) return "Профи";
  return "Мастер";
}
function renderRank() {
  const xp = getXP();
  const level = levelFromXP(xp);
  const xpIntoLevel = xp % 100;
  document.getElementById("rank-badge").textContent = `${rankName(level)} · уровень ${level}`;
  document.getElementById("rank-xp-text").textContent = `${xp} XP`;
  document.getElementById("rank-next-text").textContent = `до следующего уровня: ${100 - xpIntoLevel}`;
  document.getElementById("rank-fill").style.width = xpIntoLevel + "%";
}

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "opponent");
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function scoreMessage(text) {
  let pts = Math.min(5, Math.max(1, Math.round(text.length / 25)));
  if (/\d/.test(text)) pts += 2;
  if (text.includes("?")) pts += 1;
  return pts;
}

function updateTension(n) {
  rounds = n;
  const pct = Math.min(10 + rounds * 15, 100);
  document.getElementById("tension-fill").style.width = pct + "%";
  const label = pct < 35 ? "спокойно" : pct < 70 ? "накаляется" : "на пределе";
  document.getElementById("tension-value").textContent = label;
  moodFace.textContent = pct < 35 ? "🙂" : pct < 70 ? "😐" : "😠";
}

function fireConfetti() {
  const layer = document.getElementById("confetti-layer");
  const colors = ["#c9974b", "#a67632", "#ece7da"];
  for (let i = 0; i < 40; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "vw";
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = (Math.random() * 0.3) + "s";
    layer.appendChild(piece);
    setTimeout(() => piece.remove(), 1800);
  }
}

async function loadScenarios() {
  const res = await fetch("/admin/scenarios");
  const scenarios = await res.json();
  if (scenarios.length === 0) {
    scenarioSelect.innerHTML = "<option value=''>Нет доступных сценариев</option>";
    return;
  }
  scenarioSelect.innerHTML = scenarios.map(s => `
    <option value="${s.id}" data-role="${esc(s.opponent_role)}" data-title="${esc(s.title)}" data-tone="${esc(s.tone)}">
      ${esc(s.title)} (${esc(s.sphere)}, ${esc(s.difficulty)})
    </option>`).join("");
}

startBtn.onclick = async () => {
  if (isBusy) return;
  const userName = document.getElementById("user-name").value || "Гость";
  const opt = scenarioSelect.selectedOptions[0];
  const scenarioId = parseInt(scenarioSelect.value);
  if (!scenarioId) { alert("Выберите сценарий"); return; }

  setBusy(true);
  startBtn.textContent = "Оппонент готовится...";

  try {
    const res = await fetch("/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId, user_name: userName }),
    });
    const data = await res.json();
    sessionId = data.session_id;
    roundScore = 0;

    const seal = document.createElement("div");
    seal.className = "seal";
    seal.textContent = "Начато";
    document.body.appendChild(seal);
    setTimeout(() => seal.remove(), 600);

    opponentBriefText.innerHTML = `<span>${esc(opt.dataset.title)}</span> · <b>${esc(opt.dataset.role)} · тон: ${esc(opt.dataset.tone)}</b>`;

    setupCard.style.display = "none";
    chatCard.style.display = "block";
    chatBox.innerHTML = "";
    updateTension(0);
    document.getElementById("round-score").textContent = "Очки раунда: 0";
    addBubble("opponent", data.opening_message);
  } finally {
    setBusy(false);
    startBtn.textContent = "Начать переговоры";
  }
};

async function sendMessage() {
  if (isBusy) return;
  const text = msgInput.value.trim();
  if (!text || !sessionId) return;

  addBubble("user", text);
  msgInput.value = "";
  roundScore += scoreMessage(text);
  document.getElementById("round-score").textContent = `Очки раунда: ${roundScore}`;

  setBusy(true, "Ждём ответ...");
  typingRow.style.display = "flex";
  chatBox.scrollTop = chatBox.scrollHeight;

  try {
    const res = await fetch(`/sessions/${sessionId}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text }),
    });
    const data = await res.json();
    typingRow.style.display = "none";
    addBubble("opponent", data.reply);
    updateTension(rounds + 1);
  } finally {
    setBusy(false);
  }
}

sendBtn.onclick = sendMessage;
msgInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !isBusy) sendMessage();
});

finishBtn.onclick = async () => {
  if (!sessionId || isBusy) return;
  setBusy(true);
  finishBtn.textContent = "Готовим разбор...";

  try {
    const res = await fetch(`/sessions/${sessionId}/finish`, { method: "POST" });
    const fb = await res.json();

    chatCard.style.display = "none";
    feedbackCard.style.display = "block";

    const avgScore = (fb.score_goal + fb.score_argumentation + fb.score_empathy + fb.score_tactics) / 4;
    const gainedXP = Math.round(avgScore * 10) + roundScore;
    const xpBefore = getXP();
    const levelBefore = levelFromXP(xpBefore);
    const xpAfter = xpBefore + gainedXP;
    setXP(xpAfter);
    const levelAfter = levelFromXP(xpAfter);
    const leveledUp = levelAfter > levelBefore;

    feedbackCard.innerHTML = `
      <h3>Итог переговоров</h3>
      <div class="deal-outcome"><b>${esc(fb.deal_status)}</b><div>${esc(fb.deal_terms)}</div></div>
      <div class="xp-gain">+${gainedXP} XP ${leveledUp ? `<span class="level-up">Новый уровень: ${rankName(levelAfter)}!</span>` : ""}</div>
      <p>${esc(fb.summary)}</p>
      <p><b>Сильные стороны:</b> ${esc(fb.strengths)}</p>
      <p><b>Точки роста:</b> ${esc(fb.weaknesses)}</p>
      <div class="score-list">
        <div class="score-item"><div class="score-top"><span>Достижение цели</span><b>${fb.score_goal}/10</b></div><div class="score-track"><div data-w="${fb.score_goal * 10}"></div></div></div>
        <div class="score-item"><div class="score-top"><span>Аргументация</span><b>${fb.score_argumentation}/10</b></div><div class="score-track"><div data-w="${fb.score_argumentation * 10}"></div></div></div>
        <div class="score-item"><div class="score-top"><span>Эмпатия</span><b>${fb.score_empathy}/10</b></div><div class="score-track"><div data-w="${fb.score_empathy * 10}"></div></div></div>
        <div class="score-item"><div class="score-top"><span>Тактика</span><b>${fb.score_tactics}/10</b></div><div class="score-track"><div data-w="${fb.score_tactics * 10}"></div></div></div>
      </div>
      <button class="secondary" onclick="location.reload()">Пройти ещё раз</button>
    `;

    requestAnimationFrame(() => {
      feedbackCard.querySelectorAll(".score-track div").forEach(el => {
        el.style.width = el.dataset.w + "%";
      });
    });

    if (leveledUp) fireConfetti();
    renderRank();
  } finally {
    setBusy(false);
  }
};

renderRank();
loadScenarios();