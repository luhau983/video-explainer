# Hướng dẫn audio & prompt chuyển động

Thứ tự: script.md → AUDIO → motion prompts (dùng độ dài audio) → video.

## 1. Audio (scripts/make_audio.py)
Định dạng script.md: mỗi câu thoại 1 dòng `001. nội dung`. Dòng khác (tiêu đề, `## Nhịp`) bị bỏ qua; `[...]` tự xoá.

Cấu hình qua biến môi trường:
| Biến | Mặc định | Ghi chú |
|---|---|---|
| TTS_VOICE | vi-VN-NamMinhNeural | nữ: vi-VN-HoaiMyNeural |
| TTS_RATE | +12% | video mẫu ~5 âm tiết/giây; chỉnh tới khi TB 4-5s/câu |
| TTS_GAP | 0.25 | nghỉ giữa câu (giây) |

Viết cho TTS đọc đúng:
- Số và năm viết bằng chữ khi dễ đọc sai: "thập niên 80" → "thập niên tám mươi".
- Viết tắt viết đầy đủ: "km" → "ki-lô-mét".
- Từ nước ngoài: thêm vào pronunciation.csv (from,to), không sửa script.md.
- Dấu phẩy = nghỉ ngắn. Muốn nhấn mạnh thì tách câu.

Đầu ra kiểm tra:
- Script in "TB x.xs/câu" → mục tiêu 4-5s. Câu > 6s được liệt kê → tách hoặc rút gọn.
- Nghe voiceover.mp3 1 lượt, câu đọc sai: sửa pronunciation.csv rồi `python3 scripts/make_audio.py <id>`.
- Muốn giọng tự nhiên hơn: thay hàm tts() bằng ElevenLabs, phần còn lại giữ nguyên.

## 2. Prompt chuyển động (scripts/build_motion_prompts.py)
Prompt tự sinh cho mỗi cảnh theo công thức:
`[camera] ; [hành động] ; [chuyển động nền] ; [khoá style]` + negative prompt cố định.

- Camera: theo cột camera (close/medium/wide), tự xoay vòng để 2 cảnh liền nhau không trùng kiểu máy. Nếu cột motion có ghi camera ("slow pan right") thì dùng của bạn.
- Chuyển động nền: theo từ khoá cột scene (ocean → bọt nước, kitchen → hơi nước, freezer → sương lạnh...). Thêm luật ở mảng AMBIENT.
- Thời lượng: câu thoại ≤ 5.2s → clip 5s, dài hơn → 10s.
- Sửa tay: chỉnh cột prompt trong out/motion_prompts.csv, đặt override=1 để lần chạy sau không ghi đè.

Viết cột motion trong scenes.csv:
- Tối đa 1 hành động nhân vật + (tuỳ chọn) 1 camera, phân cách `;`.
- Tốt: `salmon looks around nervously` / `bear raises the fish; slight tilt up`
- Tránh: xoay người 180°, biến hình, nhiều nhân vật cùng làm việc khác nhau, chữ xuất hiện.
- Cảm xúc dùng động từ rõ: blinks, shrugs, gasps, nods, trembles, grins.

Clip lỗi (méo mặt, đổi style): đơn giản hoá motion → chạy lại riêng `python3 scripts/make_videos.py <id>`.
