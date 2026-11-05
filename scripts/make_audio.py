"""
Tạo giọng đọc từng câu từ script.md bằng edge-tts (miễn phí).
Đầu ra:
  out/audio/<id>.mp3        giọng từng cảnh
  out/audio/timing.csv      id,text,duration
  out/audio/voiceover.mp3   ghép toàn bộ (có khoảng nghỉ)
  out/audio/subtitles.srt   phụ đề theo câu
Cần: pip install edge-tts ; ffmpeg trong PATH
Dùng: python3 scripts/make_audio.py            (tạo câu chưa có)
      python3 scripts/make_audio.py 003 017    (tạo lại câu chỉ định)
"""
import asyncio, csv, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out/audio"
VOICE = os.getenv("TTS_VOICE", "vi-VN-NamMinhNeural")   # nữ: vi-VN-HoaiMyNeural
RATE = os.getenv("TTS_RATE", "+12%")                     # ~5 âm tiết/giây
PITCH = os.getenv("TTS_PITCH", "+0Hz")
GAP = float(os.getenv("TTS_GAP", "0.25"))                # nghỉ giữa các câu (giây)
LINE = re.compile(r"^\s*(\d{3})[.:)\-]?\s+(.+)$")


def load_lines():
    lines = []
    for raw in (ROOT / "script.md").read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw)
        if m:
            text = re.sub(r"\[.*?\]", "", m.group(2))
            text = re.sub(r"\s+([.,!?:;])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()
            lines.append((m.group(1), text))
    if not lines:
        sys.exit("Không tìm thấy câu dạng '001. nội dung' trong script.md")
    return lines


def load_pron():
    p = ROOT / "pronunciation.csv"
    return [(r["from"], r["to"]) for r in csv.DictReader(open(p, encoding="utf-8"))] if p.exists() else []


def speakable(text, pron):
    for a, b in pron:
        text = re.sub(re.escape(a), b, text, flags=re.IGNORECASE)
    return text


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


def srt_time(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02}:{m:02}:{int(s):02},{int(s % 1 * 1000):03}"


async def tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(str(path))


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    pron = load_pron()
    lines = load_lines()
    for sid, text in lines:
        f = OUT / f"{sid}.mp3"
        if f.exists() and sid not in only:
            continue
        print(f"[{sid}] {text}")
        await tts(speakable(text, pron), f)

    rows, t, srt, concat = [], 0.0, [], []
    silence = OUT / "_gap.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", str(GAP), "-q:a", "9", str(silence)], check=True)
    for i, (sid, text) in enumerate(lines, 1):
        d = duration(OUT / f"{sid}.mp3")
        rows.append({"id": sid, "text": text, "duration": f"{d:.2f}", "start": f"{t:.2f}"})
        srt.append(f"{i}\n{srt_time(t)} --> {srt_time(t + d)}\n{text}\n")
        concat += [f"file '{sid}.mp3'", f"file '_gap.mp3'"]
        t += d + GAP

    with open(OUT / "timing.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "text", "duration", "start"])
        w.writeheader(); w.writerows(rows)
    (OUT / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    (OUT / "_list.txt").write_text("\n".join(concat), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "_list.txt"),
                    "-c:a", "libmp3lame", "-q:a", "2", str(OUT / "voiceover.mp3")], check=True)
    long = [r["id"] for r in rows if float(r["duration"]) > 6]
    print(f"Tổng {t:.1f}s / {len(rows)} câu. TB {t/len(rows):.1f}s/câu.")
    if long:
        print(f"Câu > 6s (nên tách hoặc rút gọn): {', '.join(long)}")


asyncio.run(main())
