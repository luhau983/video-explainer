"""
Image-to-video cho toàn bộ out/images/<id>.png, dùng out/motion_prompts.csv
(chạy scripts/build_motion_prompts.py trước).
Bỏ qua cảnh đã có out/videos/<id>.mp4. Chạy lại an toàn.
Cần: pip install requests python-dotenv

Hàm submit_job/poll_job đang để trống phần gọi API: điền endpoint + payload
theo docs chính thức của nhà cung cấp (Seedance / Kling / ...) bạn dùng.
"""
import base64, csv, os, sys, time
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
API_KEY = os.getenv("VIDEO_API_KEY")
API_BASE = os.getenv("VIDEO_API_BASE")
DURATION = int(os.getenv("VIDEO_DURATION", "5"))


def submit_job(image_path: Path, prompt: str, negative: str, duration: int) -> str:
    """Gửi ảnh + prompt, trả về job id. TODO: sửa theo docs nhà cung cấp."""
    img_b64 = base64.b64encode(image_path.read_bytes()).decode()
    raise NotImplementedError(
        "Điền endpoint/payload theo docs nhà cung cấp. Ví dụ dạng chung:\n"
        f"POST {API_BASE}/<image-to-video> với image (base64/url), prompt, duration=5|10, aspect 16:9"
    )


def poll_job(job_id: str) -> str:
    """Chờ job xong, trả về URL video. TODO: sửa theo docs nhà cung cấp."""
    raise NotImplementedError


def main():
    if not API_KEY:
        sys.exit("Thiếu VIDEO_API_KEY trong .env")
    mp = ROOT / "out/motion_prompts.csv"
    if not mp.exists():
        sys.exit("Chưa có out/motion_prompts.csv — chạy scripts/build_motion_prompts.py")
    scenes = {r["id"]: r for r in csv.DictReader(open(mp, encoding="utf-8"))}
    only = set(sys.argv[1:])
    (ROOT / "out/videos").mkdir(parents=True, exist_ok=True)
    for sid, row in scenes.items():
        if only and sid not in only:
            continue
        img = ROOT / f"out/images/{sid}.png"
        out = ROOT / f"out/videos/{sid}.mp4"
        if not img.exists() or (out.exists() and not only):
            continue
        prompt, negative, dur = row["prompt"], row["negative"], int(row["duration"])
        print(f"[{sid}] submit: {prompt}")
        for attempt in range(3):
            try:
                url = poll_job(submit_job(img, prompt, negative, dur))
                out.write_bytes(requests.get(url, timeout=300).content)
                print(f"[{sid}] OK -> {out.name}")
                break
            except NotImplementedError:
                raise
            except Exception as e:
                print(f"[{sid}] lỗi lần {attempt + 1}: {e}")
                time.sleep(10)


if __name__ == "__main__":
    main()
