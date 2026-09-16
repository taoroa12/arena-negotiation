function esc(s) {
  return (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

async function loadList() {
  const res = await fetch("/admin/scenarios");
  const scenarios = await res.json();
  const list = document.getElementById("scenario-list");

  if (scenarios.length === 0) {
    list.innerHTML = "<div class='empty-state'>Пока пусто — создайте первый сценарий выше.</div>";
    return;
  }

  list.innerHTML = scenarios.map(s => `
    <div class="scenario-item">
      <h4>${esc(s.title)}</h4>
      <div class="meta">${esc(s.sphere)} · ${esc(s.difficulty)} · тон: ${esc(s.tone)}</div>
      <div class="desc">${esc(s.context_description)}</div>
      <button class="secondary" onclick="deleteScenario(${s.id})">Удалить</button>
    </div>
  `).join("");
}

async function deleteScenario(id) {
  if (!confirm("Удалить сценарий?")) return;
  await fetch(`/admin/scenarios/${id}`, { method: "DELETE" });
  loadList();
}

document.getElementById("create-btn").onclick = async () => {
  const body = {
    title: document.getElementById("f-title").value,
    sphere: document.getElementById("f-sphere").value,
    topic: document.getElementById("f-topic").value,
    difficulty: document.getElementById("f-difficulty").value,
    tone: document.getElementById("f-tone").value,
    opponent_role: document.getElementById("f-role").value,
    opponent_goals: document.getElementById("f-goals").value,
    context_description: document.getElementById("f-context").value,
  };
  if (!body.title || !body.sphere || !body.topic) {
    alert("Заполните хотя бы название, сферу и тему");
    return;
  }
  await fetch("/admin/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  ["f-title","f-sphere","f-topic","f-role","f-goals","f-context"].forEach(id => document.getElementById(id).value = "");
  loadList();
};

loadList();