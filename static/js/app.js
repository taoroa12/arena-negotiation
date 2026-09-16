let sessionId = null;
let rounds = 0;

const scenarioSelect = document.getElementById("scenario-select");
const chatBox = document.getElementById("chat-box");
const setupCard = document.getElementById("setup-card");
const chatCard = document.getElementById("chat-card");
const feedbackCard = document.getElementById("feedback-card");
const opponentBrief = document.getElementById("opponent-brief");

function esc(s) {
  return (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

async function loadScenarios() {
  const res = await fetch("/admin/scenarios");
  const scenarios = await res.json();
  if (scenarios.length === 0) {
    scenarioSelect.innerHTML = "<option value=''>Нет доступных сценариев — создайте в админке</option>";
    return;
  }
  scenarioSelect.innerHTML = scenarios.map(s => `
    <option value="${s.id}" data-role="${esc(s.opponent_role)}" data-title="${esc(s.title)}" data-tone="${esc(s.tone)}" data-difficulty="${esc(s.difficulty)}">
      ${esc(s.title)} (${esc(s.sphere)}, ${esc(s.difficulty)})
    </option>`).join("");
}

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "opponent");
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function updateTension(n) {
  rounds = n;
  const pct = Math.min(10 + rounds * 15, 100);
  document.getElementById("tension-fill").style.width = pct + "%";
  const label = pct < 35 ? "спокойно" : pct < 70 ? "накаляется" : "на пределе";
  document.getElementById("tension-value").textContent = label;
}

document.getElementById("start-btn").onclick = async () => {
  const userName = document.getElementById("user-name").value || "Гость";
  const opt = scenarioSelect.selectedOptions[0];
  const scenarioId = parseInt(scenarioSelect.value);
  if (!scenarioId) { alert("Выберите сценарий"); return; }

  const res = await fetch("/sessions/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId, user_name: userName }),
  });
  const data = await res.json();
  sessionId = data.session_id;

  const seal = document.createElement("div");
  seal.className = "seal";
  seal.textContent = "Начато";
  document.body.appendChild(seal);
  setTimeout(() => seal.remove(), 600);

  opponentBrief.innerHTML = `<span>${esc(opt.dataset.title)}</span><b>${esc(opt.dataset.role)} · тон: ${esc(opt.dataset.tone)}</b>`;

  setupCard.style.display = "none";
  chatCard.style.display = "block";
  chatBox.innerHTML = "";
  updateTension(0);
  addBubble("opponent", data.opening_message);
};

async function sendMessage() {
  const input = document.getElementById("msg-input");
  const text = input.value.trim();
  if (!text || !sessionId) return;

  addBubble("user", text);
  input.value = "";

  const res = await fetch(`/sessions/${sessionId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: text }),
  });
  const data = await res.json();
  addBubble("opponent", data.reply);
  updateTension(rounds + 1);
}

document.getElementById("send-btn").onclick = sendMessage;
document.getElementById("msg-input").addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});

document.getElementById("finish-btn").onclick = async () => {
  if (!sessionId) return;
  const res = await fetch(`/sessions/${sessionId}/finish`, { method: "POST" });
  const fb = await res.json();

  chatCard.style.display = "none";
  feedbackCard.style.display = "block";
  feedbackCard.innerHTML = `
    <h3>Итог переговоров</h3>
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
};

loadScenarios();