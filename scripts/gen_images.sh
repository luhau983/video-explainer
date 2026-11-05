#!/usr/bin/env bash
# Tạo ảnh cảnh từ scenes.csv bằng Codex $imagegen.
# Dùng: ./scripts/gen_images.sh            (tất cả cảnh chưa có ảnh)
#       ./scripts/gen_images.sh 001 005    (chỉ các id chỉ định — dùng để tạo lại)
set -e
cd "$(dirname "$0")/.."
ONLY="$*"
codex exec -s workspace-write "
Dùng \$imagegen. Đọc style.md và scenes.csv.
Chỉ xử lý các id: ${ONLY:-tất cả id chưa có file trong out/images/}.
Với mỗi dòng:
- prompt = nội dung style.md + desc.txt của từng nhân vật trong cột characters (phân cách ;) + cột scene + cột camera.
- Nếu có nhân vật: đính kèm front.png và 1 ảnh biểu cảm phù hợp trong characters/<tên>/ làm ảnh tham chiếu.
- Lưu out/images/<id>.png (copy từ ~/.codex/generated_images/ nếu cần).
- Xem lại ảnh vừa tạo, so với ảnh sheet. Nếu lệch màu thân, mắt, phụ kiện, hoặc có chữ trong ảnh: tạo lại, tối đa 2 lần.
- Ghi 1 dòng vào out/images/log.csv: id,prompt,so_lan_tao,ghi_chu.
Không sửa file nào khác ngoài out/images/.
"
python3 scripts/contact_sheet.py
