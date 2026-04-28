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


def mux_audio_subs(video: Path, audio: Path, srt: Path | None, dst: Path) -> None:
    cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio)]
    if srt and srt.exists() and srt.stat().st_size > 0:
        srt_abs = srt.resolve().as_posix().replace(":", "\\:")
        vf = (
            f"subtitles='{srt_abs}':force_style="
            "'FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
            "Alignment=2,MarginV=40'"
        )
        cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "23"]
    else:
        print("  (skipping subtitle burn: SRT missing or empty)")
        cmd += ["-c:v", "copy"]
    cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest", str(dst)]
    run(cmd)


def _fmt_srt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_srt(text: str, total_duration: float, words_per_cue: int = 6) -> str:
    """Distribute the script text evenly across the audio duration as SRT cues."""
    words = text.split()
    if not words or total_duration <= 0:
        return ""
    cues: list[str] = []
    bucket: list[str] = []
    for w in words:
        bucket.append(w)
        if len(bucket) >= words_per_cue:
            cues.append(" ".join(bucket))
            bucket = []
    if bucket:
        cues.append(" ".join(bucket))
    cue_dur = total_duration / len(cues)
    lines: list[str] = []
    for i, c in enumerate(cues):
        start = i * cue_dur
        end = min((i + 1) * cue_dur, total_duration)
        lines += [
            str(i + 1),
            f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}",
            c,
            "",
        ]
    return "\n".join(lines)
