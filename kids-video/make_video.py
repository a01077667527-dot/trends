#!/usr/bin/env python3
"""동물 친구들과 숫자 놀이 (1~10) — 고퀄리티 2D 애니메이션 버전.

모든 캐릭터·배경·글자를 cairo 벡터로 직접 그립니다 (외부 이미지 없음).
필요: Python3, pycairo, numpy, fonttools, ffmpeg
실행: python3 make_video.py            ->  animal_numbers.mp4
      python3 make_video.py --preview DIR   (몇 장면만 PNG로 저장)
"""
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import cairo
import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
SR = 44100
FONT = os.path.join(HERE, "fonts", "Jua.woff")
OUT = os.path.join(HERE, "animal_numbers.mp4")
TAU = math.tau

# ============================================================== data
# (숫자, 고유어, 한자어, 동물 이름, 조사, 개수, 캐릭터 종류)
SCENES = [
    (1, "하나", "일", "강아지", "가", "한 마리", "dog"),
    (2, "둘", "이", "고양이", "가", "두 마리", "cat"),
    (3, "셋", "삼", "토끼", "가", "세 마리", "rabbit"),
    (4, "넷", "사", "병아리", "가", "네 마리", "chick"),
    (5, "다섯", "오", "곰돌이", "가", "다섯 마리", "bear"),
    (6, "여섯", "육", "펭귄", "이", "여섯 마리", "penguin"),
    (7, "일곱", "칠", "아기 돼지", "가", "일곱 마리", "pig"),
    (8, "여덟", "팔", "개구리", "가", "여덟 마리", "frog"),
    (9, "아홉", "구", "판다", "가", "아홉 마리", "panda"),
    (10, "열", "십", "햄스터", "가", "열 마리", "hamster"),
]
WORDS = [s[1] for s in SCENES]


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


NUM_COLORS = [hx(c) for c in ("ff5c8a", "ff9a3c", "3aa0ff", "34c37a", "ff7a2f",
                              "2f7fe0", "f0508f", "4cae3f", "8a5cf0", "ff5a36")]
SKIES = [("8fd3ff", "e6f7ff"), ("ffd0a8", "fff3e0"), ("a8e0ff", "f0fbff"), ("c8f0b0", "f5fff0"),
         ("ffc9a0", "fff1e2"), ("9cc9ff", "eaf4ff"), ("ffc0d6", "fff0f5"), ("b8eba0", "f3ffe9"),
         ("cbb8ff", "f4efff"), ("ffd59a", "fff6e5")]
SKIES = [(hx(a), hx(b)) for a, b in SKIES]

# 캐릭터 색 (몸, 배, 포인트, 코)
ANIMALS = {
    "dog": dict(body="f2c48d", belly="fff1dc", accent="9a6240", nose="3a2a22"),
    "cat": dict(body="ffb34d", belly="fff0d6", accent="e0862a", nose="ff8fa3"),
    "rabbit": dict(body="f5f1f7", belly="ffffff", accent="ffb3c8", nose="ff8fa3"),
    "chick": dict(body="ffd93b", belly="fff3a8", accent="ff9d2e", nose="ff9d2e"),
    "bear": dict(body="b07444", belly="e8c39a", accent="7d4e2a", nose="3a2a22"),
    "penguin": dict(body="34456b", belly="ffffff", accent="ffa62e", nose="ffa62e"),
    "pig": dict(body="ffb8c8", belly="ffd9e2", accent="ff8fab", nose="ff8fab"),
    "frog": dict(body="7fd65a", belly="d9f7b5", accent="4fae35", nose="3a5a2a"),
    "panda": dict(body="fafafa", belly="ffffff", accent="2e2e36", nose="2e2e36"),
    "hamster": dict(body="f5b273", belly="fff5e6", accent="ffb3a0", nose="ff8fa3"),
}
for _a in ANIMALS.values():
    for _k in list(_a):
        _a[_k] = hx(_a[_k])

INTRO, OUTRO = 7.5, 12.0
HEAD, STEP, TAIL = 2.6, 0.8, 3.4
WIPE = 0.7


def scene_len(n):
    return HEAD + n * STEP + 0.6 + TAIL


# ============================================================== utilities
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def lighten(c, k):
    return mix(c, (1, 1, 1), k)


def darken(c, k):
    return mix(c, (0, 0, 0), k)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def back_out(t, s=2.2):
    t = clamp(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def elastic(t):
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 2 ** (-9 * t) * math.sin((t * 10 - 0.75) * TAU / 3) + 1


def hash01(*a):
    x = math.sin(sum((i + 1) * 12.9898 * v for i, v in enumerate(a)) + 78.233) * 43758.5453
    return x - math.floor(x)


# ============================================================== cairo helpers
def ell(ctx, cx, cy, rx, ry, rot=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    if rot:
        ctx.rotate(rot)
    ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()


def rgb(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


def radial_fill(ctx, c, cx, cy, r, hi=0.35, lo=0.12):
    g = cairo.RadialGradient(cx - r * 0.35, cy - r * 0.45, r * 0.05, cx, cy, r * 1.15)
    g.add_color_stop_rgb(0, *lighten(c, hi))
    g.add_color_stop_rgb(0.55, *c)
    g.add_color_stop_rgb(1, *darken(c, lo))
    ctx.set_source(g)


def paint_shape(ctx, fill, line=None, lw=3.0, grad=None):
    """현재 path를 채우고 테두리를 그린다. grad=(cx,cy,r) 이면 입체 그라디언트."""
    if grad:
        radial_fill(ctx, fill, *grad)
    else:
        rgb(ctx, fill)
    if line is None:
        ctx.fill()
        return
    ctx.fill_preserve()
    rgb(ctx, line)
    ctx.set_line_width(lw)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def round_rect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -TAU / 4, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, TAU / 4)
    ctx.arc(x + r, y + h - r, r, TAU / 4, TAU / 2)
    ctx.arc(x + r, y + r, r, TAU / 2, TAU * 3 / 4)
    ctx.close_path()


def star_path(ctx, cx, cy, r, rot=0.0, inner=0.45, pts=5):
    for k in range(pts * 2):
        rr = r if k % 2 == 0 else r * inner
        a = rot + k * math.pi / pts - math.pi / 2
        (ctx.move_to if k == 0 else ctx.line_to)(cx + math.cos(a) * rr, cy + math.sin(a) * rr)
    ctx.close_path()


def sparkle_path(ctx, cx, cy, r, rot=0.0):
    for k in range(4):
        a = rot + k * TAU / 4
        b = a + TAU / 8
        (ctx.move_to if k == 0 else ctx.line_to)(cx + math.cos(a) * r, cy + math.sin(a) * r)
        ctx.line_to(cx + math.cos(b) * r * 0.22, cy + math.sin(b) * r * 0.22)
    ctx.close_path()


# ============================================================== vector font
class CairoPen(BasePen):
    def __init__(self, gs, ctx):
        super().__init__(gs)
        self.ctx = ctx

    def _moveTo(self, p):
        self.ctx.move_to(*p)

    def _lineTo(self, p):
        self.ctx.line_to(*p)

    def _curveToOne(self, p1, p2, p3):
        self.ctx.curve_to(*p1, *p2, *p3)

    def _qCurveToOne(self, p1, p2):
        x0, y0 = self.ctx.get_current_point()
        self.ctx.curve_to(x0 + 2 / 3 * (p1[0] - x0), y0 + 2 / 3 * (p1[1] - y0),
                          p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]), *p2)

    def _closePath(self):
        self.ctx.close_path()


class VFont:
    def __init__(self, path):
        f = TTFont(path)
        self.upm = f["head"].unitsPerEm
        self.cmap = f.getBestCmap()
        self.gs = f.getGlyphSet()
        self.hmtx = f["hmtx"]
        self.cache = {}
        self._surf = cairo.ImageSurface(cairo.FORMAT_A8, 4, 4)

    def glyph(self, ch):
        if ch not in self.cache:
            name = self.cmap.get(ord(ch))
            ctx = cairo.Context(self._surf)
            if name and ch != " ":
                self.gs[name].draw(CairoPen(self.gs, ctx))
            adv = self.hmtx[name][0] if name else self.upm * 0.3
            self.cache[ch] = (ctx.copy_path(), adv)
        return self.cache[ch]

    def layout(self, s, size, tracking=0.02):
        sc = size / self.upm
        xs, x = [], 0.0
        for ch in s:
            _, adv = self.glyph(ch)
            xs.append((ch, x, adv * sc))
            x += adv * sc + tracking * size
        return xs, (x - tracking * size) if s else 0


VF = None


def vfont():
    global VF
    if VF is None:
        VF = VFont(FONT)
    return VF


def draw_text(ctx, s, cx, cy, size, fill, outline=(1, 1, 1), ow=None, shadow=True,
              grad=True, per_char=None, tracking=0.02):
    """(cx,cy)=글자 가운데. per_char(i) -> (scale, dy, rot, alpha)."""
    items, width = vfont().layout(s, size, tracking)
    ow = size * 0.16 if ow is None else ow
    sc_f = size / vfont().upm
    x0 = cx - width / 2
    mid = size * 0.33  # 베이스라인에서 글자 중심까지
    layers = (["shadow"] if shadow else []) + (["outline"] if ow > 0 else []) + ["fill"]
    for layer in layers:
        for i, (ch, x, adv) in enumerate(items):
            if ch == " ":
                continue
            sc, dy, rot, al = per_char(i) if per_char else (1, 0, 0, 1)
            if sc <= 0.01 or al <= 0.01:
                continue
            ctx.save()
            ctx.translate(x0 + x + adv / 2, cy + dy)
            ctx.rotate(rot)
            ctx.scale(sc, sc)
            if layer == "shadow":
                ctx.translate(0, size * 0.07)
            ctx.new_path()
            ctx.save()
            ctx.translate(-adv / 2, mid)
            ctx.scale(sc_f, -sc_f)
            ctx.append_path(vfont().glyph(ch)[0])
            ctx.restore()
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            if layer == "shadow":
                rgb(ctx, darken(fill, 0.55), 0.3 * al)
                ctx.set_line_width(max(ow, 1) * 2)
                ctx.stroke_preserve()
                ctx.fill()
            elif layer == "outline":
                rgb(ctx, outline, al)
                ctx.set_line_width(ow * 2)
                ctx.stroke()
            else:
                if grad:
                    g = cairo.LinearGradient(0, -size * 0.45, 0, size * 0.4)
                    g.add_color_stop_rgba(0, *lighten(fill, 0.35), al)
                    g.add_color_stop_rgba(1, *darken(fill, 0.1), al)
                    ctx.set_source(g)
                else:
                    rgb(ctx, fill, al)
                ctx.fill_preserve()
                ctx.clip()
                ctx.new_path()
                ctx.rectangle(-size, -size * 0.5, size * 2, size * 0.2)
                ctx.set_source_rgba(1, 1, 1, 0.22 * al)
                ctx.fill()
            ctx.restore()
    return width


# ============================================================== background
def draw_background(ctx, sky, t, seed=0, cam=0.0, clear_zone=True):
    top, bot = sky
    g = cairo.LinearGradient(0, 0, 0, H * 0.7)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bot)
    ctx.set_source(g)
    ctx.paint()

    # 해님
    sx, sy = 1760 - cam * 10, 140
    g = cairo.RadialGradient(sx, sy, 0, sx, sy, 230)
    g.add_color_stop_rgba(0, 1, 0.95, 0.6, 0.7)
    g.add_color_stop_rgba(1, 1, 0.95, 0.6, 0)
    ctx.set_source(g)
    ctx.arc(sx, sy, 230, 0, TAU)
    ctx.fill()
    ctx.save()
    ctx.translate(sx, sy)
    ctx.rotate(t * 0.25)
    for k in range(12):
        ctx.save()
        ctx.rotate(k * TAU / 12)
        ctx.move_to(-15, -100)
        ctx.line_to(0, -140 - 10 * math.sin(t * 3 + k))
        ctx.line_to(15, -100)
        ctx.close_path()
        ctx.set_source_rgba(1, 0.82, 0.25, 0.7)
        ctx.fill()
        ctx.restore()
    ctx.restore()
    ell(ctx, sx, sy, 85, 85)
    paint_shape(ctx, hx("ffd64a"), hx("ffb52e"), 5, grad=(sx, sy, 85))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for d in (-1, 1):
        ctx.new_path()
        ctx.arc(sx + d * 28, sy, 11, math.pi * 1.15, math.pi * 1.85)
        ctx.set_line_width(6)
        rgb(ctx, hx("8a5a1a"))
        ctx.stroke()
        ell(ctx, sx + d * 46, sy + 22, 14, 9)
        rgb(ctx, hx("ff8a6a"), 0.55)
        ctx.fill()
    ctx.new_path()
    ctx.arc(sx, sy + 12, 22, 0.15 * math.pi, 0.85 * math.pi)
    rgb(ctx, hx("8a5a1a"))
    ctx.stroke()

    # 반짝이
    for k in range(14):
        x = hash01(k, seed) * W
        y = 40 + hash01(k, seed, 2) * 420
        tw = 0.5 + 0.5 * math.sin(t * 2.5 + k * 1.7)
        sparkle_path(ctx, x, y, 6 + 9 * tw, t * 0.6 + k)
        ctx.set_source_rgba(1, 1, 1, 0.3 + 0.55 * tw)
        ctx.fill()

    # 구름
    for k in range(5):
        spd = 18 + 10 * hash01(k, 7)
        x = ((hash01(k, seed, 3) * (W + 600) + t * spd - cam * 30) % (W + 600)) - 300
        y = 90 + hash01(k, 9, seed) * 250
        draw_cloud(ctx, x, y, 0.7 + 0.5 * hash01(k, 5))

    # 먼 언덕 (패럴랙스)
    ox = -cam * 40
    for yb, col, ph, amp in ((620, hx("bfe8a6"), 0.0, 160), (690, hx("9fdc84"), 2.0, 120)):
        ctx.move_to(-50, H)
        for i in range(0, W + 101, 20):
            x = i - 50
            y = yb - amp * (0.5 + 0.5 * math.sin((x + ox) / 300 + ph)) * (0.6 + 0.4 * math.sin((x + ox) / 170 + ph * 2))
            ctx.line_to(x, y)
        ctx.line_to(W + 50, H)
        ctx.close_path()
        rgb(ctx, col)
        ctx.fill()
    for k in range(4):
        x = ((150 + k * 520 + ox * 1.3 + seed * 90) % (W + 200)) - 100
        draw_tree(ctx, x, 650 + 25 * hash01(k, seed), 0.8 + 0.3 * hash01(k, 2), t, k)

    # 앞 잔디
    g = cairo.LinearGradient(0, 720, 0, H)
    g.add_color_stop_rgb(0, *hx("8ad86e"))
    g.add_color_stop_rgb(1, *hx("5fb84a"))
    ctx.move_to(-50, H)
    for i in range(0, W + 101, 20):
        x = i - 50
        ctx.line_to(x, 740 + 18 * math.sin((x - cam * 70) / 260))
    ctx.line_to(W + 50, H)
    ctx.close_path()
    ctx.set_source(g)
    ctx.fill()
    for k in range(70):
        x = hash01(k, 11) * W
        y = 790 + hash01(k, 13) * 280
        sway = math.sin(t * 2 + x / 120) * 5
        ctx.move_to(x - 6, y)
        ctx.curve_to(x - 2, y - 15, x + sway, y - 28, x + sway * 1.5, y - 34)
        ctx.curve_to(x + 2, y - 20, x + 4, y - 10, x + 6, y)
        rgb(ctx, hx("4ea53b"), 0.55)
        ctx.fill()
    petals = [hx("ffffff"), hx("ffd1e1"), hx("fff1a0"), hx("d6e4ff")]
    for k in range(18):
        x = hash01(k, 17, seed) * W
        y = 800 + hash01(k, 19) * 250
        if clear_zone and 520 < x < 1850:
            continue  # 캐릭터 자리 비우기
        draw_flower(ctx, x, y, petals[k % 4], t, k, 0.8 + 0.4 * hash01(k, 3))


def draw_cloud(ctx, x, y, s):
    blobs = [(-70, 10, 45), (-25, -18, 60), (35, -10, 55), (80, 12, 40), (0, 18, 50)]
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for bx, by, r in blobs:
        ctx.new_sub_path()
        ctx.arc(bx, by + 12, r, 0, TAU)
    ctx.set_source_rgba(0.5, 0.65, 0.9, 0.16)
    ctx.fill()
    for bx, by, r in blobs:
        ctx.new_sub_path()
        ctx.arc(bx, by, r, 0, TAU)
    g = cairo.LinearGradient(0, -80, 0, 70)
    g.add_color_stop_rgb(0, 1, 1, 1)
    g.add_color_stop_rgb(1, 0.9, 0.95, 1)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()


def draw_tree(ctx, x, y, s, t, k):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    round_rect(ctx, -10, -70, 20, 75, 8)
    rgb(ctx, hx("a8754a"))
    ctx.fill()
    sw = math.sin(t * 1.3 + k) * 3
    for bx, by, r in ((0, -120, 55), (-38, -90, 40), (38, -90, 40)):
        ell(ctx, bx + sw, by, r, r)
        paint_shape(ctx, hx("6cc456"), None, grad=(bx + sw, by, r))
    ctx.restore()


def draw_flower(ctx, x, y, col, t, k, s):
    sway = math.sin(t * 2.2 + k) * 0.12
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, 0)
    ctx.curve_to(3, -15, math.sin(sway) * 30, -30, math.sin(sway) * 40, -40)
    ctx.set_line_width(4)
    rgb(ctx, hx("3f9a35"))
    ctx.stroke()
    ctx.translate(math.sin(sway) * 40, -40)
    ctx.rotate(sway + t * 0.3)
    for p in range(5):
        a = p * TAU / 5
        ell(ctx, math.cos(a) * 11, math.sin(a) * 11, 10, 7, a)
        paint_shape(ctx, col, darken(col, 0.15), 1.5)
    ell(ctx, 0, 0, 7, 7)
    rgb(ctx, hx("ffc531"))
    ctx.fill()
    ctx.restore()


# ============================================================== characters
def draw_animal(ctx, kind, x, y, scale, st):
    """(x,y)=발 위치. st: hop, sx, sy, blink, happy, mouth, arm, tilt, head_tilt, num, t"""
    P = ANIMALS[kind]
    body, belly, acc, nose = P["body"], P["belly"], P["accent"], P["nose"]
    line = darken(body, 0.38)
    if kind == "panda":
        line = hx("3a3a44")
    if kind == "penguin":
        line = hx("1e2740")
    t = st.get("t", 0)
    hop = st.get("hop", 0.0)
    blink, happy = st.get("blink", 0.0), st.get("happy", 0.0)
    mouth, arm = st.get("mouth", 0.0), st.get("arm", 0.0)
    num = st.get("num")
    lw = 3.2
    dark = hx("2e2e36")

    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    sh = clamp(1 - hop / 300)
    ell(ctx, 0, 2, 52 * (0.6 + 0.4 * sh), 11 * (0.6 + 0.4 * sh))
    ctx.set_source_rgba(0.1, 0.25, 0.1, 0.22 * sh)
    ctx.fill()

    ctx.translate(0, -hop)
    ctx.scale(st.get("sx", 1.0), st.get("sy", 1.0))
    ctx.rotate(st.get("tilt", 0.0))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    feet_col = acc if kind in ("chick", "penguin") else (dark if kind == "panda" else darken(body, 0.12))
    for d in (-1, 1):
        ell(ctx, d * 20, -7, 16, 10)
        paint_shape(ctx, feet_col, darken(feet_col, 0.35), lw)

    # 꼬리
    if kind in ("cat", "dog"):
        wag = math.sin(t * 8) * 0.3
        ctx.save()
        ctx.translate(28, -30)
        ctx.rotate(-0.6 + wag)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(25, -5, 35, -35, 30, -50 if kind == "cat" else -35)
        tw = 13 if kind == "cat" else 15
        ctx.set_line_width(tw)
        rgb(ctx, line)
        ctx.stroke_preserve()
        ctx.set_line_width(tw - 2 * lw)
        rgb(ctx, body)
        ctx.stroke()
        ctx.restore()
    if kind == "rabbit":
        ell(ctx, 33, -25, 14, 14)
        paint_shape(ctx, (1, 1, 1), line, lw)
    if kind == "pig":
        ctx.new_path()
        ctx.arc(38, -32, 7, 0, 5)
        ctx.set_line_width(4)
        rgb(ctx, line)
        ctx.stroke()

    # 팔
    arm_col = dark if kind == "panda" else body
    for d in (-1, 1):
        ctx.save()
        ctx.translate(d * 27, -50)
        ctx.rotate((0.45 + arm * 2.3 + 0.1 * math.sin(t * 9 + d) * arm) * d)
        if kind in ("chick", "penguin"):
            ell(ctx, d * 3, 20, 11, 24)
        else:
            ell(ctx, 0, 18, 10.5, 19)
        paint_shape(ctx, arm_col, darken(arm_col, 0.35) if kind != "panda" else hx("15151a"), lw)
        ctx.restore()

    # 몸통
    bcol = dark if kind == "panda" else body
    ell(ctx, 0, -40, 37, 35)
    paint_shape(ctx, bcol, line, lw, grad=(0, -40, 37))
    ell(ctx, 0, -36, 24, 23)
    paint_shape(ctx, belly if kind != "panda" else (0.98, 0.98, 0.98), None)
    if num is not None and num[1] > 0.01:  # 배 번호
        ns = num[1]
        ell(ctx, 0, -37, 19 * ns, 19 * ns)
        paint_shape(ctx, (1, 1, 1), num[2], 3)
        draw_text(ctx, str(num[0]), 0, -37, (26 if num[0] < 10 else 22) * ns, num[2], ow=0, shadow=False, grad=False)

    # ---- 머리
    ctx.save()
    ctx.translate(0, -100)
    ctx.rotate(st.get("head_tilt", 0.0))
    if kind == "rabbit":
        for d in (-1, 1):
            bend = 0.12 * math.sin(t * 3 + d) + (0.45 if d > 0 else 0) * (0.5 + 0.5 * math.sin(t * 1.5))
            ctx.save()
            ctx.translate(d * 18, -30)
            ctx.rotate(d * (0.12 + bend))
            ell(ctx, 0, -38, 14, 40)
            paint_shape(ctx, body, line, lw)
            ell(ctx, 0, -36, 7, 30)
            paint_shape(ctx, acc, None)
            ctx.restore()
    elif kind == "cat":
        for d in (-1, 1):
            ctx.save()
            ctx.translate(d * 30, -28)
            ctx.rotate(d * (0.35 + 0.05 * math.sin(t * 4)))
            ctx.new_path()
            ctx.move_to(-18, 8)
            ctx.line_to(0, -32)
            ctx.line_to(18, 8)
            ctx.close_path()
            paint_shape(ctx, body, line, lw)
            ctx.move_to(-9, 4)
            ctx.line_to(0, -19)
            ctx.line_to(9, 4)
            ctx.close_path()
            paint_shape(ctx, hx("ffb3c1"), None)
            ctx.restore()
    elif kind in ("bear", "panda", "hamster"):
        r = 15 if kind != "hamster" else 12
        for d in (-1, 1):
            ex, ey = d * 34, -32
            ell(ctx, ex, ey, r, r)
            paint_shape(ctx, dark if kind == "panda" else body, line, lw)
            if kind != "panda":
                ell(ctx, ex, ey, r * 0.55, r * 0.55)
                paint_shape(ctx, acc if kind == "hamster" else lighten(body, 0.3), None)
    elif kind == "pig":
        for d in (-1, 1):
            ctx.save()
            ctx.translate(d * 30, -30)
            ctx.rotate(d * (0.5 + 0.08 * math.sin(t * 5)))
            ctx.new_path()
            ctx.move_to(-14, 6)
            ctx.curve_to(-10, -20, 6, -30, 16, 4)
            ctx.close_path()
            paint_shape(ctx, body, line, lw)
            ctx.restore()
    elif kind == "frog":
        for d in (-1, 1):
            ell(ctx, d * 22, -32, 19, 18)
            paint_shape(ctx, body, line, lw, grad=(d * 22, -32, 19))

    rx, ry = {"frog": (52, 38), "hamster": (50, 43)}.get(kind, (48, 42))
    ell(ctx, 0, 0, rx, ry)
    paint_shape(ctx, body, line, lw, grad=(0, 0, rx))

    if kind == "penguin":
        for d in (-1, 1):
            ell(ctx, d * 15, 5, 23, 28)
        rgb(ctx, (1, 1, 1))
        ctx.fill()
    if kind == "cat":
        ctx.new_path()
        for i, dx in enumerate((-11, 0, 11)):
            ctx.move_to(dx, -38 + (4 if i != 1 else 0))
            ctx.line_to(dx, -27 + (2 if i != 1 else 0))
        ctx.set_line_width(5)
        rgb(ctx, acc)
        ctx.stroke()
    if kind == "dog":
        ell(ctx, 19, -6, 15, 14, 0.3)
        rgb(ctx, lighten(acc, 0.4))
        ctx.fill()
    if kind in ("dog", "bear", "hamster"):
        ell(ctx, 0, 16, 22 if kind != "hamster" else 30, 15)
        rgb(ctx, belly if kind != "bear" else lighten(body, 0.45))
        ctx.fill()
    if kind == "panda":
        for d in (-1, 1):
            ell(ctx, d * 18, -1, 13, 17, -d * 0.5)
            rgb(ctx, dark)
            ctx.fill()
    if kind == "chick":
        for k, a in enumerate((-0.4, 0, 0.4)):
            ctx.save()
            ctx.translate(0, -38)
            ctx.rotate(a + 0.12 * math.sin(t * 4 + k))
            ell(ctx, 0, -10, 6, 13)
            paint_shape(ctx, body, line, 2.5)
            ctx.restore()

    # 볼
    for d in (-1, 1):
        ell(ctx, d * 31, 14, 10, 6.5)
        rgb(ctx, hx("ff7f9e"), 0.45)
        ctx.fill()

    # 눈
    frog = kind == "frog"
    eye_y, eye_dx = (-33, 22) if frog else (-4, 17)
    eye_ink = hx("2a1e1a")
    for d in (-1, 1):
        ex = d * eye_dx + st.get("look", 0.0) * 3
        if frog:
            ell(ctx, d * eye_dx, eye_y, 12, 12)
            rgb(ctx, (1, 1, 1))
            ctx.fill()
        happy_col = (1, 1, 1) if kind == "panda" else eye_ink
        if happy > 0.5:
            ctx.new_path()
            ctx.arc(ex, eye_y + 4, 8, math.pi * 1.15, math.pi * 1.85)
            ctx.set_line_width(4.5)
            rgb(ctx, happy_col)
            ctx.stroke()
        elif blink > 0.85:
            ctx.new_path()
            ctx.move_to(ex - 7, eye_y)
            ctx.line_to(ex + 7, eye_y)
            ctx.set_line_width(4)
            rgb(ctx, happy_col)
            ctx.stroke()
        else:
            o = 1 - blink
            ell(ctx, ex, eye_y, 7.5, 9.5 * o)
            rgb(ctx, eye_ink if kind != "panda" else hx("101014"))
            ctx.fill()
            ell(ctx, ex + 2.5, eye_y - 3.5 * o, 2.8, 3.2 * o)
            rgb(ctx, (1, 1, 1))
            ctx.fill()
            ell(ctx, ex - 2.5, eye_y + 3.5 * o, 1.4, 1.4 * o)
            ctx.fill()

    # 코 / 부리 / 입
    my = 18
    if kind in ("chick", "penguin"):
        ctx.new_path()
        ctx.move_to(-11, 8)
        ctx.curve_to(-4, 2, 4, 2, 11, 8)
        ctx.curve_to(6, 13, 2, 16, 0, 16)
        ctx.curve_to(-2, 16, -6, 13, -11, 8)
        paint_shape(ctx, acc, darken(acc, 0.3), 2)
        if mouth > 0.2:
            op = mouth * 7
            ctx.move_to(-8, 13)
            ctx.curve_to(-4, 18 + op, 4, 18 + op, 8, 13)
            ctx.close_path()
            paint_shape(ctx, darken(acc, 0.1), darken(acc, 0.3), 2)
    elif kind == "pig":
        ell(ctx, 0, 12, 17, 12)
        paint_shape(ctx, acc, darken(acc, 0.25), 2.5)
        for d in (-1, 1):
            ell(ctx, d * 6, 12, 3, 4.5)
            rgb(ctx, darken(acc, 0.45))
            ctx.fill()
        my = 29
    elif not frog:
        big = kind in ("dog", "bear", "panda")
        ell(ctx, 0, 8, 7 if big else 4.5, 5 if big else 3.5)
        rgb(ctx, nose)
        ctx.fill()
        ell(ctx, -1.5, 6.5, 2, 1.3)
        ctx.set_source_rgba(1, 1, 1, 0.7)
        ctx.fill()
    if kind not in ("chick", "penguin"):
        mc = hx("5a2a2a")
        if frog:
            my = 8
        if mouth > 0.15:
            mh = 4 + 10 * mouth
            mw = 20 if frog else 9
            ctx.new_path()
            ctx.move_to(-mw, my - 2)
            ctx.curve_to(-mw * 0.6, my + mh * 1.3, mw * 0.6, my + mh * 1.3, mw, my - 2)
            ctx.close_path()
            paint_shape(ctx, hx("c2414f"), mc, 2.5)
            ell(ctx, 0, my + mh * 0.6, mw * 0.5, mh * 0.3)
            rgb(ctx, hx("ff8a9a"))
            ctx.fill()
        else:
            ctx.new_path()
            if frog:
                ctx.arc(0, my - 14, 22, 0.25 * math.pi, 0.75 * math.pi)
            else:
                ctx.move_to(-10, my - 3)
                ctx.curve_to(-8, my + 3, -2, my + 3, 0, my - 1)
                ctx.curve_to(2, my + 3, 8, my + 3, 10, my - 3)
            ctx.set_line_width(3.2)
            rgb(ctx, mc)
            ctx.stroke()
        if kind == "rabbit":
            round_rect(ctx, -5, my - 1, 10, 9, 2)
            paint_shape(ctx, (1, 1, 1), hx("c9c2cc"), 1.5)
        if kind == "dog" and mouth <= 0.15:
            ell(ctx, 3, my + 6, 5, 7)
            paint_shape(ctx, hx("ff7a8f"), hx("c2414f"), 1.5)
    if kind in ("cat", "rabbit", "hamster"):
        ctx.new_path()
        for d in (-1, 1):
            for k in (-1, 1):
                ctx.move_to(d * 24, 10 + k * 3)
                ctx.line_to(d * 44, 6 + k * 7)
        ctx.set_line_width(2)
        rgb(ctx, darken(body, 0.4), 0.7)
        ctx.stroke()
    if kind == "dog":  # 처진 귀 (얼굴 위)
        for d in (-1, 1):
            ctx.save()
            ctx.translate(d * 38, -24)
            ctx.rotate(d * (0.22 + 0.1 * math.sin(t * 4 + d)))
            ell(ctx, d * 6, 22, 15, 29)
            paint_shape(ctx, acc, darken(acc, 0.35), lw)
            ctx.restore()

    ell(ctx, -18, -24, 14, 7, -0.5)
    ctx.set_source_rgba(1, 1, 1, 0.32)
    ctx.fill()
    ctx.restore()  # head
    ctx.restore()


def idle_state(t, seed):
    breathe = math.sin(t * 3 + seed) * 0.02
    bl = (t + hash01(seed) * 3) % (2.6 + hash01(seed, 1) * 1.6)
    blink = 1.0 if bl < 0.12 else (0.5 if bl < 0.16 else 0.0)
    return dict(t=t, sx=1 + breathe, sy=1 - breathe, blink=blink, arm=0.06 * math.sin(t * 2 + seed),
                head_tilt=0.06 * math.sin(t * 1.3 + seed), hop=abs(math.sin(t * 2.2 + seed)) * 4)


def jump_state(tj, dur=0.55, height=110):
    """점프 시작 후 시간 tj. 웅크림 -> 늘어남 -> 착지 스쿼시."""
    if tj < 0:
        return {}
    if tj < 0.08:
        k = tj / 0.08
        return dict(sx=1 + 0.15 * k, sy=1 - 0.18 * k)
    tj -= 0.08
    if tj < dur:
        p = tj / dur
        stretch = 0.12 * (1 - abs(2 * p - 1))
        return dict(hop=4 * p * (1 - p) * height, sx=1 - stretch, sy=1 + stretch, arm=0.9, happy=1.0, mouth=0.8)
    tj -= dur
    if tj < 0.22:
        k = math.sin(tj / 0.22 * math.pi) * (1 - tj / 0.22)
        return dict(sx=1 + 0.2 * k, sy=1 - 0.2 * k, happy=1.0, mouth=0.5)
    return {}


# ============================================================== UI pieces
def draw_dust(ctx, x, y, tt, scale):
    if not 0 <= tt < 0.5:
        return
    p = tt / 0.5
    for d in (-1, 1):
        for k in range(3):
            px = x + d * (30 + 70 * ease_out(p) + k * 18) * scale
            py = y - (8 + k * 10) * scale * ease_out(p)
            ctx.new_path()
            ctx.arc(px, py, (10 + k * 4) * scale * (1 - p * 0.5), 0, TAU)
            ctx.set_source_rgba(1, 1, 1, 0.75 * (1 - p))
            ctx.fill()


def draw_bubble(ctx, x, y, text, s, col):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    _, w = vfont().layout(text, 64)
    bw, bh = w + 64, 92
    round_rect(ctx, -bw / 2, -bh / 2 + 7, bw, bh, 46)
    ctx.set_source_rgba(0, 0, 0, 0.12)
    ctx.fill()
    ctx.new_path()
    ctx.move_to(-16, bh / 2 - 4)
    ctx.line_to(0, bh / 2 + 24)
    ctx.line_to(16, bh / 2 - 4)
    ctx.close_path()
    paint_shape(ctx, (1, 1, 1), col, 5)
    round_rect(ctx, -bw / 2, -bh / 2, bw, bh, 46)
    paint_shape(ctx, (1, 1, 1), col, 5)
    ctx.rectangle(-17, bh / 2 - 6, 34, 6)
    rgb(ctx, (1, 1, 1))
    ctx.fill()
    draw_text(ctx, text, 0, 0, 64, col, ow=0, shadow=False)
    ctx.restore()


def draw_number_badge(ctx, n, cx, cy, s, t, col):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(s, s)
    ctx.save()
    ctx.rotate(t * 0.5)
    star_path(ctx, 0, 0, 200, 0, 0.84, 12)
    rgb(ctx, lighten(col, 0.6))
    ctx.fill()
    ctx.restore()
    ell(ctx, 0, 12, 160, 160)
    ctx.set_source_rgba(0, 0, 0, 0.15)
    ctx.fill()
    ell(ctx, 0, 0, 160, 160)
    paint_shape(ctx, col, (1, 1, 1), 14, grad=(0, 0, 160))
    ell(ctx, -55, -75, 55, 26, -0.6)
    ctx.set_source_rgba(1, 1, 1, 0.3)
    ctx.fill()
    wob = 1 + 0.035 * math.sin(t * 5)
    draw_text(ctx, str(n), 0, 0, (230 if n < 10 else 190) * wob, (1, 1, 1), outline=darken(col, 0.25), ow=9,
              shadow=True, grad=False)
    for k in range(3):
        a = t * 1.2 + k * TAU / 3
        sparkle_path(ctx, math.cos(a) * 215, math.sin(a) * 215, 22 + 6 * math.sin(t * 6 + k), t * 2)
        rgb(ctx, hx("fff27a"))
        ctx.fill()
    ctx.restore()


def letter_pop(t0, step=0.06, dur=0.45):
    def f(i):
        tt = t0 - i * step
        if tt <= 0:
            return (0, 0, 0, 0)
        p = clamp(tt / dur)
        return (back_out(p), -40 * (1 - ease_out(p)), 0.3 * (1 - ease_out(p)), clamp(p * 3))
    return f


def letter_wave(t, amp=8, spd=4, ph=0.5):
    return lambda i: (1, -abs(math.sin(t * spd - i * ph)) * amp, 0, 1)


def combine(a, b):
    def f(i):
        s1, d1, r1, a1 = a(i)
        s2, d2, r2, a2 = b(i)
        return (s1 * s2, d1 + d2, r1 + r2, a1 * a2)
    return f


def draw_confetti(ctx, tt, seed, count):
    if tt <= 0:
        return
    for k in range(count):
        spd = 180 + 160 * hash01(k, seed, 22)
        y = -40 + tt * spd - hash01(k, seed, 23) * 500
        if y < -40 or y > H + 40:
            continue
        x = hash01(k, seed, 21) * W + math.sin(tt * 2 + k) * 40
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(tt * 4 + k)
        if k % 3 == 0:
            star_path(ctx, 0, 0, 14)
        else:
            ctx.scale(1, abs(math.cos(tt * 6 + k)) + 0.1)
            round_rect(ctx, -8, -12, 16, 24, 3)
        rgb(ctx, NUM_COLORS[k % 10])
        ctx.fill()
        ctx.restore()


# ============================================================== layout
def slots(n):
    """(x, 발 y, 크기, 순서)"""
    if n <= 5:
        return [(1140 + (i - (n - 1) / 2) * 270, 900, 1.62) for i in range(n)]
    back = math.ceil(n / 2)
    front = n - back
    out = [(1080 + (i - (back - 1) / 2) * 250, 720, 1.2) for i in range(back)]
    shift = 125 if front == back else 0  # 앞줄은 뒷줄 사이사이에 서기
    out += [(1080 + shift + (i - (front - 1) / 2) * 250, 975, 1.4) for i in range(front)]
    return out


# ============================================================== scenes
def scene_intro(ctx, t):
    draw_background(ctx, (hx("9fd8ff"), hx("fff4e0")), t, 42, cam=t * 0.2, clear_zone=False)
    for i, sc in enumerate(SCENES):
        tx = 150 + i * 180
        ti = t - 0.25 * i
        if ti < 0:
            continue
        p = ease_out(ti / 1.2)
        sx = lerp(-250 if i < 5 else W + 250, tx, p)
        st = idle_state(t, i)
        if ti < 1.2:
            st.update(hop=abs(math.sin(ti * 9)) * 60 * (1 - p), arm=0.6, mouth=0.6)
        elif t > 4.2:
            jt = (t - 4.2 - i * 0.12) % 2.4
            st.update(jump_state(jt, 0.5, 90))
        st["tilt"] = 0.05 * math.sin(t * 3 + i)
        draw_animal(ctx, sc[6], sx, 990 if i % 2 else 940, 1.12, st)
    if t > 1.0:
        f = combine(letter_pop(t - 1.0, 0.08), letter_wave(t, 6, 3, 0.6))
        draw_text(ctx, "동물 친구들과", W / 2, 210, 130, hx("ff7a5c"), per_char=f)
    if t > 2.0:
        f = combine(letter_pop(t - 2.0, 0.1, 0.6), letter_wave(t, 10, 3.5, 0.7))
        draw_text(ctx, "숫자 놀이!", W / 2, 420, 230, hx("3d8ef0"), ow=30, per_char=f)
    if t > 3.6:
        a = ease_out((t - 3.6) / 0.6)
        draw_text(ctx, "1부터 10까지 같이 세어 볼까요?", W / 2, 610, 62, hx("8a5a3a"),
                  per_char=lambda i: (1, 20 * (1 - a), 0, a))


def scene_number(ctx, idx, t):
    n, word, sino, animal, josa, count_word, kind = SCENES[idx]
    col = NUM_COLORS[idx]
    draw_background(ctx, SKIES[idx], t, idx, cam=t * 0.15)

    draw_number_badge(ctx, n, 260, 330, elastic(clamp((t - 0.15) / 0.9)) * 0.95, t, col)
    if t > 0.9:
        f = combine(letter_pop(t - 0.9, 0.1, 0.5), letter_wave(t, 6, 3, 0.6))
        draw_text(ctx, word, 260, 600, 120, col, ow=18, per_char=f)
    if t > 1.4:
        a = ease_out((t - 1.4) / 0.4)
        draw_text(ctx, f"({sino})", 260, 705, 58, hx("8a6a5a"), per_char=lambda i: (a, 0, 0, a))

    sl = slots(n)
    cheer0 = HEAD + n * STEP + 0.6
    fly = 0.55
    for i in sorted(range(n), key=lambda i: sl[i][1]):  # 뒷줄 먼저
        x, y, s = sl[i]
        ti = t - (HEAD + i * STEP)
        if ti < 0:
            continue
        st = idle_state(t, i * 3 + idx)
        if ti < fly:  # 오른쪽에서 포물선 점프로 등장
            p = ti / fly
            px = lerp(W + 200, x, ease_io(p))
            st.update(hop=4 * p * (1 - p) * 420 + (1 - p) * 120, sx=0.9, sy=1.12, arm=1.0, mouth=0.7,
                      tilt=-0.35 * (1 - p))
            draw_animal(ctx, kind, px, y, s, st)
            continue
        tl = ti - fly
        if tl < 0.25:
            q = math.sin(tl / 0.25 * math.pi) * (1 - tl / 0.25 * 0.5)
            st.update(sx=1 + 0.22 * q, sy=1 - 0.22 * q, hop=0)
        if tl < 0.9:
            st.update(mouth=0.7 * (1 - tl / 0.9) + 0.1, happy=1.0 if tl < 0.5 else 0.0)
        tc = t - cheer0 - i * 0.09
        if tc > 0:
            st.update(jump_state(tc % 1.35, 0.5, 120))
            st["mouth"] = max(st.get("mouth", 0), 0.5)
        st["num"] = (i + 1, back_out(clamp((tl - 0.1) / 0.35)), col)
        draw_animal(ctx, kind, x, y, s, st)
        draw_dust(ctx, x, y, tl, s)
    for i in range(n):  # 세는 말풍선
        tl = t - (HEAD + i * STEP + fly)
        if 0 <= tl < 0.75:
            x, y, s = sl[i]
            sc = back_out(clamp(tl / 0.25)) * (1 if tl < 0.6 else 1 - (tl - 0.6) / 0.15)
            draw_bubble(ctx, x, y - 160 * s - 75, WORDS[i], sc, col)
    if t > cheer0 - 0.2:
        tt = t - cheer0 + 0.2
        text = f"{animal}{josa} {count_word} 있어요!"
        _, w = vfont().layout(text, 84)
        bw = w + 120
        s = back_out(clamp(tt / 0.45))
        cx, cy = 1140, 125
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(s, s)
        round_rect(ctx, -bw / 2, -56, bw, 132, 66)
        ctx.set_source_rgba(0, 0, 0, 0.12)
        ctx.fill()
        round_rect(ctx, -bw / 2, -66, bw, 132, 66)
        paint_shape(ctx, (1, 1, 1), col, 7)
        ctx.restore()
        if s > 0.5:
            f = combine(letter_pop(tt - 0.2, 0.045, 0.4), letter_wave(t, 5, 4, 0.5))
            draw_text(ctx, text, cx, cy, 84, col, ow=0, shadow=False, per_char=f)
            for k in range(8):
                a = t * 1.1 + k * TAU / 8
                sparkle_path(ctx, cx + math.cos(a) * (bw / 2 + 40), cy + math.sin(a) * 95,
                             16 + 6 * math.sin(t * 7 + k), t * 2 + k)
                rgb(ctx, hx("ffd23a"))
                ctx.fill()
    draw_confetti(ctx, t - cheer0, idx, 40)


def scene_outro(ctx, t):
    draw_background(ctx, (hx("ffcfe0"), hx("fff6e0")), t, 77, cam=t * 0.1, clear_zone=False)
    for i, sc in enumerate(SCENES):
        x = 140 + i * 182
        y = 880 if i % 2 == 0 else 975
        ti = t - 0.15 * i
        if ti < 0:
            continue
        st = idle_state(t, i + 50)
        st["hop"] += (1 - ease_out(clamp(ti / 0.6))) * 500
        hl = 2.2 + i * 0.55
        if t > hl:
            st.update(jump_state(t - hl, 0.45, 110))
        if t > 8.0:
            st.update(jump_state((t - 8.0 - i * 0.07) % 1.2, 0.45, 90))
            st["arm"] = 0.6 + 0.4 * math.sin(t * 10 + i)
        st["num"] = (i + 1, back_out(clamp((t - hl) / 0.35)) if t > hl else 0, NUM_COLORS[i])
        draw_animal(ctx, sc[6], x, y, 1.08, st)
    for i, sc in enumerate(SCENES):
        hl = 2.2 + i * 0.55
        if 0 < t - hl < 0.6:
            x = 140 + i * 182
            y = 880 if i % 2 == 0 else 975
            sc_ = back_out(clamp((t - hl) / 0.2)) * (1 - clamp((t - hl - 0.45) / 0.15))
            draw_bubble(ctx, x, y - 250, sc[1], sc_, NUM_COLORS[i])
    if 1.8 < t < 7.6:
        a = clamp((t - 1.8) / 0.4) * clamp((7.6 - t) / 0.4)
        draw_text(ctx, "다 같이 세어 봐요!", W / 2, 250, 120, hx("8a5cf0"), per_char=lambda i: (1, 0, 0, a))
    if t > 7.8:
        f = combine(letter_pop(t - 7.8, 0.08, 0.5), letter_wave(t, 10, 4, 0.6))
        draw_text(ctx, "참 잘했어요!", W / 2, 240, 190, hx("ff6a5a"), ow=26, per_char=f)
    if t > 9.0:
        f = combine(letter_pop(t - 9.0, 0.05, 0.4), letter_wave(t, 5, 3, 0.5))
        draw_text(ctx, "다음에 또 만나요~ 안녕!", W / 2, 450, 90, hx("3d8ef0"), per_char=f)
    draw_confetti(ctx, t - 7.8, 99, 90)


# ============================================================== timeline / render
SEGS = [("intro", None, INTRO)] + [("num", i, scene_len(s[0])) for i, s in enumerate(SCENES)] + [("outro", None, OUTRO)]
STARTS = list(np.cumsum([0] + [s[2] for s in SEGS[:-1]]))
TOTAL = sum(s[2] for s in SEGS)


def draw_seg(ctx, si, t):
    kind, idx, _ = SEGS[si]
    if kind == "intro":
        scene_intro(ctx, t)
    elif kind == "num":
        scene_number(ctx, idx, t)
    else:
        scene_outro(ctx, t)


def render_frame(fi):
    T = fi / FPS
    si = max(i for i, s in enumerate(STARTS) if s <= T + 1e-9)
    t = T - STARTS[si]
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    if si > 0 and t < WIPE:  # 원형 와이프 전환
        draw_seg(ctx, si - 1, SEGS[si - 1][2])
        r = ease_io(t / WIPE) * 1250
        ctx.save()
        ctx.new_path()
        ctx.arc(W / 2, H / 2, r, 0, TAU)
        ctx.clip()
        draw_seg(ctx, si, t)
        ctx.restore()
        ctx.new_path()
        ctx.arc(W / 2, H / 2, r, 0, TAU)
        ctx.set_line_width(28)
        rgb(ctx, (1, 1, 1))
        ctx.stroke()
        ctx.arc(W / 2, H / 2, r + 21, 0, TAU)
        ctx.set_line_width(14)
        rgb(ctx, NUM_COLORS[si % 10])
        ctx.stroke()
    else:
        draw_seg(ctx, si, t)
    a = min(clamp(T / 0.5), clamp((TOTAL - T) / 0.8))
    if a < 1:
        ctx.set_source_rgba(1, 1, 1, 1 - a)
        ctx.paint()
    surf.flush()
    return bytes(surf.get_data())


# ============================================================== audio
def nf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tone(freq, dur, vol, kind="bell"):
    t = np.arange(int(SR * dur)) / SR
    if kind == "bell":  # 글로켄슈필
        env = np.exp(-t * 4.5) * np.minimum(1, t * 400)
        w = (np.sin(TAU * freq * t) + 0.25 * np.sin(TAU * freq * 2.76 * t) * np.exp(-t * 9)
             + 0.1 * np.sin(TAU * freq * 5.4 * t) * np.exp(-t * 14))
    elif kind == "marimba":
        env = np.exp(-t * 7) * np.minimum(1, t * 300)
        w = np.sin(TAU * freq * t) + 0.15 * np.sin(TAU * freq * 4 * t) * np.exp(-t * 20)
    elif kind == "pad":
        env = np.minimum(1, t / 0.25) * np.clip((dur - t) / 0.4, 0, 1)
        w = sum(np.sin(TAU * freq * (1 + d) * t + d * 500) for d in (-0.004, 0, 0.004)) / 3
        w = w + 0.3 * np.sin(TAU * freq * 2 * t)
    else:  # bass
        env = np.exp(-t * 5) * np.minimum(1, t * 200)
        w = np.sin(TAU * freq * t) + 0.3 * np.sin(TAU * freq * 2 * t)
    return vol * env * w


def add(buf, sig, at):
    i = int(at * SR)
    if i < 0 or i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def kick():
    t = np.arange(int(SR * 0.25)) / SR
    f = 50 + 120 * np.exp(-t * 30)
    return 0.5 * np.exp(-t * 14) * np.sin(TAU * np.cumsum(f) / SR)


def noise_hit(dur, decay, vol, seed=0):
    n = np.random.default_rng(seed).uniform(-1, 1, int(SR * dur))
    n = np.diff(n, prepend=0)
    return vol * n * np.exp(-np.arange(len(n)) / SR * decay)


def boing(f0=300):
    t = np.arange(int(SR * 0.35)) / SR
    f = f0 * (1 + 0.8 * np.sin(t * 40) * np.exp(-t * 8)) * (1 + t * 2)
    return 0.2 * np.exp(-t * 7) * np.sin(TAU * np.cumsum(f) / SR)


def whoosh():
    n = np.random.default_rng(5).uniform(-1, 1, int(SR * 0.7))
    t = np.arange(len(n)) / SR
    return 0.5 * np.convolve(n, np.ones(30) / 30, mode="same") * np.sin(np.pi * t / 0.7) ** 2


def pop_sfx(pitch):
    t = np.arange(int(SR * 0.15)) / SR
    f = pitch * (1 + 2.0 * np.exp(-t * 50))
    return 0.3 * np.exp(-t * 25) * np.sin(TAU * np.cumsum(f) / SR)


def tada():
    out = np.zeros(int(SR * 2.5))
    for k, m in enumerate((72, 76, 79)):
        add(out, tone(nf(m), 0.3, 0.22, "marimba"), k * 0.1)
    for m in (72, 76, 79, 84):
        add(out, tone(nf(m), 2.0, 0.15, "bell"), 0.32)
    add(out, noise_hit(1.5, 3, 0.1, seed=3), 0.32)
    return out


def reverb(x):
    out = x.copy()
    for d, g in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.163, 0.15), (0.241, 0.1)):
        k = int(d * SR)
        out[k:] += g * x[:-k]
    return out


def build_audio():
    n = int(SR * (TOTAL + 3))
    music, sfx = np.zeros(n), np.zeros(n)
    beat = 60 / 112
    # 오리지널 멜로디 (C장조, 8마디) (음, 박자)
    mel = [(72, 1), (76, 1), (79, 1), (76, 1), (77, .5), (76, .5), (74, 1), (71, 2),
           (72, 1), (74, 1), (76, .5), (77, .5), (79, 1), (81, 1), (79, 1), (76, 2),
           (77, 1), (81, 1), (79, 1), (76, 1), (74, .5), (76, .5), (77, 1), (74, 2),
           (72, 1), (76, 1), (74, 1), (71, 1), (72, 4)]
    chords = [(60, 64, 67), (65, 69, 72), (67, 71, 74), (60, 64, 67),
              (65, 69, 72), (60, 64, 67), (67, 71, 74), (60, 64, 67)]
    bass = [48, 53, 55, 48, 53, 48, 55, 48]
    loop = sum(d for _, d in mel) * beat
    t0 = 0.0
    while t0 < TOTAL:
        b = 0.0
        for m, d in mel:
            add(music, tone(nf(m), d * beat + 0.6, 0.1, "bell"), t0 + b * beat)
            b += d
        for bar in range(8):
            at = t0 + bar * 4 * beat
            for m in chords[bar]:
                add(music, tone(nf(m), 4 * beat, 0.035, "pad"), at)
            for k in range(4):
                bt = at + k * beat
                add(music, tone(nf(bass[bar] + (0 if k % 2 == 0 else 7)), beat, 0.14, "bass"), bt)
                add(music, kick() * 0.55 if k % 2 == 0 else noise_hit(0.12, 30, 0.07, seed=k), bt)
                add(music, noise_hit(0.05, 80, 0.03, seed=k + 9), bt + beat / 2)
                add(music, tone(nf(chords[bar][k % 3] + 12), 0.4, 0.03, "marimba"), bt + beat / 2)
        t0 += loop
    scale = [72, 74, 76, 77, 79, 81, 83, 84, 86, 88]
    for si, (kind, idx, dur) in enumerate(SEGS):
        s0 = STARTS[si]
        if si > 0:
            add(sfx, whoosh(), s0 - 0.15)
        if kind == "intro":
            for i in range(10):
                add(sfx, boing(260 + 25 * i), s0 + 0.25 * i + 0.3)
            add(sfx, tada(), s0 + 2.0)
        elif kind == "num":
            n_ = SCENES[idx][0]
            add(sfx, tone(nf(84), 1.2, 0.22, "bell"), s0 + 0.2)
            add(sfx, tone(nf(91), 1.2, 0.16, "bell"), s0 + 0.32)
            for i in range(n_):
                land = s0 + HEAD + i * STEP + 0.55
                add(sfx, pop_sfx(500), s0 + HEAD + i * STEP)
                add(sfx, boing(220), land - 0.02)
                add(sfx, tone(nf(scale[i]), 0.9, 0.3, "marimba"), land)
                add(sfx, tone(nf(scale[i] + 12), 0.9, 0.1, "bell"), land)
            add(sfx, tada(), s0 + HEAD + n_ * STEP + 0.4)
        else:
            for i in range(10):
                add(sfx, boing(240), s0 + 0.15 * i + 0.3)
                hl = s0 + 2.2 + i * 0.55
                add(sfx, tone(nf(scale[i]), 0.9, 0.3, "marimba"), hl)
                add(sfx, tone(nf(scale[i] + 12), 0.9, 0.1, "bell"), hl)
            add(sfx, tada(), s0 + 7.8)
            add(sfx, tada(), s0 + 9.0)
    out = (reverb(music) * 0.8 + reverb(sfx) * 0.85)[: int(SR * TOTAL)]
    fl = int(SR * 2.0)
    out[-fl:] *= np.linspace(1, 0, fl)
    out = np.tanh(out * 1.1) * 0.92
    d = int(0.012 * SR)
    right = np.concatenate([np.zeros(d), out[:-d]]) * 0.85 + out * 0.15
    return (np.stack([out, right], axis=1) * 32767).astype(np.int16)


# ============================================================== main
def main():
    if "--preview" in sys.argv:
        from PIL import Image
        outdir = sys.argv[-1]
        picks = [(0, 3.5), (0, 6.0), (1, 1.4), (3, HEAD + 2 * STEP + 0.62), (6, scene_len(7) - 1.2),
                 (9, scene_len(10) - 1.6), (10, scene_len(10) - 0.9), (11, 4.0), (11, 9.6), (4, 0.35), (5, HEAD + 0.3)]
        for k, (si, t) in enumerate(picks):
            fr = render_frame(int(round((STARTS[si] + t) * FPS)))
            Image.frombuffer("RGBX", (W, H), fr, "raw", "BGRX").convert("RGB").save(os.path.join(outdir, f"p{k}.png"))
        return

    wav_path = os.path.join(HERE, "_audio.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(build_audio().tobytes())
    nframes = int(TOTAL * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "bgr0", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_path,
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "animation", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, fr in enumerate(pool.imap(render_frame, range(nframes), chunksize=6)):
            proc.stdin.write(fr)
            if k % 300 == 0:
                print(f"  {k}/{nframes}", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    os.remove(wav_path)
    print(f"완성: {OUT} ({TOTAL:.1f}초, {nframes} frames)")


if __name__ == "__main__":
    main()
