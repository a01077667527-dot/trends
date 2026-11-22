"""다른 한 마리 찾기 – 움직이는 4×4 그리드 쇼츠 (1080x1920).

입력: 반복 GIF 1개(같은 캐릭터). 한 칸만 매 프레임에 같은 '미세 변경'을 적용.
사용법:
  python3 odd_grid.py out/cat/cat.gif out/cat/odd_nose.mp4 --odd nose --n 4 --time 15 --seed 3
변경 종류(--odd): nose(코 색), eye(눈동자 색), ear(귀 안쪽 색), stripe(이마 줄무늬 색)
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageSequence, ImageFont
from shorts import music, tone, SR

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
F = lambda s: ImageFont.truetype(FONT, s)
INK, RED, GREEN, YEL = "#3a2a2a", "#e53935", "#3f8f6a", "#ffd43b"


def hsv(a):
    rgb = a / 255.0
    mx, mn = rgb.max(2), rgb.min(2)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.select([mx == r, mx == g], [((g - b) / d) % 6, (b - r) / d + 2], (r - g) / d + 4) * 60
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return h, s, mx


def odd_edit(img, kind):
    a = np.asarray(img).astype(float)
    h, s, v = hsv(a)
    if kind == "nose":      # 분홍 코 → 연갈색
        m = ((h > 330) | (h < 12)) & (s > 0.18) & (v > 0.6)
        tgt = np.array([190, 135, 105.0])
    elif kind == "eye":     # 갈색 눈동자 → 초록
        m = (v < 0.45) & (v > 0.12) & (s > 0.15) & (s < 0.7) & ((h < 40) | (h > 340))
        tgt = np.array([60, 110, 70.0])
    elif kind == "ear":     # (흰 귀 안쪽은 색이 없어 대신) 볼 점 → 진하게
        m = (h > 20) & (h < 40) & (s > 0.25) & (s < 0.45) & (v > 0.8)
        tgt = np.array([200, 120, 60.0])
    else:                   # 진한 주황 줄무늬 → 갈색
        m = (h > 20) & (h < 38) & (s > 0.45) & (v > 0.75)
        tgt = np.array([175, 110, 70.0])
    lum = a.mean(2, keepdims=True)
    ref = np.median(lum[m]) if m.any() else 1
    out = a.copy()
    out[m] = np.clip(tgt * (lum[m] / ref), 0, 255)
    return Image.fromarray(out.astype(np.uint8))


def load_frames(gif, size):
    g = Image.open(gif)
    fr = [f.convert("RGB") for f in ImageSequence.Iterator(g)]
    w, h = fr[0].size
    side = min(w, h)
    box = ((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2)
    dur = sum(f.info.get("duration", 100) for f in ImageSequence.Iterator(Image.open(gif))) / 1000
    return [f.crop(box).resize((size, size), Image.LANCZOS) for f in fr], dur


def render(gif, out, odd="nose", n=4, find=15, seed=1, title="다른 고양이 한 마리를 찾아보세요!"):
    rnd = random.Random(seed)
    gap, margin = 12, 30
    cell = (W - 2 * margin - (n - 1) * gap) // n
    frames, loop = load_frames(gif, cell)
    odd_frames = [odd_edit(f, odd) for f in frames]
    k_odd = rnd.randrange(n * n)
    phase = [rnd.random() * loop for _ in range(n * n)]
    top = 430
    grid_h = n * cell + (n - 1) * gap
    rev, end = 3.5, 2.5
    total = find + rev + end

    base = Image.new("RGB", (W, H), "#fff3dc")
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((30, 120, W - 30, 250), 65, fill=GREEN)
    d.text((W // 2, 185), title, font=F(60), fill="#fff", anchor="mm")
    d.text((W // 2, 330), f"딱 한 마리만 살짝 달라요", font=F(52), fill=INK, anchor="mm")
    d.rounded_rectangle((margin - 14, top - 14, W - margin + 14, top + grid_h + 14), 30, fill="#ffffff")

    # 소리
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    put(0.05, np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)]))
    for s in range(find - 5, find):
        put(s, tone([1200 if s < find - 1 else 1600], .08, .03, .35))
    put(find + .2, np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .8, .35, .45)]))
    m = music(total, "pluck"); a[: len(m)] += m / np.abs(m).max() * np.abs(a).max() * .3
    wav = out + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a / np.abs(a).max() * .7 * 32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                           "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    nf = len(frames)
    by = top + grid_h + 60
    for f in range(int(total * FPS)):
        t = f / FPS
        fr = base.copy(); dd = ImageDraw.Draw(fr)
        for k in range(n * n):
            r_, c_ = divmod(k, n)
            x, y = margin + c_ * (cell + gap), top + r_ * (cell + gap)
            idx = int(((t + phase[k]) % loop) / loop * nf) % nf
            fr.paste((odd_frames if k == k_odd else frames)[idx], (x, y))
        remain = max(0.0, find - t)
        col = RED if remain <= 5 else GREEN
        dd.text((90, by + 40), "찾아보기" if remain > 0 else "정답!", font=F(54), fill=INK, anchor="lm")
        dd.text((W - 90, by + 40), f"{math.ceil(remain)}초" if remain > 0 else "", font=F(64), fill=col, anchor="rm")
        dd.rounded_rectangle((90, by + 100, W - 90, by + 134), 17, fill="#eadfcc")
        if remain > 0:
            dd.rounded_rectangle((90, by + 100, 90 + max(34, (W - 180) * remain / find), by + 134), 17, fill=col)
        if t >= find:
            r_, c_ = divmod(k_odd, n)
            cx, cy = margin + c_ * (cell + gap) + cell / 2, top + r_ * (cell + gap) + cell / 2
            pop = 1 + .3 * max(0, 1 - (t - find) / .3)
            rr = cell * .62 * pop
            dd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=RED, width=12)
        if t >= find + rev:
            dd.rounded_rectangle((90, by + 170, W - 90, by + 300), 65, fill=RED)
            dd.text((W / 2, by + 235), "찾으셨나요? 댓글로 알려주세요!", font=F(50), fill="#fff", anchor="mm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    r_, c_ = divmod(k_odd, n)
    print(f"완료: {out}  정답 = {r_+1}번째 줄 {c_+1}번째 칸 ({odd})  {total:.1f}초")


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    render(a[0], a[1], opt("--odd", "nose"), opt("--n", 4), opt("--time", 15), opt("--seed", 1))
