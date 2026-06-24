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


PER_PAGE = 80   # Pexels maximum
MAX_PAGES = 6   # per keyword; 6 * 80 = up to 480 candidates per keyword


def _download_one(v: dict, out_dir: Path, index: int) -> Path | None:
    files = sorted(
        [f for f in v["video_files"] if f.get("width") and f.get("height")],
        key=lambda f: f["width"] * f["height"],
    )
    target = next(
        (f for f in files if 720 <= max(f["width"], f["height"]) <= 1920),
        files[-1] if files else None,
    )
    if not target:
        return None
    path = out_dir / f"clip_{index:03d}.mp4"
    try:
        with requests.get(target["link"], stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
    except Exception as e:
        print(f"  Failed download: {e}")
        return None
    return path


def fetch_clips(keywords: list[str], count: int, orientation: str, out_dir: Path) -> list[Path]:
    """Fetch up to `count` unique clips. Pages through Pexels (page 1 of every
    keyword first, then page 2, ...) so longer videos get varied footage rather
    than reusing the same 15 results. orientation: 'portrait' 9:16 / 'landscape' 16:9.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": _key()}
    saved: list[Path] = []
    seen_ids: set[int] = set()

    queries = [k.strip() for k in keywords if k.strip()] or ["nature"]
    random.shuffle(queries)

    for page in range(1, MAX_PAGES + 1):
        if len(saved) >= count:
            break
        for q in queries:
            if len(saved) >= count:
                break
            params = {"query": q, "per_page": PER_PAGE, "page": page, "orientation": orientation}
            r = requests.get(API, headers=headers, params=params, timeout=30)
            if r.status_code != 200:
                print(f"  Pexels search '{q}' p{page} failed: {r.status_code}")
                continue
            videos = r.json().get("videos", [])
            random.shuffle(videos)
            for v in videos:
                if len(saved) >= count:
                    break
                if v["id"] in seen_ids:
                    continue
                path = _download_one(v, out_dir, len(saved))
                if path is None:
                    continue
                saved.append(path)
                seen_ids.add(v["id"])

    if not saved:
        raise RuntimeError(f"Pexels returned no usable clips for keywords {keywords}")
    print(f"  fetched {len(saved)} unique clips (requested {count})")
    return saved
