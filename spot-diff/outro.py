"""쇼츠 마지막 구독 부탁 장면 (모든 쇼츠 공통)."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTRO_SEC = 2.0
W, H = 1080, 1920
GREEN, RED = "#3f8f6a", "#e53935"
HERE = os.path.dirname(os.path.abspath(__file__))
MASCOT = os.path.join(HERE, "..", "brand", "v2", "logo_A.png")
FONT = next(p for p in ["/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
                        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"] if os.path.exists(p))
F = lambda s: ImageFont.truetype(FONT, s)

_base = None


def _bell(d, cx, cy, s):
    d.pieslice((cx - 26 * s, cy - 30 * s, cx + 26 * s, cy + 22 * s), 180, 360, fill="#fff")
    d.rectangle((cx - 26 * s, cy - 4 * s, cx + 26 * s, cy + 14 * s), fill="#fff")
    d.polygon([(cx - 26 * s, cy + 14 * s), (cx + 26 * s, cy + 14 * s), (cx + 34 * s, cy + 24 * s), (cx - 34 * s, cy + 24 * s)], fill="#fff")
    d.ellipse((cx - 8 * s, cy + 24 * s, cx + 8 * s, cy + 36 * s), fill="#fff")


def base():
    global _base
    if _base is None:
        im = Image.new("RGB", (W, H), GREEN)
        d = ImageDraw.Draw(im)
        if os.path.exists(MASCOT):
            m = Image.open(MASCOT).convert("RGB").resize((420, 420), Image.LANCZOS)
            mask = Image.new("L", (420, 420), 0); ImageDraw.Draw(mask).ellipse((0, 0, 420, 420), fill=255)
            d.ellipse((W // 2 - 222, 418, W // 2 + 222, 862), fill="#fff")
            im.paste(m, (W // 2 - 210, 430), mask)
        d.text((W // 2, 1000), "매일 새 문제!", font=F(104), fill="#fff", anchor="mm")
        d.text((W // 2, 1125), "구독하고 함께 해요", font=F(82), fill="#ffe3a3", anchor="mm")
        d.text((W // 2, 1480), "두뇌 건강 강화 프로젝트", font=F(48), fill="#d3f0e0", anchor="mm")
        _base = im
    return _base


def frame(t):
    """t: 구독 장면 시작 후 경과 초."""
    im = base().copy()
    d = ImageDraw.Draw(im)
    s = 1 + 0.06 * math.sin(t * 2 * math.pi * 1.6)          # 버튼이 콩닥콩닥
    bw, bh, cy = 470 * s, 140 * s, 1300
    d.rounded_rectangle((W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2), bh / 2, fill=RED)
    _bell(d, W / 2 - 110 * s, cy - 6 * s, 1.15 * s)
    d.text((W / 2 + 40 * s, cy), "구독", font=F(int(72 * s)), fill="#fff", anchor="mm")
    if t < 0.25:
        im = Image.blend(Image.new("RGB", (W, H), "#ffffff"), im, t / 0.25)
    return im


def sound(tone):
    """구독 장면 효과음 (shorts.tone 을 받아 사용)."""
    return np.concatenate([tone([784, 1568], .15, .1, .4), tone([1047, 2094], .2, .12, .4), tone([1568, 3136], .6, .3, .4)])
