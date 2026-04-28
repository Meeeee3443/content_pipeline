from pathlib import Path
from urllib.parse import quote
import requests

POLL_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&nologo=true"


def _download(prompt: str, width: int, height: int, dst: Path) -> None:
    url = POLL_URL.format(prompt=quote(prompt), w=width, h=height)
    print(f"  GET {url[:100]}...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    dst.write_bytes(r.content)
    print(f"  wrote: {dst.name} ({len(r.content)//1024} KB)")


def run(image_prompt: str, out_dir: Path) -> dict:
    print("[stage2] generating images via Pollinations")
    out_dir.mkdir(parents=True, exist_ok=True)
    hero_16x9 = out_dir / "hero_16x9.png"
    hero_1x1 = out_dir / "hero_1x1.png"
    _download(image_prompt, 1920, 1080, hero_16x9)
    _download(image_prompt, 1080, 1080, hero_1x1)
    return {"hero_16x9": hero_16x9.name, "hero_1x1": hero_1x1.name}
