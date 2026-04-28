"""Stage 3: 9:16 reel built from Edge TTS narration + Pexels clips + FFmpeg."""

from pathlib import Path
import asyncio
import edge_tts

from ..utils import pexels, ffmpeg_helpers as ff

WIDTH, HEIGHT = 1080, 1920


async def _tts(text: str, voice: str, audio_dst: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice)
    with open(audio_dst, "wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])


def run(reel_script: str, keywords: list[str], voice: str, out_dir: Path, work_dir: Path) -> dict:
    print("[stage3] building 9:16 reel")
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    audio = work_dir / "voice.mp3"
    asyncio.run(_tts(reel_script, voice, audio))
    audio_dur = ff.probe_duration(audio)
    print(f"  TTS duration: {audio_dur:.1f}s")

    srt = work_dir / "subs.srt"
    srt_text = ff.make_srt(reel_script, audio_dur, words_per_cue=5)
    srt.write_text(srt_text, encoding="utf-8")
    print(f"  SRT: {len(srt_text)} chars, {srt_text.count(chr(10))} lines")

    clip_seconds = 4.0
    n_clips = max(3, int(audio_dur / clip_seconds) + 1)
    print(f"  fetching {n_clips} portrait clips from Pexels")
    raw_clips = pexels.fetch_clips(keywords, n_clips, "portrait", work_dir / "raw")

    norm_dir = work_dir / "norm"
    norm_dir.mkdir(exist_ok=True)
    norm_clips = []
    for i, src in enumerate(raw_clips):
        dst = norm_dir / f"n_{i:02d}.mp4"
        ff.normalize_clip(src, dst, WIDTH, HEIGHT, clip_seconds)
        norm_clips.append(dst)

    silent = work_dir / "silent.mp4"
    ff.concat_clips(norm_clips, silent)

    final = out_dir / "reel_9x16.mp4"
    ff.mux_audio_subs(silent, audio, srt, final)
    print(f"  wrote: {final.name}")
    return {"reel_9x16": final.name}
