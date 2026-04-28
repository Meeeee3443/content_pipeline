import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("  $ " + " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd[:4])}...")


def probe_duration(path: Path) -> float:
    res = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True,
    )
    return float(res.stdout.strip() or 0.0)


def normalize_clip(src: Path, dst: Path, width: int, height: int, duration: float) -> None:
    """Crop+scale a clip to exact width x height and trim to duration seconds."""
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-t", f"{duration}",
        "-vf", vf,
        "-r", "30",
        "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        str(dst),
    ])


def concat_clips(clips: list[Path], dst: Path) -> None:
    listfile = dst.parent / "concat.txt"
    listfile.write_text(
        "\n".join(f"file '{c.resolve().as_posix()}'" for c in clips),
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c", "copy", str(dst),
    ])
    listfile.unlink(missing_ok=True)


def mux_audio_subs(video: Path, audio: Path, srt: Path, dst: Path) -> None:
    vf = (
        f"subtitles={srt.as_posix()}:force_style="
        "'FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
        "Alignment=2,MarginV=40'"
    )
    run([
        "ffmpeg", "-y",
        "-i", str(video), "-i", str(audio),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(dst),
    ])
