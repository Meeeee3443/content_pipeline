import json
from pathlib import Path
import ollama

from ..utils.web_fetch import fetch_article

MODEL = "qwen2.5:7b"

def _schema(n_chapters: int) -> dict:
    return {
        "type": "object",
        "required": ["short_copy", "reel_script", "long_chapters", "image_prompt"],
        "properties": {
            "short_copy": {"type": "string"},
            "reel_script": {"type": "string"},
            "long_chapters": {
                "type": "array",
                "minItems": max(3, n_chapters - 2),
                "maxItems": n_chapters + 2,
                "items": {"type": "string"},
            },
            "image_prompt": {"type": "string"},
        },
    }

PROMPT_HEAD = """You are a social media content writer and video scriptwriter.

Topic: {topic}
Keywords: {keywords}
Client brief / rough prompt: {notes}
{article_block}
Write content based on the brief above. If a source article is provided,
extract the key facts and ideas from it; do not invent details not supported
by the inputs.

Return a JSON object with these exact fields.

short_copy:
  150-200 words. Hook in the first line. Platform-neutral. No hashtags.

reel_script:
  ~140 words (about 60 seconds spoken). Conversational tone.
  Plain prose only. No stage directions. Read aloud by a TTS voice.

{chapters_spec}

image_prompt:
  ONE image generation prompt, max 60 words. Style: cinematic, photorealistic.
  Subject, mood, lighting, color palette, composition.

All fields are required. Return JSON only.
"""


def _chapters_spec(n_chapters: int) -> str:
    """Build the long_chapters instruction for a target chapter count
    (~1 chapter ≈ 1 spoken minute at ~150 words)."""
    return (
        "long_chapters:\n"
        f"  An array of EXACTLY {n_chapters} chapters. Together they form a\n"
        f"  roughly {n_chapters}-minute spoken script. Each chapter must be 130-170\n"
        "  words of plain narration — a complete paragraph with multiple sentences.\n"
        "  The chapters together tell a coherent story arc: open with a hook that\n"
        "  names the topic and why it matters; develop it across the middle chapters\n"
        "  (what it is in plain language, background and context, how it works,\n"
        "  concrete real-world examples, and implications); and close the final\n"
        "  chapter with the one thing to remember plus a call to action.\n"
        "  No chapter titles, no numbers, no markdown, no [stage directions].\n"
        "  Each chapter is plain prose that flows naturally when read aloud."
    )


def _build_prompt(topic: str, keywords: list[str], notes: str, article_text: str, n_chapters: int) -> str:
    if article_text:
        article_block = (
            "\nSource article (use this as your primary factual basis):\n"
            "---\n"
            f"{article_text}\n"
            "---\n"
        )
    else:
        article_block = ""
    return PROMPT_HEAD.format(
        topic=topic,
        keywords=", ".join(keywords) if keywords else "(none)",
        notes=notes or "(none)",
        article_block=article_block,
        chapters_spec=_chapters_spec(n_chapters),
    )


def run(topic: str, keywords: list[str], notes: str, source_url: str, out_dir: Path, n_chapters: int = 8) -> dict:
    print(f"[stage1] generating text via Ollama ({MODEL}), target {n_chapters} chapters")
    out_dir.mkdir(parents=True, exist_ok=True)

    article_text = ""
    if source_url:
        print(f"  fetching source URL: {source_url}")
        article_text, fetch_err = fetch_article(source_url)
        if fetch_err:
            print(f"  WARN: {fetch_err} (continuing without article)")
        else:
            print(f"  article extracted: {len(article_text)} chars, {len(article_text.split())} words")
            (out_dir / "source_article.txt").write_text(article_text, encoding="utf-8")

    prompt = _build_prompt(topic, keywords, notes, article_text, n_chapters)
    (out_dir / "prompt_used.txt").write_text(prompt, encoding="utf-8")

    # Output budget scales with chapter count (~180 words/chapter + the other
    # fields), at ~1.7 tokens/word, with headroom.
    num_predict = max(4096, int((n_chapters * 180 + 500) * 1.7))
    resp = ollama.generate(
        model=MODEL,
        prompt=prompt,
        format=_schema(n_chapters),
        options={"temperature": 0.7, "num_predict": num_predict},
    )
    raw = resp.get("response", "")
    (out_dir / "raw_response.txt").write_text(raw, encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama returned non-JSON: {e}. See raw_response.txt")

    chapters = [c.strip() for c in data.get("long_chapters", []) if c and c.strip()]
    floor = max(3, n_chapters - 3)
    if len(chapters) < floor:
        raise RuntimeError(f"Ollama returned only {len(chapters)} chapters; need at least {floor}")

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
    if article_text:
        files["source_article"] = "source_article.txt"
    files["prompt_used"] = "prompt_used.txt"

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
