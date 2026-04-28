from pathlib import Path
import re
import ollama

MODEL = "llama3.2:3b"

PROMPT = """You are a social media content writer and video scriptwriter.

Topic: {topic}
Keywords: {keywords}
Notes: {notes}

Generate ALL of the following in one response. Use the exact section markers shown.

---SHORT_COPY---
150-200 words. Hook in the first line.
Platform-neutral. No hashtags.

---REEL_SCRIPT---
60 seconds spoken (~140 words).
Conversational tone. Plain prose only — no stage directions, no [CUT] markers.
This text will be read aloud verbatim by a TTS voice.

---LONG_SCRIPT---
About 3 minutes spoken (~450 words).
Story arc: Hook -> Problem -> Deep Dive -> Examples -> CTA.
Plain prose only — no stage directions, no chapter labels.
This text will be read aloud verbatim by a TTS voice.

---IMAGE_PROMPT---
One image generation prompt, max 60 words.
Style: cinematic, photorealistic.
Include: subject, mood, lighting, color palette, composition.
"""


def _split_sections(text: str) -> dict:
    parts = re.split(r"---([A-Z_]+)---", text)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        key = parts[i].strip()
        body = parts[i + 1].strip()
        out[key] = body
    return out


def run(topic: str, keywords: list[str], notes: str, out_dir: Path) -> dict:
    print(f"[stage1] generating text via Ollama ({MODEL})")
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = PROMPT.format(
        topic=topic,
        keywords=", ".join(keywords),
        notes=notes or "(none)",
    )
    resp = ollama.generate(model=MODEL, prompt=prompt, options={"temperature": 0.8})
    text = resp.get("response", "")
    sections = _split_sections(text)

    required = ["SHORT_COPY", "REEL_SCRIPT", "LONG_SCRIPT", "IMAGE_PROMPT"]
    missing = [k for k in required if k not in sections or not sections[k]]
    if missing:
        (out_dir / "raw_response.txt").write_text(text, encoding="utf-8")
        raise RuntimeError(f"Ollama output missing sections: {missing}")

    files = {}
    for key, body in sections.items():
        fname = key.lower() + ".txt"
        (out_dir / fname).write_text(body, encoding="utf-8")
        files[key.lower()] = fname

    print("  wrote: " + ", ".join(files.values()))
    return {
        "short_copy": sections["SHORT_COPY"],
        "reel_script": sections["REEL_SCRIPT"],
        "long_script": sections["LONG_SCRIPT"],
        "image_prompt": sections["IMAGE_PROMPT"],
        "files": files,
    }
