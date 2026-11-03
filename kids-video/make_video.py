#!/usr/bin/env python3
"""동물 친구들과 숫자 놀이 (1~10) — 어린이용 숫자 학습 영상 생성기.

필요: Python3, Pillow, numpy, ffmpeg, Noto Color Emoji 폰트
실행: python3 make_video.py  ->  animal_numbers.mp4
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1280, 720, 30
SR = 44100
FONT = os.path.join(HERE, "fonts", "Jua.woff")
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
OUT = os.path.join(HERE, "animal_numbers.mp4")

# 숫자, 고유어, 한자어, 동물, 조사, 개수 표현, 이모지, 배경색
SCENES = [
    (1, "하나", "일", "강아지", "가", "한 마리", "🐶", (255, 228, 225)),
    (2, "둘", "이", "고양이", "가", "두 마리", "🐱", (255, 243, 205)),
    (3, "셋", "삼", "토끼", "가", "세 마리", "🐰", (225, 245, 254)),
    (4, "넷", "사", "병아리", "가", "네 마리", "🐤", (232, 245, 233)),
    (5, "다섯", "오", "곰돌이", "가", "다섯 마리", "🐻", (255, 236, 210)),
    (6, "여섯", "육", "펭귄", "이", "여섯 마리", "🐧", (227, 242, 253)),
    (7, "일곱", "칠", "아기 돼지", "가", "일곱 마리", "🐷", (252, 228, 236)),
    (8, "여덟", "팔", "개구리", "가", "여덟 마리", "🐸", (237, 247, 214)),
    (9, "아홉", "구", "판다", "가", "아홉 마리", "🐼", (240, 235, 255)),
    (10, "열", "십", "햄스터", "가", "열 마리", "🐹", (255, 240, 220)),
]
NUM_COLORS = [(255, 99, 132), (255, 159, 64), (54, 162, 235), (75, 192, 120),
              (255, 140, 0), (30, 136, 229), (236, 64, 122), (67, 160, 71),
              (126, 87, 194), (244, 81, 30)]

INTRO, OUTRO = 5.0, 9.0
HEAD, STEP, TAIL = 2.2, 0.7, 2.6


def scene_len(n):
    return HEAD + n * STEP + TAIL


# ---------------------------------------------------------------- fonts
_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, max(1, size))
    return _fonts[size]


_emoji_base = {}
_emoji_cache = {}


def emoji(ch, size):
    size = max(4, int(size))
    key = (ch, size)
    if key not in _emoji_cache:
        if ch not in _emoji_base:
            f = ImageFont.truetype(EMOJI_FONT, 109)
            im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
            _emoji_base[ch] = im.crop(im.getbbox())
        b = _emoji_base[ch]
        s = size / max(b.size)
        _emoji_cache[key] = b.resize((max(1, int(b.width * s)), max(1, int(b.height * s))), Image.LANCZOS)
        if len(_emoji_cache) > 600:
            _emoji_cache.clear()
    return _emoji_cache[key]


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def pop(t, dur=0.35):
    """0 -> 1 with a springy overshoot."""
    if t <= 0:
        return 0.0
    if t >= dur:
        return 1.0
    x = t / dur
    c1, c3 = 1.70158 * 1.4, 1.70158 * 1.4 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------------------------------------------------------- drawing helpers
def text_c(d, xy, s, size, fill, stroke=(255, 255, 255), sw=8, anchor="mm"):
    d.text(xy, s, font=font(size), fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=stroke)


def paste_c(img, sprite, cx, cy):
    img.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))


def background(color, t, seed=0):
    img = Image.new("RGBA", (W, H), color + (255,))
    d = ImageDraw.Draw(img)
    # 부드러운 구름
    for i in range(4):
        x = ((i * 380 + seed * 97 + t * 25) % (W + 300)) - 150
        y = 70 + (i % 2) * 60
        for dx, dy, r in ((0, 0, 38), (40, -15, 48), (85, 0, 38), (40, 12, 40)):
            d.ellipse((x + dx - r, y + dy - r, x + dx + r, y + dy + r), fill=(255, 255, 255, 255))
    # 잔디 언덕
    d.ellipse((-200, H - 120, W * 0.7, H + 260), fill=(150, 215, 120, 255))
    d.ellipse((W * 0.35, H - 100, W + 250, H + 260), fill=(130, 200, 105, 255))
    # 작은 꽃
    for i in range(9):
        fx = 60 + i * 145 + (seed * 31 % 50)
        fy = H - 45 + (i % 3) * 12
        sway = math.sin(t * 2 + i) * 3
        for k in range(5):
            a = k * 2 * math.pi / 5
            px, py = fx + sway + math.cos(a) * 9, fy + math.sin(a) * 9
            d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(255, 255, 255, 255))
        d.ellipse((fx + sway - 6, fy - 6, fx + sway + 6, fy + 6), fill=(255, 205, 60, 255))
    return img


def star(d, cx, cy, r, color, rot=0.0):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        a = rot + k * math.pi / 5 - math.pi / 2
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.polygon(pts, fill=color)


def grid_positions(n):
    rows = 1 if n <= 5 else 2
    per = [n] if rows == 1 else [math.ceil(n / 2), n - math.ceil(n / 2)]
    size = 150 if n <= 5 else 125
    gap = 200 if n <= 5 else 175
    pos = []
    top = 390 if rows == 1 else 270
    for r, cnt in enumerate(per):
        y = top + r * 170
        x0 = W / 2 - (cnt - 1) * gap / 2 + 90
        for c in range(cnt):
            pos.append((x0 + c * gap, y))
    return pos, size


# ---------------------------------------------------------------- scenes
def draw_intro(t):
    img = background((255, 245, 230), t, 3)
    d = ImageDraw.Draw(img)
    animals = [s[6] for s in SCENES]
    for i, a in enumerate(animals):
        p = pop(t - 0.15 * i)
        if p <= 0:
            continue
        cx = 110 + i * 118
        cy = 480 + math.sin(t * 5 + i) * 18
        paste_c(img, emoji(a, 95 * p), cx, cy)
    s = pop(t - 0.4, 0.6)
    if s > 0:
        text_c(d, (W / 2, 190), "동물 친구들과", int(70 * s), (255, 120, 80), sw=10)
        text_c(d, (W / 2, 300), "숫자 놀이!", int(120 * s), (60, 140, 230), sw=12)
    if t > 2.6:
        text_c(d, (W / 2, 640), "1부터 10까지 같이 세어 볼까요?", 44, (110, 80, 60), sw=7)
    return img


def draw_number_scene(idx, t):
    n, word, sino, animal, josa, count_word, em, bg = SCENES[idx]
    col = NUM_COLORS[idx]
    img = background(bg, t, idx)
    d = ImageDraw.Draw(img)

    # 왼쪽 큰 숫자
    p = pop(t, 0.5)
    if p > 0:
        r = 115 * p
        cx, cy = 170, 300
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,), outline=(255, 255, 255, 255), width=10)
        wob = 1 + 0.04 * math.sin(t * 6)
        text_c(d, (cx, cy + 6), str(n), int(150 * p * wob), (255, 255, 255), stroke=col, sw=0)
    p2 = pop(t - 0.6, 0.45)
    if p2 > 0:
        text_c(d, (170, 470), word, int(78 * p2), col, sw=9)
        text_c(d, (170, 540), f"({sino})", int(40 * p2), (120, 100, 90), sw=6)

    # 동물이 하나씩 등장
    pos, size = grid_positions(n)
    appeared = 0
    for i in range(n):
        ti = t - HEAD - i * STEP
        if ti < 0:
            continue
        appeared = i + 1
        sc = pop(ti, 0.4)
        bounce = abs(math.sin((t * 3.2) + i * 0.7)) * 14
        x, y = pos[i]
        paste_c(img, emoji(em, size * sc), x, y - bounce)
        # 몇 번째인지 숫자 표시
        if sc > 0.6:
            text_c(d, (x, y + size * 0.62), str(i + 1), 40, col, sw=6)

    # 방금 나온 친구 위에 세는 말풍선
    counting = SCENES[appeared - 1][1] if appeared else None
    t_last = t - HEAD - (appeared - 1) * STEP if appeared else 0
    end_t = HEAD + n * STEP
    if appeared and t < end_t + 0.1:
        x, y = pos[appeared - 1]
        bs = pop(t_last, 0.25)
        by = y - size * 0.85
        bw, bh = 120 * bs, 58 * bs
        if bs > 0.05:
            d.rounded_rectangle((x - bw / 2, by - bh / 2, x + bw / 2, by + bh / 2), radius=int(25 * bs),
                                fill=(255, 255, 255, 255), outline=col + (255,), width=4)
            text_c(d, (x, by + 2), counting, int(40 * bs), col, sw=0)

    # 마지막 문장
    tt = t - end_t - 0.2
    if tt > 0:
        s = pop(tt, 0.5)
        d.rounded_rectangle((W / 2 - 430 + 90, 615 - 48 * s, W / 2 + 430 + 90, 615 + 48 * s), radius=40,
                            fill=(255, 255, 255, 235), outline=col + (255,), width=5)
        text_c(d, (W / 2 + 90, 617), f"{animal}{josa} {count_word} 있어요!", int(54 * s), col, sw=0)
        for k in range(6):
            a = t * 1.5 + k * math.pi / 3
            star(d, W / 2 + 90 + math.cos(a) * 470, 615 + math.sin(a) * 70, 16, (255, 210, 60, 255), t * 3)
    return img


def draw_outro(t):
    img = background((255, 248, 225), t, 7)
    d = ImageDraw.Draw(img)
    # 반짝이 색종이
    if t > 3.0:
        rng = np.random.default_rng(1)
        for k in range(60):
            x0, sp, ph = rng.uniform(0, W), rng.uniform(80, 200), rng.uniform(0, 5)
            y = ((t - 3.0) * sp + ph * 100) % (H + 40) - 20
            x = x0 + math.sin(t * 2 + k) * 20
            c = NUM_COLORS[k % 10] + (255,)
            if k % 3 == 0:
                star(d, x, y, 10, c, t * 4 + k)
            else:
                d.rectangle((x - 5, y - 8, x + 5, y + 8), fill=c)
    # 1~10 복습
    for i, sc in enumerate(SCENES):
        p = pop(t - 0.25 * i, 0.35)
        if p <= 0:
            continue
        cx = 100 + i * 120
        hop = abs(math.sin(t * 4 + i * 0.6)) * 16 if t > 3 else 0
        paste_c(img, emoji(sc[6], 90 * p), cx, 330 - hop)
        r = 34 * p
        d.ellipse((cx - r, 425 - r, cx + r, 425 + r), fill=NUM_COLORS[i] + (255,))
        text_c(d, (cx, 428), str(sc[0]), int(40 * p), (255, 255, 255), sw=0)
        text_c(d, (cx, 485), sc[1], int(34 * p), NUM_COLORS[i], sw=5)
    s = pop(t - 3.0, 0.6)
    if s > 0:
        text_c(d, (W / 2, 140), "참 잘했어요!", int(100 * s), (255, 110, 90), sw=12)
    s2 = pop(t - 5.0, 0.5)
    if s2 > 0:
        text_c(d, (W / 2, 610), "다음에 또 만나요~ 안녕!", int(60 * s2), (60, 140, 230), sw=9)
    return img


# ---------------------------------------------------------------- timeline
def timeline():
    segs = [("intro", None, INTRO)]
    for i in range(len(SCENES)):
        segs.append(("num", i, scene_len(SCENES[i][0])))
    segs.append(("outro", None, OUTRO))
    return segs


def fade(img, t, dur):
    a = min(clamp(t / 0.3), clamp((dur - t) / 0.3))
    if a >= 1:
        return img
    white = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    return Image.blend(white, img, a)


# ---------------------------------------------------------------- audio
def note_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(freq, dur, vol=0.3):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 6) * np.minimum(1, t * 200)
    w = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.12 * np.sin(6 * np.pi * freq * t)
    return vol * env * w


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def pop_sfx(pitch):
    t = np.arange(int(SR * 0.18)) / SR
    f = pitch * (1 + 1.5 * np.exp(-t * 40))
    return 0.45 * np.exp(-t * 22) * np.sin(2 * np.pi * np.cumsum(f) / SR)


def chime():
    out = np.zeros(int(SR * 1.2))
    for k, m in enumerate((84, 88, 91, 96)):
        add(out, pluck(note_freq(m), 1.0, 0.18), k * 0.07)
    return out


def tada():
    out = np.zeros(int(SR * 2.0))
    for k, m in enumerate((72, 76, 79)):
        add(out, pluck(note_freq(m), 0.4, 0.25), k * 0.12)
    for m in (72, 76, 79, 84):
        add(out, pluck(note_freq(m), 1.6, 0.18), 0.38)
    return out


def build_audio(total, segs):
    buf = np.zeros(int(SR * (total + 1)))
    # 배경 음악: 밝은 C장조 반복 멜로디 (120 BPM)
    beat = 0.5
    melody = [72, 76, 79, 76, 77, 74, 71, 74, 72, 76, 79, 84, 81, 79, 77, 76]
    chords = [(48, 55, 64), (53, 60, 65), (55, 62, 67), (48, 55, 64)]
    nbeats = int(total / beat)
    for b in range(nbeats):
        at = b * beat
        add(buf, pluck(note_freq(melody[b % 16]), 0.45, 0.07), at)
        if b % 2 == 1:
            add(buf, pluck(note_freq(melody[(b + 2) % 16] + 12), 0.2, 0.025), at + beat / 2)
        if b % 4 == 0:
            for m in chords[(b // 4) % 4]:
                add(buf, pluck(note_freq(m), 2.0, 0.05), at)
    # 효과음
    start = 0.0
    for kind, idx, dur in segs:
        if kind == "intro":
            for i in range(10):
                add(buf, pop_sfx(500 + 60 * i), start + 0.15 * i)
            add(buf, chime(), start + 0.4)
        elif kind == "num":
            n = SCENES[idx][0]
            add(buf, chime(), start + 0.05)
            for i in range(n):
                add(buf, pop_sfx(520 * 2 ** (i / 12 * 2)), start + HEAD + i * STEP)
            add(buf, tada(), start + HEAD + n * STEP + 0.2)
        else:
            for i in range(10):
                add(buf, pop_sfx(520 * 2 ** (i / 12 * 2)), start + 0.25 * i)
            add(buf, tada(), start + 3.0)
            add(buf, chime(), start + 5.0)
        start += dur
    buf = buf[: int(SR * total)]
    # 끝부분 페이드아웃
    fl = int(SR * 1.5)
    buf[-fl:] *= np.linspace(1, 0, fl)
    buf = np.tanh(buf * 1.2) * 0.9
    return (buf * 32767).astype(np.int16)


# ---------------------------------------------------------------- main
def main():
    segs = timeline()
    total = sum(s[2] for s in segs)
    wav_path = os.path.join(HERE, "_audio.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(build_audio(total, segs).tobytes())

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_path,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frame_no = 0
    for kind, idx, dur in segs:
        nf = int(round(dur * FPS))
        for f in range(nf):
            t = f / FPS
            if kind == "intro":
                img = draw_intro(t)
            elif kind == "num":
                img = draw_number_scene(idx, t)
            else:
                img = draw_outro(t)
            img = fade(img, t, dur)
            proc.stdin.write(img.convert("RGB").tobytes())
            frame_no += 1
        print(f"  {kind} {'' if idx is None else idx + 1} done", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    os.remove(wav_path)
    print(f"완성: {OUT} ({total:.1f}초, {frame_no} frames)")


if __name__ == "__main__":
    main()
