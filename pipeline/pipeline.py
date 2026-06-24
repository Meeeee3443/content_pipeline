"""Orchestrator: parses the issue payload (or CLI args), runs selected stages."""

import argparse
import json
import os
import re
import sys
import traceback
from pathlib import Path

from .stages import stage1_text, stage2_image, stage3_reel, stage4_long
from .utils import manifest, progress
from .utils.slug import make_slug


VOICE_MAP = {
    "en-US-ChristopherNeural (male, warm)": "en-US-ChristopherNeural",
    "en-US-JennyNeural (female, friendly)": "en-US-JennyNeural",
    "en-US-GuyNeural (male, news)": "en-US-GuyNeural",
    "en-GB-RyanNeural (male, British)": "en-GB-RyanNeural",
    "en-IN-PrabhatNeural (male, Indian)": "en-IN-PrabhatNeural",
    "en-IN-NeerjaNeural (female, Indian)": "en-IN-NeerjaNeural",
}


def _normalize_voice(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "en-US-ChristopherNeural"
    return VOICE_MAP.get(raw, raw if raw.startswith("en-") else "en-US-ChristopherNeural")


def _chapters_for_length(raw: str) -> int:
    """Map a length selection to a long-video chapter count (~1 chapter/min).
    Accepts the issue-form label (e.g. 'Long (~10 min)') or a bare number of
    minutes; clamps to a sane 3..16 range. Defaults to 6 when unset."""
    m = re.search(r"\d+", str(raw or ""))
    minutes = int(m.group()) if m else 6
    return max(3, min(minutes, 16))


def _outputs_from_checkboxes(checked: list[str]) -> dict:
    """Map issue-form checkbox labels to a flag dict."""
    s = " | ".join(checked or []).lower()
    return {
        "short_copy": "short copy" in s,
        "reel_script": "reel script" in s,
        "long_script": "long script" in s,
        "images": "hero images" in s,
        "reel_video": "reel video" in s,
        "long_video": "long video" in s,
    }


def _parse_payload(payload: dict) -> dict:
    """The issue-parser action returns {field_id: value} or
    {field_id: {text, list, ...}} depending on field type."""

    def get(k):
        v = payload.get(k)
        if isinstance(v, dict):
            return v.get("text") or v.get("list") or ""
        return v or ""

    raw_outputs = payload.get("outputs")
    if isinstance(raw_outputs, dict):
        checked = raw_outputs.get("selected") or raw_outputs.get("list") or []
    elif isinstance(raw_outputs, list):
        checked = raw_outputs
    else:
        checked = [s.strip() for s in str(raw_outputs or "").split(",") if s.strip()]

    return {
        "client": str(get("client")).strip(),
        "topic": str(get("topic")).strip(),
        "keywords": [k.strip() for k in str(get("keywords")).split(",") if k.strip()],
        "source_url": str(get("source_url")).strip(),
        "voice": _normalize_voice(str(get("voice")).strip()),
        "notes": str(get("notes")).strip(),
        "n_chapters": _chapters_for_length(get("length")),
        "outputs": _outputs_from_checkboxes(checked),
    }


def _from_cli(args) -> dict:
    flags = [f.strip() for f in (args.outputs or "").split(",") if f.strip()]
    return {
        "client": args.client or "local",
        "topic": args.topic,
        "keywords": [k.strip() for k in (args.keywords or "").split(",") if k.strip()],
        "source_url": args.source_url or "",
        "voice": _normalize_voice(args.voice),
        "notes": args.notes or "",
        "n_chapters": _chapters_for_length(args.minutes),
        "outputs": {
            "short_copy": "short_copy" in flags or "all" in flags,
            "reel_script": "reel_script" in flags or "all" in flags,
            "long_script": "long_script" in flags or "all" in flags,
            "images": "images" in flags or "all" in flags,
            "reel_video": "reel" in flags or "reel_video" in flags or "all" in flags,
            "long_video": "long" in flags or "long_video" in flags or "all" in flags,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-env", help="env var name containing JSON issue payload")
    ap.add_argument("--issue-number", default="")
    ap.add_argument("--topic")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--client", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--voice", default="en-US-ChristopherNeural")
    ap.add_argument("--notes", default="")
    ap.add_argument("--minutes", default="6", help="approx long-video length in minutes (3..16)")
    ap.add_argument("--outputs", default="all", help="comma list: short_copy,reel_script,long_script,images,reel,long,all")
    args = ap.parse_args()

    if args.payload_env:
        raw = os.environ.get(args.payload_env, "")
        if not raw:
            print(f"ERROR: env var {args.payload_env} is empty", file=sys.stderr)
            sys.exit(2)
        payload = json.loads(raw)
        cfg = _parse_payload(payload)
    else:
        if not args.topic:
            ap.error("--topic is required when --payload-env is not used")
        cfg = _from_cli(args)

    if not cfg["topic"]:
        print("ERROR: no topic in payload", file=sys.stderr)
        sys.exit(2)
    if not cfg["keywords"]:
        cfg["keywords"] = [cfg["topic"]]

    slug = make_slug(cfg["topic"])
    out_dir = Path("docs/outputs") / slug
    work_dir = Path("tmp") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"Topic:      {cfg['topic']}")
    print(f"Client:     {cfg['client']}")
    print(f"Keywords:   {cfg['keywords']}")
    print(f"Source URL: {cfg.get('source_url') or '(none)'}")
    print(f"Voice:      {cfg['voice']}")
    print(f"Long video: ~{cfg['n_chapters']} chapters")
    print(f"Outputs:    {[k for k,v in cfg['outputs'].items() if v]}")
    print(f"Slug:       {slug}")
    print("=" * 60)

    artifacts: dict = {}
    errors: list[str] = []

    needs_text = any(
        cfg["outputs"][k] for k in ("short_copy", "reel_script", "long_script", "reel_video", "long_video", "images")
    )

    # Live progress checklist — edits the issue comment in CI, no-op locally.
    steps = []
    if needs_text:
        steps.append(("text", "Script"))
    if cfg["outputs"]["images"]:
        steps.append(("images", "Hero images"))
    if cfg["outputs"]["reel_video"]:
        steps.append(("reel", "Reel video"))
    if cfg["outputs"]["long_video"]:
        steps.append(("long", "Long video"))
    prog = progress.Progress(steps)
    prog.begin()

    text = None
    if needs_text:
        prog.set("text", "running")
        try:
            text = stage1_text.run(
                cfg["topic"], cfg["keywords"], cfg["notes"],
                cfg.get("source_url", ""),
                out_dir,
                cfg.get("n_chapters", 8),
            )
            artifacts["text"] = text["files"]
            prog.set("text", "done")
        except Exception as e:
            errors.append(f"stage1: {e}")
            traceback.print_exc()
            prog.set("text", "failed")

    if cfg["outputs"]["images"]:
        if text:
            prog.set("images", "running")
            try:
                artifacts["images"] = stage2_image.run(text["image_prompt"], out_dir)
                prog.set("images", "done")
            except Exception as e:
                errors.append(f"stage2: {e}")
                traceback.print_exc()
                prog.set("images", "failed")
        else:
            prog.set("images", "skipped")

    if cfg["outputs"]["reel_video"]:
        if text:
            prog.set("reel", "running")
            try:
                artifacts["reel"] = stage3_reel.run(
                    text["reel_script"], cfg["keywords"], cfg["voice"],
                    out_dir, work_dir / "reel",
                )
                prog.set("reel", "done")
            except Exception as e:
                errors.append(f"stage3: {e}")
                traceback.print_exc()
                prog.set("reel", "failed")
        else:
            prog.set("reel", "skipped")

    if cfg["outputs"]["long_video"]:
        if text:
            prog.set("long", "running")
            try:
                artifacts["long"] = stage4_long.run(
                    text["long_script"], cfg["keywords"], cfg["voice"],
                    out_dir, work_dir / "long",
                )
                prog.set("long", "done")
            except Exception as e:
                errors.append(f"stage4: {e}")
                traceback.print_exc()
                prog.set("long", "failed")
        else:
            prog.set("long", "skipped")

    prog.done(bool(errors))

    summary = {
        "slug": slug,
        "issue_number": args.issue_number or None,
        "client": cfg["client"],
        "topic": cfg["topic"],
        "keywords": cfg["keywords"],
        "source_url": cfg.get("source_url", ""),
        "voice": cfg["voice"],
        "notes": cfg["notes"],
        "n_chapters": cfg.get("n_chapters"),
        "requested": cfg["outputs"],
        "artifacts": artifacts,
        "errors": errors,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest.add_entry(summary)

    print("\nDone.")
    if errors:
        print(f"With {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
