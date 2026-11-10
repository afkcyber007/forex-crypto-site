"""Creates original high-resolution trading artwork for articles and the home page.
Already run once — images are in assets/img/. Re-run only if you add articles:
    pip install pillow
    python tools/make_images.py
Each image is unique (seeded from the article name)."""
import math
import random
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "img"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 2400, 1260
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

THEMES = {
    "forex":  {"bg": ((6, 14, 36), (10, 34, 82)), "up": (56, 132, 255), "down": (120, 140, 180), "glow": (40, 110, 255), "accent": (120, 180, 255)},
    "gold":   {"bg": ((18, 12, 4), (60, 40, 8)), "up": (255, 196, 46), "down": (150, 110, 50), "glow": (255, 170, 0), "accent": (255, 215, 110)},
    "crypto": {"bg": ((4, 20, 18), (6, 50, 40)), "up": (14, 203, 129), "down": (246, 70, 93), "glow": (14, 203, 129), "accent": (120, 255, 200)},
    "risk":   {"bg": ((14, 8, 30), (44, 20, 70)), "up": (14, 203, 129), "down": (246, 70, 93), "glow": (150, 90, 255), "accent": (200, 170, 255)},
}


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def gradient(theme):
    a, b = THEMES[theme]["bg"]
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(0, W, 4):
            t = min(1, (x / W) * 0.55 + (y / H) * 0.45)
            c = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
            for k in range(4):
                if x + k < W:
                    px[x + k, y] = c
    return img


def grid(d, color):
    for x in range(0, W, 120):
        d.line([(x, 0), (x, H)], fill=color, width=1)
    for y in range(0, H, 120):
        d.line([(0, y), (W, y)], fill=color, width=1)


def walk(rng, n, start=100.0, vol=1.6, drift=0.12):
    v, out = start, []
    for _ in range(n):
        o = v
        c = o + rng.gauss(drift, vol)
        h = max(o, c) + abs(rng.gauss(0, vol * 0.6))
        l = min(o, c) - abs(rng.gauss(0, vol * 0.6))
        out.append((o, h, l, c))
        v = c
    return out


def candles(img, rng, theme, n=70, top=170, bottom=1120, left=80, right=2320):
    d = ImageDraw.Draw(img, "RGBA")
    th = THEMES[theme]
    data = walk(rng, n, vol=rng.uniform(1.2, 2.2), drift=rng.uniform(-0.05, 0.35))
    lo = min(x[2] for x in data); hi = max(x[1] for x in data)
    sy = lambda v: bottom - (v - lo) / (hi - lo) * (bottom - top)
    step = (right - left) / n
    # moving average glow
    closes = [c[3] for c in data]
    ma = [sum(closes[max(0, i - 8):i + 1]) / len(closes[max(0, i - 8):i + 1]) for i in range(n)]
    pts = [(left + step * (i + .5), sy(ma[i])) for i in range(n)]
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line(pts, fill=th["glow"] + (200,), width=26)
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img.paste(glow, (0, 0), glow)
    for i, (o, h, l, c) in enumerate(data):
        x = left + step * (i + .5)
        col = th["up"] if c >= o else th["down"]
        d.line([(x, sy(h)), (x, sy(l))], fill=col + (230,), width=4)
        y1, y2 = sorted([sy(o), sy(c)])
        d.rounded_rectangle([x - step * .32, y1, x + step * .32, max(y2, y1 + 4)], 4, fill=col + (255,))
    d.line(pts, fill=th["accent"] + (255,), width=5)
    return data


def area(img, rng, theme):
    d = ImageDraw.Draw(img, "RGBA")
    th = THEMES[theme]
    v, pts = 0.0, []
    for i in range(160):
        v += rng.gauss(0.35, 3.2)
        pts.append(v)
    lo, hi = min(pts), max(pts)
    xy = [(60 + i * (W - 120) / 159, 1100 - (p - lo) / (hi - lo) * 760) for i, p in enumerate(pts)]
    poly = xy + [(W - 60, H), (60, H)]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.polygon(poly, fill=th["glow"] + (70,))
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.paste(layer, (0, 0), layer)
    d.line(xy, fill=th["accent"] + (255,), width=7)
    x, y = xy[-1]
    d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=th["accent"] + (255,))


def depth(img, rng, theme):
    d = ImageDraw.Draw(img, "RGBA")
    th = THEMES[theme]
    mid = W // 2
    for side, col in ((-1, th["up"]), (1, th["down"])):
        cum, pts = 0, [(mid, 1120)]
        for i in range(1, 60):
            cum += rng.uniform(4, 22) * (1 + i / 30)
            pts.append((mid + side * i * 18, 1120 - cum))
        pts.append((mid + side * 59 * 18, 1120))
        d.polygon(pts, fill=col + (90,), outline=col + (255,))
        d.line(pts[:-1], fill=col + (255,), width=6)


def gauge(img, rng, theme, label="1:500"):
    d = ImageDraw.Draw(img, "RGBA")
    th = THEMES[theme]
    cx, cy, r = 1700, 820, 470
    for i in range(0, 181, 3):
        a = math.radians(180 + i)
        t = i / 180
        col = (int(14 + 232 * t), int(203 - 133 * t), int(129 - 36 * t))
        x1, y1 = cx + (r - 70) * math.cos(a), cy + (r - 70) * math.sin(a)
        x2, y2 = cx + r * math.cos(a), cy + r * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=col + (255,), width=14)
    a = math.radians(180 + rng.uniform(120, 165))
    d.line([(cx, cy), (cx + (r - 110) * math.cos(a), cy + (r - 110) * math.sin(a))], fill=(255, 255, 255, 255), width=14)
    d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=th["accent"] + (255,))
    f = font(FONT_B, 110)
    w = d.textlength(label, font=f)
    d.text((cx - w / 2, cy + 60), label, font=f, fill=(255, 255, 255, 235))


def shield(img, theme):
    d = ImageDraw.Draw(img, "RGBA")
    th = THEMES[theme]
    cx, cy = 1780, 640
    pts = [(cx, cy - 420), (cx + 340, cy - 300), (cx + 320, cy + 80), (cx, cy + 420), (cx - 320, cy + 80), (cx - 340, cy - 300)]
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(pts, fill=th["glow"] + (160,))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img.paste(glow, (0, 0), glow)
    d.polygon(pts, fill=(255, 255, 255, 18), outline=th["accent"] + (255,), width=12)
    d.line([(cx - 150, cy), (cx - 30, cy + 130), (cx + 180, cy - 140)], fill=th["accent"] + (255,), width=40, joint="curve")


def platform(img, rng, theme):
    d = ImageDraw.Draw(img, "RGBA")
    for k, (x, y) in enumerate([(1320, 250), (1520, 470)]):
        d.rounded_rectangle([x, y, x + 840, y + 680], 28, fill=(10, 18, 34, 235), outline=(90, 130, 200, 255), width=4)
        d.rectangle([x, y, x + 840, y + 60], fill=(30, 46, 80, 255))
        for j, c in enumerate([(246, 70, 93), (255, 196, 46), (14, 203, 129)]):
            d.ellipse([x + 26 + j * 40, y + 18, x + 50 + j * 40, y + 42], fill=c + (255,))
        f = font(FONT_M, 34)
        d.text((x + 160, y + 12), "MT4" if k == 0 else "MT5", font=f, fill=(200, 215, 240, 255))
        sub = Image.new("RGB", (1000, 580), (10, 18, 34))
        candles(sub, rng, theme, n=40, top=30, bottom=550, left=10, right=990) if False else None
        rr = random.Random(rng.random())
        data = walk(rr, 40)
        lo = min(z[2] for z in data); hi = max(z[1] for z in data)
        for i, (o, h, l, c) in enumerate(data):
            xx = x + 30 + i * 20
            sy = lambda v: y + 640 - (v - lo) / (hi - lo) * 540
            col = (56, 132, 255) if c >= o else (120, 140, 180)
            d.line([(xx, sy(h)), (xx, sy(l))], fill=col + (255,), width=3)
            y1, y2 = sorted([sy(o), sy(c)])
            d.rectangle([xx - 8, y1, xx + 8, max(y2, y1 + 3)], fill=col + (255,))


def title_block(img, kicker, ticker, theme):
    d = ImageDraw.Draw(img, "RGBA")
    th = THEMES[theme]
    # left fade so text reads well
    fade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for x in range(0, 1300):
        a = int(170 * (1 - x / 1300) ** 1.4)
        fd.line([(x, 0), (x, H)], fill=(0, 0, 0, a))
    img.paste(fade, (0, 0), fade)
    d.rounded_rectangle([110, 120, 110 + 22 + d.textlength(kicker, font=font(FONT_B, 44)) + 22, 196], 18, fill=th["up"] + (255,))
    d.text((132, 130), kicker, font=font(FONT_B, 44), fill=(5, 10, 20, 255))
    d.text((106, 230), ticker, font=font(FONT_B, 150), fill=(255, 255, 255, 245))


def vignette(img):
    v = Image.new("L", img.size, 0)
    vd = ImageDraw.Draw(v)
    vd.ellipse([-W * .25, -H * .4, W * 1.25, H * 1.4], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(200))
    black = Image.new("RGB", img.size, (0, 0, 0))
    return Image.composite(img, black, v)


SPECS = {
    "how-to-choose-a-forex-broker": ("forex", "candles", "FOREX BROKERS", "EUR/USD"),
    "forex-leverage-explained": ("forex", "gauge", "LEVERAGE", "1:500?"),
    "crypto-futures-trading-guide": ("crypto", "candles", "CRYPTO FUTURES", "BTC/USDT"),
    "how-to-trade-gold-xauusd": ("gold", "candles", "GOLD TRADING", "XAU/USD"),
    "risk-management-for-traders": ("risk", "area", "RISK MANAGEMENT", "−1% MAX"),
    "how-to-use-trading-signals": ("crypto", "depth", "TRADING SIGNALS", "BUY / SELL"),
    "mt4-vs-mt5": ("forex", "platform", "PLATFORMS", "MT4 vs MT5"),
    "crypto-exchange-safety": ("crypto", "shield", "SECURITY", "2FA ON"),
    "what-is-forex-trading": ("forex", "area", "FOREX BASICS", "GBP/USD"),
    "best-forex-broker-ranking": ("forex", "candles", "BEST FOREX BROKER", "RANKED"),
    "best-crypto-exchange-ranking": ("crypto", "depth", "BEST CRYPTO EXCHANGE", "RANKED"),
}
EXTRA_PAGES = ["best-forex-broker-ranking", "best-crypto-exchange-ranking"]


def make(slug, theme, kind, kicker, ticker):
    rng = random.Random(slug)
    img = gradient(theme)
    d = ImageDraw.Draw(img, "RGBA")
    grid(d, (255, 255, 255, 14))
    if kind == "candles":
        candles(img, rng, theme, left=700)
    elif kind == "area":
        area(img, rng, theme)
    elif kind == "depth":
        depth(img, rng, theme)
    elif kind == "gauge":
        area(img, rng, theme)
        gauge(img, rng, theme, "1:500")
    elif kind == "shield":
        area(img, rng, theme)
        shield(img, theme)
    elif kind == "platform":
        platform(img, rng, theme)
    img = vignette(img)
    if kicker:
        title_block(img, kicker, ticker, theme)
    return img


def main():
    articles = sorted((ROOT / "data" / "articles").glob("*.md"))
    targets = [(f.stem, f) for f in articles] + [(s, None) for s in EXTRA_PAGES]
    for slug, f in targets:
        if (OUT / f"{slug}.jpg").exists():
            continue  # keep existing pictures (and any photo you added yourself)
        spec = SPECS.get(slug)
        if not spec:
            text = f.read_text(encoding="utf-8").lower() if f else ""
            theme = "gold" if "gold" in text[:400] else "crypto" if "crypto" in text[:400] else "forex"
            spec = (theme, random.Random(slug).choice(["candles", "area", "depth"]), "TRADING GUIDE", "")
        img = make(slug, *spec)
        img.save(OUT / f"{slug}.jpg", quality=86, optimize=True, progressive=True)
        print("wrote", slug)
    # home page backgrounds (no text)
    if (OUT / "hero-forex.jpg").exists() and (OUT / "hero-crypto.jpg").exists():
        print("done"); return
    make("hero-forex", "forex", "candles", "", "").save(OUT / "hero-forex.jpg", quality=82, optimize=True, progressive=True)
    make("hero-crypto", "crypto", "candles", "", "").save(OUT / "hero-crypto.jpg", quality=82, optimize=True, progressive=True)
    print("done")


if __name__ == "__main__":
    main()
