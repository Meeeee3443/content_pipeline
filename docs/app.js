// ============================================================
// EDIT THESE TWO LINES to match your GitHub repo:
const OWNER = "Meeeee3443";
const REPO  = "content_pipeline";
// ============================================================

const TEMPLATE = "content-request.yml";

function buildIssueUrl(form) {
  const data = new FormData(form);
  const outputs = data.getAll("outputs").join(", ");
  const params = new URLSearchParams();
  params.set("template", TEMPLATE);
  params.set("title", `[Content] ${data.get("topic") || ""}`);
  params.set("client", data.get("client") || "");
  params.set("topic", data.get("topic") || "");
  params.set("keywords", data.get("keywords") || "");
  params.set("outputs", outputs);
  params.set("voice", data.get("voice") || "");
  params.set("notes", data.get("notes") || "");
  return `https://github.com/${OWNER}/${REPO}/issues/new?${params.toString()}`;
}

function initForm() {
  const form = document.getElementById("request-form");
  const btn = document.getElementById("generate-btn");
  if (!form || !btn) return;
  btn.addEventListener("click", () => {
    if (!form.reportValidity()) return;
    const url = buildIssueUrl(form);
    window.open(url, "_blank");
  });
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString();
}

function fileLink(slug, filename) {
  const url = `../outputs/${slug}/${encodeURIComponent(filename)}`;
  return `<a href="${url}" target="_blank">${filename}</a>`;
}

function renderEntry(e) {
  const a = e.artifacts || {};
  const links = [];
  if (a.text) Object.values(a.text).forEach(f => links.push(fileLink(e.slug, f)));
  if (a.images) Object.values(a.images).forEach(f => links.push(fileLink(e.slug, f)));
  if (a.reel) Object.values(a.reel).forEach(f => links.push(fileLink(e.slug, f)));
  if (a.long) Object.values(a.long).forEach(f => links.push(fileLink(e.slug, f)));

  const errs = (e.errors || []).length
    ? `<div class="errors">${e.errors.length} error(s): ${e.errors.join(" | ")}</div>` : "";

  return `
    <article class="entry">
      <div class="entry-head">
        <h2>${escapeHtml(e.topic || "(untitled)")}</h2>
        <time>${fmtDate(e.created_at)}</time>
      </div>
      <div class="entry-meta">
        ${escapeHtml(e.client || "—")} · keywords: ${(e.keywords || []).map(escapeHtml).join(", ")}
        ${e.issue_number ? ` · <a href="https://github.com/${OWNER}/${REPO}/issues/${e.issue_number}" target="_blank">#${e.issue_number}</a>` : ""}
      </div>
      <div class="entry-files">
        ${links.length ? links.join("") : '<span style="color:var(--muted);font-size:13px;">No files</span>'}
      </div>
      ${errs}
    </article>
  `;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
  }[c]));
}

async function initDashboard() {
  const root = document.getElementById("entries");
  if (!root) return;
  try {
    const r = await fetch(`manifest.json?t=${Date.now()}`);
    if (!r.ok) throw new Error("manifest.json not found");
    const data = await r.json();
    if (!data.entries || !data.entries.length) {
      root.innerHTML = '<p class="empty">No content yet. Submit a request to get started.</p>';
      return;
    }
    root.innerHTML = data.entries.map(renderEntry).join("");
  } catch (err) {
    root.innerHTML = `<p class="empty">Could not load manifest: ${escapeHtml(err.message)}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initForm();
  initDashboard();
});
