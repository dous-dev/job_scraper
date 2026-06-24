const API = {
  sources: "/api/sources",
  search: "/api/search",
};

const els = {
  form: document.getElementById("search-form"),
  query: document.getElementById("query"),
  location: document.getElementById("location"),
  remote: document.getElementById("remote-only"),
  btn: document.getElementById("search-btn"),
  sources: document.getElementById("sources"),
  results: document.getElementById("results"),
  status: document.getElementById("status-bar"),
  empty: document.getElementById("empty-state"),
  template: document.getElementById("card-template"),
};

const state = {
  activeSources: new Set(),
  loading: false,
};

init();

async function init() {
  bindExamples();
  els.form.addEventListener("submit", onSearch);
  await loadSources();
}

async function loadSources() {
  try {
    const res = await fetch(API.sources);
    const sources = await res.json();
    els.sources.querySelectorAll(".chip-source").forEach((c) => c.remove());
    sources.forEach((s) => {
      state.activeSources.add(s.id);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip-source";
      chip.dataset.id = s.id;
      chip.dataset.kind = s.kind;
      chip.dataset.active = "true";
      chip.innerHTML = `<span class="kind-dot"></span>${s.name}`;
      chip.title = s.kind === "it" ? "Źródło branżowe IT" : "Źródło ogólne (wszystkie branże)";
      chip.addEventListener("click", () => toggleSource(chip, s.id));
      els.sources.appendChild(chip);
    });
  } catch (err) {
    console.warn("Nie udało się pobrać listy źródeł:", err);
  }
}

function toggleSource(chip, id) {
  if (state.activeSources.has(id)) {
    state.activeSources.delete(id);
    chip.dataset.active = "false";
  } else {
    state.activeSources.add(id);
    chip.dataset.active = "true";
  }
}

function bindExamples() {
  document.querySelectorAll(".chip-example").forEach((btn) => {
    btn.addEventListener("click", () => {
      els.query.value = btn.dataset.q;
      els.form.requestSubmit();
    });
  });
}

async function onSearch(event) {
  event.preventDefault();
  if (state.loading) return;

  const query = els.query.value.trim();
  if (!query) {
    els.query.focus();
    return;
  }

  if (state.activeSources.size === 0) {
    showStatus("Wybierz przynajmniej jedno źródło.", { error: true });
    return;
  }

  setLoading(true);
  els.empty.style.display = "none";
  renderSkeletons();

  const payload = {
    query,
    location: els.location.value.trim() || null,
    remote_only: els.remote.checked,
    sources: Array.from(state.activeSources),
  };

  try {
    const res = await fetch(API.search, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    console.error(err);
    els.results.innerHTML = "";
    showStatus("Wystąpił błąd podczas wyszukiwania. Spróbuj ponownie.", { error: true });
  } finally {
    setLoading(false);
  }
}

function setLoading(loading) {
  state.loading = loading;
  els.btn.disabled = loading;
  els.btn.querySelector(".btn-label").textContent = loading ? "Szukam…" : "Szukaj";
  els.btn.querySelector(".spinner").hidden = !loading;
}

function renderSkeletons(count = 6) {
  els.status.hidden = true;
  els.results.innerHTML = "";
  for (let i = 0; i < count; i++) {
    const card = document.createElement("article");
    card.className = "job-card skeleton";
    card.innerHTML = `
      <div class="job-card-head">
        <div class="sk" style="width:44px;height:44px;border-radius:11px;"></div>
        <div style="flex:1;display:flex;flex-direction:column;gap:8px;">
          <div class="sk" style="height:16px;width:80%;"></div>
          <div class="sk" style="height:12px;width:50%;"></div>
        </div>
      </div>
      <div class="sk" style="height:12px;width:100%;"></div>
      <div class="sk" style="height:12px;width:90%;"></div>
      <div class="sk" style="height:12px;width:60%;"></div>`;
    els.results.appendChild(card);
  }
}

function renderResults(data) {
  const terms = tokenize(data.parsed_keywords || data.query);

  if (!data.results || data.results.length === 0) {
    els.results.innerHTML = "";
    showStatus(`Brak wyników dla „${data.query}”. Spróbuj innych słów kluczowych.`, { error: false });
    els.empty.style.display = "block";
    els.empty.querySelector("h2").textContent = "Brak wyników";
    els.empty.querySelector("p").textContent = "Zmień zapytanie lub rozszerz wybrane źródła.";
    return;
  }

  const bySource = (data.by_source || [])
    .map((s) => `<span class="pill">${s.source}: ${s.count}</span>`)
    .join("");
  showStatus(
    `<span class="count">${data.total} ofert</span> dla „${escapeHtml(data.query)}”` +
      (data.parsed_location ? ` • 📍 ${escapeHtml(data.parsed_location)}` : "") +
      (data.remote_only ? " • 🏠 tylko zdalne" : "") +
      ` ${bySource}` +
      `<span class="took">${(data.took_ms / 1000).toFixed(1)}s</span>`,
    { error: false, html: true }
  );

  els.results.innerHTML = "";
  data.results.forEach((job, idx) => {
    els.results.appendChild(buildCard(job, terms, idx));
  });
}

function buildCard(job, terms, idx) {
  const node = els.template.content.cloneNode(true);
  const card = node.querySelector(".job-card");
  card.style.animationDelay = `${Math.min(idx * 0.03, 0.4)}s`;

  const logo = node.querySelector(".job-logo");
  if (job.logo) {
    logo.style.backgroundImage = `url("${job.logo}")`;
    logo.textContent = "";
  } else {
    logo.textContent = (job.company && job.company !== "—" ? job.company : job.source).charAt(0).toUpperCase();
  }

  node.querySelector(".job-title").innerHTML = highlight(job.title, terms);
  node.querySelector(".job-company").textContent = job.company || "—";

  const badge = node.querySelector(".source-badge");
  badge.textContent = job.source;

  const loc = node.querySelector(".job-location");
  loc.textContent = job.location ? `📍 ${job.location}` : "📍 —";

  const salary = node.querySelector(".job-salary");
  if (job.salary) {
    salary.textContent = `💰 ${job.salary}`;
    salary.hidden = false;
  }

  const remote = node.querySelector(".job-remote");
  if (job.remote) remote.hidden = false;

  const desc = node.querySelector(".job-desc");
  if (job.description) {
    desc.innerHTML = highlight(job.description, terms);
  } else {
    desc.remove();
  }

  const score = node.querySelector(".job-score");
  score.innerHTML = `Trafność <b>${job.score.toFixed(1)}</b>`;

  const open = node.querySelector(".btn-open");
  open.href = job.url;

  return node;
}

/* ---------- helpers ---------- */

function tokenize(text) {
  // Zachowujemy polskie znaki, by podświetlanie trafiało w słowa z diakrytykami.
  return (
    (text || "")
      .toLowerCase()
      .match(/[0-9a-ząćęłńóśźż\+\#]+/g)
      ?.filter((t) => t.length > 1) || []
  );
}

function highlight(text, terms) {
  let safe = escapeHtml(text);
  if (!terms || terms.length === 0) return safe;
  const unique = [...new Set(terms)].sort((a, b) => b.length - a.length);
  for (const term of unique) {
    const re = new RegExp(`(${escapeRegex(term)})`, "gi");
    safe = safe.replace(re, "<mark>$1</mark>");
  }
  return safe;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function showStatus(html, { error = false, html: isHtml = false } = {}) {
  els.status.hidden = false;
  els.status.classList.toggle("error", error);
  if (isHtml) els.status.innerHTML = html;
  else els.status.textContent = html;
}
