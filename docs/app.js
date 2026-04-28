// ============================================================
// EDIT THESE TWO LINES to match your GitHub repo:
const OWNER = "Meeeee3443";
const REPO  = "content_pipeline";
// ============================================================

const TEMPLATE = "content-request.yml";

// ----- Form (index.html) -----
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

// ----- Shared helpers -----
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
  }[c]));
}
function fileUrl(slug, filename) {
  return `outputs/${slug}/${encodeURIComponent(filename)}`;
}
async function loadManifest() {
  const r = await fetch(`manifest.json?t=${Date.now()}`);
  if (!r.ok) throw new Error("manifest.json not found");
  return r.json();
}

function getClientFilter() {
  const params = new URLSearchParams(location.search);
  return (params.get("client") || "").trim();
}

// ----- Dashboard (dashboard.html) -----
function renderCard(e) {
  const a = e.artifacts || {};
  const thumb = a.images && a.images.hero_1x1
    ? `<img class="thumb" src="${fileUrl(e.slug, a.images.hero_1x1)}" alt="" loading="lazy">`
    : `<div class="thumb thumb-empty">no image</div>`;

  const tags = [];
  if (a.text) tags.push(`text`);
  if (a.images) tags.push(`images`);
  if (a.reel) tags.push(`reel`);
  if (a.long) tags.push(`long video`);

  const errBadge = (e.errors || []).length
    ? `<span class="badge badge-err">${e.errors.length} error</span>` : "";

  return `
    <a class="card" href="view.html?slug=${encodeURIComponent(e.slug)}">
      ${thumb}
      <div class="card-body">
        <div class="card-head">
          <h2>${escapeHtml(e.topic || "(untitled)")}</h2>
          ${errBadge}
        </div>
        <div class="card-meta">
          <span class="client">${escapeHtml(e.client || "—")}</span>
          <span class="dot">·</span>
          <span>${fmtDate(e.created_at)}</span>
        </div>
        <div class="card-tags">
          ${tags.map(t => `<span class="tag">${t}</span>`).join("")}
        </div>
      </div>
    </a>
  `;
}

async function initDashboard() {
  const root = document.getElementById("entries");
  if (!root) return;
  const filter = getClientFilter();

  if (filter) {
    const titleEl = document.getElementById("dash-title");
    if (titleEl) titleEl.innerHTML = `<em>${escapeHtml(filter)}</em>`;
    const subEl = document.getElementById("dash-sub");
    if (subEl) subEl.textContent = `Content for ${filter}, newest first.`;
    const pillEl = document.getElementById("filter-pill");
    if (pillEl) pillEl.innerHTML = `<span class="filter-pill">filtered: ${escapeHtml(filter)} · <a href="dashboard.html">show all</a></span>`;
  }

  try {
    const data = await loadManifest();
    let entries = data.entries || [];
    if (filter) {
      const f = filter.toLowerCase();
      entries = entries.filter(e => (e.client || "").toLowerCase() === f);
    }
    if (!entries.length) {
      const msg = filter
        ? `No content yet for ${escapeHtml(filter)}.`
        : "No content yet. Submit a request to get started.";
      root.innerHTML = `<p class="empty">${msg}</p>`;
      return;
    }
    root.innerHTML = `<div class="grid">${entries.map(renderCard).join("")}</div>`;
  } catch (err) {
    root.innerHTML = `<p class="empty">Could not load: ${escapeHtml(err.message)}</p>`;
  }
}

// ----- Detail (view.html) -----
function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = "Copied";
    setTimeout(() => { btn.textContent = orig; }, 1200);
  });
}
async function loadText(slug, file) {
  try {
    const r = await fetch(fileUrl(slug, file));
    return r.ok ? await r.text() : "";
  } catch { return ""; }
}
function section(title, body) {
  return `<section class="vsec"><h2>${escapeHtml(title)}</h2>${body}</section>`;
}
function videoBlock(slug, file, label) {
  const url = fileUrl(slug, file);
  return `
    <div class="vplayer">
      <video controls preload="metadata" src="${url}"></video>
      <div class="vplayer-foot">
        <span>${escapeHtml(label)}</span>
        <a class="btn" href="${url}" download>Download</a>
      </div>
    </div>
  `;
}
function imageBlock(slug, files) {
  return `<div class="vimages">${
    Object.entries(files).map(([key, f]) => `
      <figure>
        <img src="${fileUrl(slug, f)}" alt="${escapeHtml(key)}" loading="lazy">
        <figcaption>
          <span>${escapeHtml(key)}</span>
          <a class="btn btn-sm" href="${fileUrl(slug, f)}" download>Download</a>
        </figcaption>
      </figure>
    `).join("")
  }</div>`;
}
function textBlock(slug, label, file, content) {
  const safe = escapeHtml(content || "(empty)");
  const id = `txt-${file}`;
  return `
    <div class="vtext">
      <div class="vtext-head">
        <span>${escapeHtml(label)}</span>
        <span class="vtext-actions">
          <button class="btn btn-sm" data-copy="${id}">Copy</button>
          <a class="btn btn-sm" href="${fileUrl(slug, file)}" download>Download</a>
        </span>
      </div>
      <pre id="${id}">${safe}</pre>
    </div>
  `;
}

async function initView() {
  const root = document.getElementById("view");
  if (!root) return;
  const params = new URLSearchParams(location.search);
  const slug = params.get("slug");
  if (!slug) {
    root.innerHTML = `<p class="empty">Missing slug.</p>`;
    return;
  }
  let data;
  try { data = await loadManifest(); }
  catch (err) {
    root.innerHTML = `<p class="empty">Could not load: ${escapeHtml(err.message)}</p>`;
    return;
  }
  const e = (data.entries || []).find(x => x.slug === slug);
  if (!e) {
    root.innerHTML = `<p class="empty">Entry not found.</p>`;
    return;
  }

  const topicEl = document.getElementById("v-topic");
  if (topicEl) topicEl.textContent = e.topic || "(untitled)";
  const metaEl = document.getElementById("v-meta");
  if (metaEl) metaEl.innerHTML = `
    ${escapeHtml(e.client || "—")} · ${fmtDate(e.created_at)}
    · keywords: ${(e.keywords || []).map(escapeHtml).join(", ")}
    ${e.issue_number ? ` · <a href="https://github.com/${OWNER}/${REPO}/issues/${e.issue_number}" target="_blank">issue #${e.issue_number}</a>` : ""}
  `;

  const a = e.artifacts || {};
  const parts = [];

  if (a.reel && a.reel.reel_9x16) {
    parts.push(section("Reel · 9:16", videoBlock(e.slug, a.reel.reel_9x16, "reel_9x16.mp4")));
  }
  if (a.long && a.long.long_16x9) {
    parts.push(section("Long video · 16:9", videoBlock(e.slug, a.long.long_16x9, "long_16x9.mp4")));
  }
  if (a.images && Object.keys(a.images).length) {
    parts.push(section("Hero images", imageBlock(e.slug, a.images)));
  }
  if (a.text && Object.keys(a.text).length) {
    const labels = {
      short_copy: "Short copy",
      reel_script: "Reel script",
      long_script: "Long script",
      image_prompt: "Image prompt",
    };
    const blocks = await Promise.all(
      Object.entries(a.text).map(async ([key, f]) => {
        const content = await loadText(e.slug, f);
        return textBlock(e.slug, labels[key] || key, f, content);
      })
    );
    parts.push(section("Text", blocks.join("")));
  }
  if ((e.errors || []).length) {
    parts.push(section("Errors", `<pre class="errblock">${escapeHtml(e.errors.join("\n"))}</pre>`));
  }
  if (!parts.length) {
    parts.push(`<p class="empty">No artifacts in this entry.</p>`);
  }

  root.innerHTML = parts.join("");

  root.querySelectorAll("[data-copy]").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.getAttribute("data-copy"));
      if (target) copyToClipboard(target.textContent, btn);
    });
  });
}

// ----- Boot -----
document.addEventListener("DOMContentLoaded", () => {
  initForm();
  initDashboard();
  initView();
});
