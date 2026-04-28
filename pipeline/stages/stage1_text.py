import json
from pathlib import Path
import ollama

MODEL = "llama3.2:3b"

SCHEMA = {
    "type": "object",
    "required": ["short_copy", "reel_script", "long_chapters", "image_prompt"],
    "properties": {
        "short_copy": {"type": "string"},
        "reel_script": {"type": "string"},
        "long_chapters": {
            "type": "array",
            "minItems": 6,
            "maxItems": 10,
            "items": {"type": "string"},
        },
        "image_prompt": {"type": "string"},
    },
}

PROMPT = """You are a social media content writer and video scriptwriter.

Topic: {topic}
Keywords: {keywords}
Notes: {notes}

Return a JSON object with these exact fields.

short_copy:
  150-200 words. Hook in the first line. Platform-neutral. No hashtags.

reel_script:
  ~140 words (about 60 seconds spoken). Conversational tone.
  Plain prose only. No stage directions. Read aloud by a TTS voice.

long_chapters:
  An array of EXACTLY 8 chapters. Together they must form a 6-8 minute
  spoken script. Each chapter must be 120-180 words of plain narration.
  Each chapter is a complete paragraph with multiple sentences.
  The 8 chapters together tell a coherent story arc:
    1. Hook - grab attention, name the topic, hint at why it matters
    2. The big idea - what this thing actually is, in plain language
    3. Background - history, context, how we got here
    4. The mechanism - how it works, the underlying details
    5. Real example #1 - a concrete case that illustrates the point
    6. Real example #2 - a different angle or surprising application
    7. Implications - what this means going forward, who it affects
    8. Takeaway - the one thing to remember, plus a call to action
  No chapter titles, no numbers, no markdown, no [stage directions].
  Each chapter is plain prose that flows naturally when read aloud.

image_prompt:
  ONE image generation prompt, max 60 words. Style: cinematic, photorealistic.
  Subject, mood, lighting, color palette, composition.

All fields are required. Return JSON only.
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
        options={"temperature": 0.7, "num_predict": 4096},
    )
    raw = resp.get("response", "")
    (out_dir / "raw_response.txt").write_text(raw, encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama returned non-JSON: {e}. See raw_response.txt")

    chapters = [c.strip() for c in data.get("long_chapters", []) if c and c.strip()]
    if len(chapters) < 4:
        raise RuntimeError(f"Ollama returned only {len(chapters)} chapters; need at least 4")

    long_script = "\n\n".join(chapters)

    for k in ("short_copy", "reel_script", "image_prompt"):
        if not data.get(k, "").strip():
            raise RuntimeError(f"Ollama JSON missing/empty field: {k}")

    files = {
        "short_copy": "short_copy.txt",
        "reel_script": "reel_script.txt",
        "long_script": "long_script.txt",
        "image_prompt": "image_prompt.txt",
    }
    (out_dir / "short_copy.txt").write_text(data["short_copy"].strip(), encoding="utf-8")
    (out_dir / "reel_script.txt").write_text(data["reel_script"].strip(), encoding="utf-8")
    (out_dir / "long_script.txt").write_text(long_script, encoding="utf-8")
    (out_dir / "image_prompt.txt").write_text(data["image_prompt"].strip(), encoding="utf-8")

    word_counts = {
        "short": len(data["short_copy"].split()),
        "reel": len(data["reel_script"].split()),
        "long_total": len(long_script.split()),
        "long_chapters": len(chapters),
        "long_avg": len(long_script.split()) // max(len(chapters), 1),
    }
    print(f"  word counts: {word_counts}")
    print(f"  wrote: short_copy.txt, reel_script.txt, long_script.txt ({len(chapters)} chapters), image_prompt.txt")

    return {
        "short_copy": data["short_copy"].strip(),
        "reel_script": data["reel_script"].strip(),
        "long_script": long_script,
        "image_prompt": data["image_prompt"].strip(),
        "files": files,
    }
