import os
import random
from pathlib import Path
import requests

API = "https://api.pexels.com/videos/search"


def _key() -> str:
    k = os.environ.get("PEXELS_API_KEY", "").strip()
    if not k:
        raise RuntimeError("PEXELS_API_KEY env var is not set")
    return k


def fetch_clips(keywords: list[str], count: int, orientation: str, out_dir: Path) -> list[Path]:
    """orientation: 'portrait' for 9:16, 'landscape' for 16:9."""
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": _key()}
    saved: list[Path] = []
    seen_ids: set[int] = set()

    queries = [k.strip() for k in keywords if k.strip()] or ["nature"]
    random.shuffle(queries)

    for q in queries:
        if len(saved) >= count:
            break
        params = {"query": q, "per_page": 15, "orientation": orientation}
        r = requests.get(API, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            print(f"  Pexels search '{q}' failed: {r.status_code}")
            continue
        videos = r.json().get("videos", [])
        random.shuffle(videos)
        for v in videos:
            if v["id"] in seen_ids:
                continue
            files = sorted(
                [f for f in v["video_files"] if f.get("width") and f.get("height")],
                key=lambda f: f["width"] * f["height"],
            )
            target = next(
                (f for f in files if 720 <= max(f["width"], f["height"]) <= 1920),
                files[-1] if files else None,
            )
            if not target:
                continue
            url = target["link"]
            ext = ".mp4"
            path = out_dir / f"clip_{len(saved):02d}{ext}"
            try:
                with requests.get(url, stream=True, timeout=60) as resp:
                    resp.raise_for_status()
                    with open(path, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=8192):
                            fh.write(chunk)
            except Exception as e:
                print(f"  Failed download: {e}")
                continue
            saved.append(path)
            seen_ids.add(v["id"])
            if len(saved) >= count:
                break

    if not saved:
        raise RuntimeError(f"Pexels returned no usable clips for keywords {keywords}")
    return saved
