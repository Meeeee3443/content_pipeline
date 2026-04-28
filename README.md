# Content Pipeline

> Topic in. Finished content out, in about ten minutes.

**Version:** 0.1.0 · **Status:** working build, in active development

An open-source content-generation pipeline that runs entirely on GitHub
infrastructure — no servers, no Docker, no paid APIs. A topic submitted
through a GitHub Pages form triggers a GitHub Action that generates copy,
images, a vertical reel, and a long-form video, then publishes them to a
client-facing dashboard.

Maintained by [Performedia](mailto:dev@performedia.com).

## Live instance

| | URL |
|---|---|
| **Form** (internal — staff submit topics here) | <https://meeeee3443.github.io/content_pipeline/> |
| **Dashboard** (all generated content) | <https://meeeee3443.github.io/content_pipeline/dashboard.html> |
| **Per-client filtered view** | `…/dashboard.html?client=<ClientName>` |
| **Repository** | <https://github.com/Meeeee3443/content_pipeline> |

## What it produces, per request

| Stage | Output | Tool |
|---|---|---|
| 1 | Short copy · reel script · long script · image prompt | Ollama, `llama3.2:3b`, JSON-schema output |
| 2 | Hero images (16:9 and 1:1) | Pollinations.ai (free HTTP, no key) |
| 3 | Vertical reel, ~60s, 9:16, with burned subtitles | Edge TTS + Pexels stock footage + FFmpeg |
| 4 | Long video, ~6–8 min, 16:9, with burned subtitles | Edge TTS + Pexels stock footage + FFmpeg |

The long script is generated as 8 narrative chapters
(120–180 words each) for coherence at length. Each chapter follows a
fixed story arc: hook, big idea, background, mechanism, two examples,
implications, takeaway.

## Architecture

```
   STAFF                                          GITHUB
   ┌──────────────────┐    deep-link              ┌────────────────────────────┐
   │ Pages form       │    pre-fills issue        │ Issue created              │
   │ docs/index.html  ├──────────────────────────▶│  └─ Action: Generate       │
   └──────────────────┘                           │     ├─ Stage 1 Ollama text │
                                                  │     ├─ Stage 2 images      │
   CLIENT                                         │     ├─ Stage 3 reel        │
   ┌──────────────────┐                           │     └─ Stage 4 long video  │
   │ Per-client       │◀────────────────────────  │                            │
   │ filtered         │   manifest.json + media   │  Commits docs/outputs/...  │
   │ dashboard URL    │                           │  Updates manifest.json     │
   └──────────────────┘                           │  Comments link on issue    │
                                                  └────────────────────────────┘
```

The intake form on Pages doesn't have a server. It builds a deep-link
URL to a pre-filled GitHub Issue; submitting the issue is what triggers
the Action. No auth tokens are exposed to the browser.

## One-time setup

This walks through forking and deploying your own instance.

1. **Push this repo to a public GitHub repo** of your own.
   Public is recommended — public repos get unlimited Actions minutes.
2. **Update `docs/app.js`** lines 3–4:
   ```js
   const OWNER = "your-github-username";
   const REPO  = "your-repo-name";
   ```
3. **Pages**: repo Settings → Pages → Source: `Deploy from a branch`,
   branch `main`, folder `/docs`. Save.
4. **Action permissions**: repo Settings → Actions → General →
   "Read and write permissions" + check "Allow GitHub Actions to
   create and approve pull requests". Save.
5. **Pexels API key** (free, 30 seconds):
   - Sign up at <https://www.pexels.com/api/>
   - Repo Settings → Secrets and variables → Actions → New repository
     secret. Name: `PEXELS_API_KEY`, value: your key.

That's it — there's no other infrastructure.

## Usage (recommended agency workflow)

Clients should not need GitHub accounts. The internal flow is:

1. **Intake** — client emails or messages a topic + keywords.
2. **You submit** the form at the Pages URL above. Action runs on its own.
3. **Share the per-client dashboard URL** once the run completes:
   ```
   https://<owner>.github.io/<repo>/dashboard.html?client=<ClientName>
   ```
   That URL shows only that client's content. They can preview the
   reel, watch the long video, copy scripts, and download images
   without ever touching GitHub.

The `?client=` filter is a string-match on the `client` field captured
in the issue form. Use a consistent client name across requests
(case-insensitive match).

## Local development (optional)

The full pipeline runs natively on Linux/macOS/Windows without Docker.

```bash
# Python environment
pip install -r requirements.txt

# System dependencies
# - FFmpeg + ImageMagick (apt / brew / chocolatey)
# - Ollama, then: ollama pull llama3.2:3b

export PEXELS_API_KEY=your_key
python -m pipeline.pipeline \
  --topic "the science of sleep" \
  --keywords "sleep, brain, dream, night, bedroom" \
  --outputs all
```

CLI flags:

- `--outputs` — comma-separated subset of `short_copy, reel_script,
  long_script, images, reel, long`, or `all`
- `--voice` — full Edge TTS voice id, e.g. `en-IN-NeerjaNeural`

Local outputs land in `docs/outputs/<slug>/` (same as the Action runs).

## Tech stack

- **Frontend**: vanilla HTML/CSS/JS. No build step. Deployed by GitHub Pages.
- **Type system**: warm dark palette with serif (Fraunces) headlines and
  sans (Inter) body. WCAG AAA contrast across all text (≥7:1).
- **Pipeline**: Python 3.11, ~600 lines across 4 stages.
- **Models / services**:
  - Ollama `llama3.2:3b` (local on Action runner) — text generation
  - Pollinations.ai — image generation
  - Microsoft Edge TTS public endpoint — voiceover
  - Pexels API — stock video footage
  - FFmpeg + libass — video assembly and subtitle burn-in
- **Orchestration**: GitHub Actions, ~12-step workflow, 25–40 min per
  full run on the free `ubuntu-latest` runner

## Cost

Free, end-to-end. Public-repo Actions minutes are unlimited; Pexels and
Pollinations have no rate caps for this volume; Edge TTS is a free
public Microsoft endpoint; Ollama runs on the Action runner.

## Roadmap

- [ ] Long video target length: today ~6–8 min once Stage 1 reliably
  emits 8 chapters; bigger model upgrade (`qwen2.5:7b` or hosted Groq
  `llama-3.3-70b-versatile`) for higher script quality
- [ ] Move large MP4s out of the repo to GitHub Releases once the repo
  exceeds ~1 GB total
- [ ] Password protection on per-client dashboards (Cloudflare Worker
  or similar gating layer)
- [ ] Per-client logo / brand color via URL params
- [ ] Custom domain (`pipeline.performedia.com`)
- [ ] Strict WCAG AA on non-text UI (1.4.11) — bump card borders to ≥3:1

## Changelog

### 0.1.0 — first working build

- End-to-end pipeline: form → Action → text / images / reel / long video → dashboard
- GitHub Issue forms as the structured intake (deep-linked from Pages form)
- JSON-schema-enforced text generation via Ollama
- Reel and long video assembled with custom SRT generation, with
  graceful fallback when subtitle burn-in fails
- Dashboard with per-client filter, video previews, copy-to-clipboard
  scripts, and download buttons
- Bot commits outputs back to the repo (success or failure) and
  comments on the issue with the result link
- WCAG AAA contrast across all text
- Chapter-based long-script generation (8 chapters × 120–180 words)
  for coherent multi-minute video output

## Maintainer

Performedia · <dev@performedia.com>
