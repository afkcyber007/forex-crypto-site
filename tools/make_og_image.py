"""Optional: regenerates assets/og-image.png (the preview picture shown when your site is shared).
Needs Pillow:  pip install pillow   then   python tools/make_og_image.py"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
W, H = 1200, 630
img = Image.new("RGB", (W, H), "#0b1220")
d = ImageDraw.Draw(img)
for y in range(H):  # subtle vertical gradient
    t = y / H
    d.line([(0, y), (W, y)], fill=(int(11 + 6 * t), int(18 + 8 * t), int(32 + 14 * t)))
d.ellipse([820, -260, 1460, 380], fill="#1c2a4a")
try:
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    f1, f2, f3 = ImageFont.truetype(bold, 64), ImageFont.truetype(reg, 34), ImageFont.truetype(bold, 30)
except OSError:
    f1 = f2 = f3 = ImageFont.load_default()
d.rounded_rectangle([80, 90, 150, 160], 16, fill="#f5b700")
d.text((175, 98), cfg["site_name"], font=f3, fill="#ffcf3f")
d.text((80, 220), "Best Forex Brokers &", font=f1, fill="white")
d.text((80, 300), "Crypto Exchanges by Country", font=f1, fill="white")
d.text((80, 410), "Minimum deposits · Regulation · Leverage · Free signals", font=f2, fill="#c3cde0")
d.rounded_rectangle([80, 490, 520, 550], 12, fill="#f5b700")
d.text((105, 502), "Compare 240+ countries", font=f3, fill="#1a1300")
img.save(root / "assets" / "og-image.png", optimize=True)
print("saved assets/og-image.png")
