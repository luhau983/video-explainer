# AI Explainer Video — pipeline ảnh/video đồng nhất

## Yêu cầu
- Codex CLI đã đăng nhập bằng tài khoản ChatGPT (Plus trở lên) — để dùng `$imagegen`
- Python 3.10+: `pip install pillow requests python-dotenv edge-tts` + ffmpeg
- API key dịch vụ video (Seedance/Kling...) cho bước 6

## Cấu trúc
```
style.md              style block cố định cho mọi prompt
characters/<tên>/     desc.txt + 4-6 ảnh sheet (front, side, 34, biểu cảm)
scenes.csv            id, characters (phân cách ;), scene, camera, motion
prompts/make_sheet.md prompt tạo character sheet
prompts/write_script.md prompt viết kịch bản + scenes.csv
GUIDE-script.md       cấu trúc, quy tắc, checklist kịch bản
GUIDE-audio-motion.md giọng đọc + prompt chuyển động
pronunciation.csv     từ điển phát âm cho TTS
script.md             kịch bản mẫu (5 câu) đúng định dạng
scripts/              gen_sheets.sh, gen_images.sh, contact_sheet.py,
                      make_audio.py, build_motion_prompts.py, make_videos.py
out/images, out/videos
```

## Quy trình
0. Kịch bản: đọc `GUIDE-script.md`, rồi nhờ Claude/Codex viết theo `prompts/write_script.md`
   (thay <CHỦ ĐỀ>). Kết quả: `script.md`, `scenes.csv`, `characters_new.txt`.
   Kiểm chứng mọi chỗ [CẦN NGUỒN], lưu vào `sources.md`, đi hết checklist cuối guide.
1. Sửa `style.md`, tạo thư mục + `desc.txt` cho nhân vật mới trong `characters_new.txt`.
2. Tạo character sheet, duyệt bằng mắt, xoá/tạo lại tới khi ưng:
   `./scripts/gen_sheets.sh salmon bear anisakis`
3. Tạo ảnh cảnh + lưới soát lỗi:
   `./scripts/gen_images.sh` → mở `out/images/_contact_sheet.jpg`
   Cảnh lệch thì xoá ảnh và chạy lại riêng: `./scripts/gen_images.sh 003 017`
4. Audio (cần `pip install edge-tts` + ffmpeg): `python3 scripts/make_audio.py`
   → out/audio/<id>.mp3, timing.csv, voiceover.mp3, subtitles.srt
5. Prompt chuyển động: `python3 scripts/build_motion_prompts.py` → out/motion_prompts.csv
6. Tạo video (sau khi điền API trong `make_videos.py` và `.env`):
   `cp .env.example .env && python3 scripts/make_videos.py`
7. Đưa `out/videos/*.mp4` + `voiceover.mp3` + `subtitles.srt` vào pipeline dựng (giọng đọc, phụ đề, layout nền giấy).

## Lưu ý
- Chạy theo lô 10-15 cảnh nếu dùng gói Plus, vì tạo ảnh tốn hạn mức nhanh.
- Không sửa style.md/desc.txt giữa chừng một video, nếu không sẽ mất đồng nhất.
- Prompt motion: 1 ý, chuyển động nhỏ.
