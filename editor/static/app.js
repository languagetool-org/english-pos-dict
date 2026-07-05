"use strict";

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { status: r.status, data: await r.json() };
}

function renderValidation(problems) {
  const ul = document.getElementById("problems");
  ul.innerHTML = "";
  if (!problems.length) {
    const li = document.createElement("li");
    li.className = "ok";
    li.textContent = "✓ valid";
    ul.appendChild(li);
    return;
  }
  for (const p of problems) {
    const li = document.createElement("li");
    li.textContent = p;
    ul.appendChild(li);
  }
}

function renderExpansion(rows) {
  const tb = document.getElementById("expansion");
  tb.innerHTML = "";
  for (const [form, lemma, tag, variants] of rows) {
    const tr = document.createElement("tr");
    for (const cell of [form, lemma, tag, variants]) {
      const td = document.createElement("td");
      td.className = "mono";
      td.textContent = cell;
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
}

function renderEvidence(result) {
  const box = document.getElementById("evidence");
  box.classList.remove("muted");
  let html = "";
  if (result.disagreement) {
    html += `<div class="banner-warn">Suggests <span class="tag">${esc(result.suggestion_tag)}</span> `
      + `(${esc(result.suggestion)}, ${esc(result.confidence)}) — differs from current tags. `
      + `<button id="apply-btn" data-tag="${esc(result.suggestion_tag)}">Apply tag</button></div>`;
  }
  html += "<table><thead><tr><th>Source</th><th>Verdict</th><th>Confidence</th><th>Detail</th></tr></thead><tbody>";
  for (const ev of result.verdicts) {
    const d = ev.detail || {};
    let detail = "";
    if (ev.source === "corpus" && d.available) {
      detail = `plural ${d.plural_hits}/${d.noun_hits} (rate ${(d.plural_rate || 0).toFixed(3)})`;
    } else if (ev.source === "becl") {
      detail = d.becl_class || (d.found === false ? "not in BECL" : "");
    } else if (ev.source === "wiktionary") {
      detail = d.found ? "wikitext markers" : "no entry";
    }
    html += `<tr><td>${esc(ev.source)}</td><td>${esc(ev.verdict)}</td><td>${esc(ev.confidence)}</td><td class="muted">${esc(detail)}</td></tr>`;
  }
  html += "</tbody></table>";
  box.innerHTML = html;

  const applyBtn = document.getElementById("apply-btn");
  if (applyBtn) {
    applyBtn.addEventListener("click", () => applySuggestedTag(applyBtn.dataset.tag));
  }
}

function applySuggestedTag(tag) {
  // Replace an existing NN / NN:U / NN:UN singular tag in the line with the suggestion.
  const input = document.getElementById("line");
  input.value = input.value.replace(/NN:UN|NN:U|NN(?![A-Z:])/, tag);
  input.dispatchEvent(new Event("input"));
}

function initEditor() {
  const editor = document.querySelector(".editor");
  if (!editor) return;
  const input = document.getElementById("line");
  const { file, line, lemma } = editor.dataset;

  const validate = debounce(async () => {
    const { data } = await postJSON("/api/validate", { line: input.value });
    renderValidation(data.problems);
    renderExpansion(data.expansion);
  }, 250);
  input.addEventListener("input", validate);
  validate();

  document.getElementById("save-btn").addEventListener("click", async () => {
    const status = document.getElementById("save-status");
    const { status: code, data } = await postJSON("/api/save", {
      file, line_no: parseInt(line, 10), line: input.value,
    });
    if (code === 200) {
      status.textContent = "✓ saved";
    } else if (code === 409) {
      status.textContent = "⚠ file changed on disk — reload";
    } else {
      status.textContent = "✗ " + (data.error || "not saved");
    }
  });

  const evBtn = document.getElementById("evidence-btn");
  const loadEvidence = async () => {
    const box = document.getElementById("evidence");
    box.textContent = "Loading…";
    const r = await fetch(`/api/evidence/${encodeURIComponent(lemma)}`);
    renderEvidence(await r.json());
  };
  evBtn.addEventListener("click", loadEvidence);
  if (evBtn.dataset.auto === "1") loadEvidence();
}

function initRescan() {
  const form = document.getElementById("rescan-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.getElementById("rescan-status");
    status.textContent = "scanning…";
    const { data } = await postJSON("/api/rescan", {});
    status.textContent = `✓ ${data.count} issues — reload to view`;
  });
}

document.addEventListener("DOMContentLoaded", () => { initEditor(); initRescan(); });
