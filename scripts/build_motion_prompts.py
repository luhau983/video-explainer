"""
Sinh prompt chuyển động động cho từng cảnh từ scenes.csv (+ timing.csv nếu đã có audio).
Prompt = [camera move] + [hành động chính] + [chuyển động nền theo bối cảnh] + [khoá style]
Đầu ra: out/motion_prompts.csv  (id,duration,prompt,negative) — make_videos.py đọc file này.
Sửa tay cột prompt trong file đầu ra nếu muốn; chạy lại sẽ GIỮ dòng có override=1.
"""
import csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out/motion_prompts.csv"

CAMERA = {  # loại cảnh -> các kiểu máy xoay vòng để tránh lặp
    "close": ["slow push-in", "subtle handheld drift", "slow pull-back"],
    "medium": ["gentle dolly-in", "slow orbit left", "slight tilt up", "slow orbit right"],
    "wide": ["slow pan right", "slow crane down", "slow pan left", "slow aerial drift forward"],
}
AMBIENT = [  # từ khoá bối cảnh -> chuyển động nền
    (r"ocean|\bsea\b|underwater|aquarium|swimming|river(?! bank)", "bubbles rising, light rays shimmering through water"),
    (r"kitchen|restaurant|bar|food|soup|cook", "steam gently rising, warm light flicker"),
    (r"factory|warehouse|freezer|frozen|ice|cold", "cold mist drifting, frost particles floating"),
    (r"night|lamp|lantern|neon|city", "lights softly flickering, faint particles in the air"),
    (r"forest|field|grass|tree|outdoor", "leaves swaying in light breeze"),
    (r"stomach|gut|intestine|cell|body|blood", "soft organic pulsing of the surroundings"),
    (r"office|meeting|government|tokyo|city hall", "papers fluttering slightly, background people moving"),
]
CAM_WORDS = re.compile(r"\bcamera\b|push-in|pull-back|\bpan\b|\btilt\b|\bzoom\b|dolly|orbit|crane|tracking", re.I)
STYLE_LOCK = "keep low-poly 3D style and character design exactly as the input image, smooth natural motion"
NEGATIVE = "morphing, face distortion, extra limbs, flicker, text, subtitles, watermark, style change, fast camera"


def cam_type(camera):
    c = camera.lower()
    return "close" if "close" in c else "wide" if "wide" in c else "medium"


def ambient(scene):
    return next((a for pat, a in AMBIENT if re.search(pat, scene, re.I)), "subtle environmental motion")


def main():
    scenes = list(csv.DictReader(open(ROOT / "scenes.csv", encoding="utf-8")))
    timing = {}
    tp = ROOT / "out/audio/timing.csv"
    if tp.exists():
        timing = {r["id"]: float(r["duration"]) for r in csv.DictReader(open(tp, encoding="utf-8"))}
    keep = {}
    if OUT.exists():
        keep = {r["id"]: r for r in csv.DictReader(open(OUT, encoding="utf-8")) if r.get("override") == "1"}

    counters, last, rows = {}, None, []
    for s in scenes:
        sid = s["id"]
        if sid in keep:
            rows.append(keep[sid]); continue
        t = cam_type(s.get("camera", ""))
        opts = CAMERA[t]
        i = counters.get(t, 0)
        move = opts[i % len(opts)]
        if move == last:                       # tránh 2 cảnh liền nhau cùng kiểu máy
            i += 1; move = opts[i % len(opts)]
        counters[t], last = i + 1, move
        # tách cột motion: đoạn nào nói về camera thì ưu tiên dùng thay cho camera tự chọn
        segs = [x.strip() for x in (s.get("motion") or "").split(";") if x.strip()]
        cam_segs = [x for x in segs if CAM_WORDS.search(x)]
        act_segs = [x for x in segs if not CAM_WORDS.search(x)]
        if cam_segs:
            move = cam_segs[0]
        action = "; ".join(act_segs) or "character makes a small natural gesture"
        amb = ambient(s.get("scene", ""))
        if amb.split()[0] in action.lower():       # tránh lặp (vd: bubbles 2 lần)
            amb = ""
        speech = timing.get(sid, 4.5)
        dur = 5 if speech <= 5.2 else 10
        prompt = "; ".join(x for x in [move, action, amb, STYLE_LOCK] if x)
        rows.append({"id": sid, "duration": dur, "speech": f"{speech:.2f}",
                     "prompt": prompt, "negative": NEGATIVE, "override": "0"})

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "duration", "speech", "prompt", "negative", "override"])
        w.writeheader(); w.writerows(rows)
    n10 = sum(1 for r in rows if int(r["duration"]) == 10)
    print(f"Đã ghi {OUT} — {len(rows)} cảnh, {n10} cảnh cần clip 10s")


if __name__ == "__main__":
    main()
