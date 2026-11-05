"""Ghép toàn bộ out/images/*.png thành 1 lưới để soát đồng nhất. Cần: pip install pillow"""
from pathlib import Path
from PIL import Image, ImageDraw

src = Path(__file__).resolve().parent.parent / "out/images"
files = sorted(src.glob("[0-9]*.png"))
if not files:
    raise SystemExit("Chưa có ảnh trong out/images/")
W, H, COLS = 480, 270, 5
rows = (len(files) + COLS - 1) // COLS
sheet = Image.new("RGB", (W * COLS, H * rows), "white")
for i, f in enumerate(files):
    im = Image.open(f).convert("RGB")
    im.thumbnail((W, H))
    x, y = (i % COLS) * W, (i // COLS) * H
    sheet.paste(im, (x, y))
    ImageDraw.Draw(sheet).text((x + 8, y + 8), f.stem, fill="red")
out = src / "_contact_sheet.jpg"
sheet.save(out, quality=85)
print(f"Đã tạo {out} ({len(files)} ảnh)")
