import json
from pathlib import Path
import ollama

MODEL = "llama3.2:3b"

SCHEMA = {
    "type": "object",
    "required": ["short_copy", "reel_script", "long_script", "image_prompt"],
    "properties": {
        "short_copy": {"type": "string"},
        "reel_script": {"type": "string"},
        "long_script": {"type": "string"},
        "image_prompt": {"type": "string"},
    },
}

PROMPT = """You are a social media content writer and video scriptwriter.

Topic: {topic}
Keywords: {keywords}
Notes: {notes}

Return a JSON object with exactly these four string fields:

- short_copy: 150-200 words. Hook in the first line. Platform-neutral. No hashtags.

- reel_script: ~140 words (about 60 seconds spoken). Conversational tone.
  Plain prose only — no stage directions, no [CUT] markers, no chapter labels.
  This text will be read aloud verbatim by a TTS voice.

- long_script: ~450 words (about 3 minutes spoken).
  Story arc: hook, problem, deep dive, examples, call to action.
  Plain prose only — no stage directions, no chapter labels.
  This text will be read aloud verbatim by a TTS voice.

- image_prompt: ONE image generation prompt, max 60 words.
  Style: cinematic, photorealistic. Include subject, mood, lighting,
  color palette, and composition.

All four fields are required. Return JSON only — no commentary outside the JSON.
"""


def run(topic: str, keywords: list[str], notes: str, out_dir: Path) -> dict:
    print(f"[stage1] generating text via Ollama ({MODEL})")
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = PROMPT.format(
        topic=topic,
        keywords=", ".join(keywords),
        notes=notes or "(none)",
    )
    resp = ollama.generate(
        model=MODEL,
        prompt=prompt,
        format=SCHEMA,
        options={"temperature": 0.7},
    )
    raw = resp.get("response", "")
    (out_dir / "raw_response.txt").write_text(raw, encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama returned non-JSON: {e}. See raw_response.txt")

    missing = [k for k in ("short_copy", "reel_script", "long_script", "image_prompt")
               if not data.get(k, "").strip()]
    if missing:
        raise RuntimeError(f"Ollama JSON missing/empty fields: {missing}")

    files = {}
    for key, body in data.items():
        if not isinstance(body, str):
            continue
        fname = f"{key}.txt"
        (out_dir / fname).write_text(body.strip(), encoding="utf-8")
        files[key] = fname

    print("  wrote: " + ", ".join(files.values()))
    return {
        "short_copy": data["short_copy"].strip(),
        "reel_script": data["reel_script"].strip(),
        "long_script": data["long_script"].strip(),
        "image_prompt": data["image_prompt"].strip(),
        "files": files,
    }
