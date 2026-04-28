# Content Pipeline

Open-source content generation pipeline that runs entirely on GitHub Actions.
Topic in via a GitHub Pages form, finished content out via a GitHub Pages dashboard.

## What it does

For each topic submitted, the pipeline produces:

| Stage | Output | Tool |
|-------|--------|------|
| 1 | Short copy, reel script, long script, image prompt | Ollama (`llama3.2:3b`) |
| 2 | Hero images (16:9 + 1:1) | Pollinations.ai |
| 3 | 60-second vertical reel | Edge TTS + Pexels + FFmpeg |
| 4 | 3-minute horizontal long video | Edge TTS + Pexels + FFmpeg |

All outputs land in `outputs/<topic-slug>/` and are visible on the Pages dashboard.

## Architecture

```
Client                                  GitHub
┌──────────────────┐    deep-link       ┌─────────────────────────┐
│ Pages form       │  to pre-filled     │ Issue created           │
│ docs/index.html  ├───────────────────▶│  └─ Action triggered    │
└──────────────────┘                    │     ├─ Stage 1 Ollama   │
        ▲                               │     ├─ Stage 2 image    │
        │                               │     ├─ Stage 3 reel     │
        │ download links                │     └─ Stage 4 long     │
        │                               │                         │
┌──────────────────┐                    │  Commits outputs/<slug>/│
│ Pages dashboard  │◀───────────────────┤  Updates manifest.json  │
│ docs/dashboard   │  manifest.json     │  Comments on issue      │
└──────────────────┘                    └─────────────────────────┘
```

## One-time setup

1. **Fork or push this repo to GitHub** (public repo for unlimited Action minutes)
2. **Enable Pages**: Settings → Pages → Source: `main` branch, folder: `/docs`
3. **Add a Pexels API key**:
   - Sign up free at [pexels.com/api](https://www.pexels.com/api/)
   - Settings → Secrets and variables → Actions → New secret
   - Name: `PEXELS_API_KEY`, value: your key
4. **Update `docs/app.js`**: change `OWNER` and `REPO` constants to match your GitHub username + repo name
5. **Enable Actions**: Settings → Actions → General → Allow all actions, allow workflows to write

## Usage

Once setup is done, your Pages site is live at:
`https://<username>.github.io/<repo>/`

Client visits → fills topic + options → clicks Generate → confirms on GitHub →
~5–20 minutes later, content appears on the dashboard at:
`https://<username>.github.io/<repo>/dashboard.html`

## Local testing (optional)

```bash
pip install -r requirements.txt
# Install Ollama from ollama.com, then:
ollama pull llama3.2:3b
# Install FFmpeg, ImageMagick (system packages)

export PEXELS_API_KEY=your_key
python -m pipeline.pipeline --topic "test topic" --keywords "a, b, c" --outputs reel
```

## Cost

Free. Public repo gets unlimited GitHub Actions minutes. Pexels and Pollinations
are free with no caps. Edge TTS uses Microsoft's free public endpoint.
