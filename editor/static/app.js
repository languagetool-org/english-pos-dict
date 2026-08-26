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
  // Per-source status line (both corpus endpoints)
  for (const src of ["corpus", "bcql"]) {
    const ev = result.verdicts.find(v => v.source === src);
    if (!ev) continue;
    const d = ev.detail || {};
    const on = d.available && d.source_url;
    const statusColor = on ? "var(--tag-ok, #4a7c59)" : "var(--tag-warn, #c65f5f)";
    html += `<p style="margin: .4rem 0; font-size: .85rem;">
                ${src}: <span style="color: var(--muted, #666);" class="mono">${esc(d.source_url || 'not configured')}</span> (<span style="color: ${statusColor}">${on ? "On" : "Off"}</span>)
              </p>`;
  }
  html += "<table><thead><tr><th>Source</th><th>Verdict</th><th>Confidence</th><th>Detail</th></tr></thead><tbody>";
  for (const ev of result.verdicts) {
    const d = ev.detail || {};
    let detail = "";
    if (ev.source === "corpus" && d.available) {
      detail = `plural ${d.plural_hits}/${d.noun_hits} (rate ${(d.plural_rate || 0).toFixed(3)})`;
    } else if (ev.source === "bcql" && d.available) {
      const parts = [];
      if (d.anchored_hits != null) parts.push(`a/an+punct ${d.anchored_hits}`);
      if (d.quantifier_hits != null) parts.push(`much/little ${d.quantifier_hits}`);
      if (d.det_hits != null) parts.push(`a/an ${d.det_hits}/${d.noun_hits} (${(d.det_rate || 0).toFixed(4)})`);
      detail = `${d.test || ""}: ${parts.join(" · ")}`;
    } else if (ev.source === "becl") {
      detail = d.becl_class || (d.found === false ? "not in BECL" : "");
    } else if (ev.source === "wiktionary") {
      detail = d.found ? "wikitext markers" : "no entry";
    } else if (ev.source === "esdb") {
      detail = d.note || "";
    }
    html += `<tr><td>${esc(ev.source)}</td><td>${esc(ev.verdict)}</td><td>${esc(ev.confidence)}</td><td class="muted">${esc(detail)}</td></tr>`;
  }
  html += "</tbody></table>";
  if (result.plural_tantum) {
    html = `<div class="banner-warn">Plurale tantum: <b>${esc(result.plural_tantum_plural)}</b> is the only noun form; <i>${esc(result.lemma)}</i> (naive singular) is not a real noun. <button id="replace-plural-btn" data-lemma="${esc(result.plural_tantum_plural)}">Use plural</button></div>` + html;
  }
  box.innerHTML = html;

  const applyBtn = document.getElementById("apply-btn");
  if (applyBtn) {
    applyBtn.addEventListener("click", () => applySuggestedTag(applyBtn.dataset.tag));
  }
  const replacePluralBtn = document.getElementById("replace-plural-btn");
  if (replacePluralBtn) {
    replacePluralBtn.addEventListener("click", () => {
      const input = document.getElementById("line");
      input.value = `${replacePluralBtn.dataset.lemma}=NNS=all`;
      input.dispatchEvent(new Event("input"));
    });
  }
}

function applySuggestedTag(tag) {
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

  const saveEntry = async () => {
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
  };
  document.getElementById("save-btn").addEventListener("click", saveEntry);

  const evBtn = document.getElementById("evidence-btn");
  const loadEvidence = async () => {
    const box = document.getElementById("evidence");
    box.textContent = "Loading…";
    const r = await fetch(`/api/evidence/${encodeURIComponent(lemma)}`);
    renderEvidence(await r.json());
  };
  evBtn.addEventListener("click", loadEvidence);
  if (evBtn.dataset.auto === "1") loadEvidence();

  const moveBtn = document.getElementById("move-btn");
  if (moveBtn) {
    moveBtn.addEventListener("click", async () => {
      const status = document.getElementById("move-status");
      const dest = document.getElementById("move-dest").value;
      status.textContent = "moving…";
      const { status: code, data } = await postJSON("/api/move", {
        file, line_no: parseInt(line, 10), dest,
      });
      if (code === 200) {
        status.textContent = `✓ moved to ${data.to}:${data.line_no}`;
        setTimeout(() => location.href = `/entry/${data.to}/${data.line_no}`, 700);
      } else if (code === 409) {
        status.textContent = "⚠ file changed on disk — reload";
      } else {
        status.textContent = "✗ " + (data.error || "not moved");
      }
    });
  }

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      saveEntry();
    }
    if (e.key === "Escape") {
      window.history.back();
    }
  });
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

function initValidateAll() {
  const form = document.getElementById("validate-all-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.getElementById("validate-all-status");
    const box = document.getElementById("validate-all-results");
    status.textContent = "validating…";
    const { data } = await postJSON("/api/validate-all", {});
    if (data.error) {
      status.textContent = "✗ " + data.error;
      return;
    }
    status.textContent = `✓ ${data.count} problems`;
    if (!data.count) {
      box.textContent = "All entries pass check-syntax validation.";
      return;
    }
    let html = `<p class="muted">${data.count} entries have issues:</p><table class="entries">`;
    html += "<thead><tr><th>Lemma</th><th>File:Line</th><th>Problems</th></tr></thead><tbody>";
    for (const r of data.results.slice(0, 200)) {
      html += `<tr><td><a href="/entry/${encodeURIComponent(r.file)}/${r.line_no}?evidence=1">${esc(r.lemma)}</a></td>`;
      html += `<td class="muted">${esc(r.file)}:${r.line_no}</td>`;
      html += `<td class="muted">${esc(r.problems.join("; "))}</td></tr>`;
    }
    if (data.results.length > 200) {
      html += `<tr><td colspan="3" class="muted">… ${data.results.length - 200} more.</td></tr>`;
    }
    html += "</tbody></table>";
    box.innerHTML = html;
  });
}

function initCorpusSettings() {
  const corpusInput = document.getElementById("corpus-url");
  const bcqlInput = document.getElementById("bcql-url");
  if (!corpusInput || !bcqlInput) return;
  const status = document.getElementById("corpus-settings-status");
  const load = async () => {
    const r = await fetch("/api/settings");
    const data = await r.json();
    corpusInput.value = data.corpus_url || "";
    bcqlInput.value = data.bcql_url || "";
    status.textContent =
      `bcql: ${data.bcql_url ? "on" : "off"} · count: ${data.corpus_url ? "on" : "off"}`;
  };
  document.getElementById("corpus-save").addEventListener("click", async () => {
    const { status: code, data } = await postJSON("/api/settings", {
      corpus_url: corpusInput.value.trim(),
      bcql_url: bcqlInput.value.trim(),
    });
    status.textContent = code === 200
      ? `✓ bcql: ${data.bcql_url ? "on" : "off"} · count: ${data.corpus_url ? "on" : "off"}`
      : "✗ " + (data.error || "failed");
  });
  load();
}

function initFileBrowser() {
  const buildBtn = document.getElementById("run-build-dict");
  const sepBtn = document.getElementById("run-separate");
  const gitBtn = document.getElementById("git-commit-btn");
  if (!buildBtn && !sepBtn && !gitBtn) return;

  if (buildBtn) {
    buildBtn.addEventListener("click", async () => {
      const status = document.getElementById("build-dict-status");
      const output = document.getElementById("script-output");
      status.textContent = "running…";
      const { data } = await postJSON("/api/run/build-dict", {});
      status.textContent = data.ok ? "✓ done" : `✗ rc=${data.rc}`;
      output.textContent = (data.stdout || "") + (data.stderr || "");
      output.classList.remove("muted");
    });
  }

  if (sepBtn) {
    sepBtn.addEventListener("click", async () => {
      const status = document.getElementById("separate-status");
      const output = document.getElementById("script-output");
      status.textContent = "running…";
      const { data } = await postJSON("/api/run/separate", {});
      status.textContent = data.ok ? "✓ done — reload to see changes" : `✗ rc=${data.rc}`;
      output.textContent = (data.stdout || "") + (data.stderr || "");
      output.classList.remove("muted");
    });
  }

  // Git: load status on page load
  loadGitStatus();

  if (gitBtn) {
    gitBtn.addEventListener("click", async () => {
      const message = document.getElementById("git-message");
      const status = document.getElementById("git-commit-status");
      if (!message.value.trim()) { status.textContent = "enter a message"; return; }
      status.textContent = "committing…";
      const { data } = await postJSON("/api/git/commit", { message: message.value.trim() });
      status.textContent = data.ok ? "✓ committed" : "✗ " + (data.error || "failed");
      if (data.ok) { message.value = ""; loadGitStatus(); }
    });
  }
}

async function loadGitStatus() {
  const el = document.getElementById("git-status");
  const diffEl = document.getElementById("git-diff");
  if (!el) return;
  try {
    const { data } = await (await fetch("/api/git/status")).json();
    if (!data.files.length) {
      el.textContent = "Working tree clean.";
      diffEl.textContent = "";
      return;
    }
    let html = `<b>${data.files.length} changed file${data.files.length > 1 ? "s" : ""}:</b> `;
    html += data.files.map(f => `${esc(f.status)} ${esc(f.path)}`).join(", ");
    el.innerHTML = html;
    // Load diff for first file
    const firstPath = data.files[0].path;
    const d = await (await fetch(`/api/git/diff?path=${encodeURIComponent(firstPath)}`)).json();
    if (d.ok && d.diff.trim()) {
      diffEl.textContent = d.diff;
      diffEl.classList.remove("muted");
    }
  } catch { el.textContent = "git not available"; }
}

document.addEventListener("DOMContentLoaded", () => {
  initEditor();
  initRescan();
  initValidateAll();
  initCorpusSettings();
  initFileBrowser();
});
