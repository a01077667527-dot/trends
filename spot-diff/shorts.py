"""쇼츠용(1080x1920) 기억력 틀린그림 영상.

구성: 인트로/썸네일 2초 → 기억하기 15초 → 찾아보기 15초 → 정답 10초
배경음악: 직접 합성한 잔잔한 오르골풍 음악(저작권 걱정 없음) + 효과음

사용법:
  python3 shorts.py out/camping2 out/camping2/shorts.mp4
  옵션: --times 15,15,10  --intro 2  --no-music  --no-crop(가로 그림 자르지 않기)
결과: shorts.mp4 와 같은 폴더에 thumbnail.png 도 저장
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from video import tone, FONT, SR

W, H, FPS = 1080, 1920, 30
BG, INK, GREEN, ORANGE, RED = "#fff3dc", "#3a2a2a", "#3f8f6a", "#e08a2e", "#e53935"
F = lambda s: ImageFont.truetype(FONT, s)
HERE = os.path.dirname(os.path.abspath(__file__))
MASCOT = os.path.join(HERE, "..", "brand", "watermark_A.png")

# 쇼츠 화면은 아래쪽(제목·채널명)과 오른쪽(좋아요 버튼)이 가려짐 → 핵심은 y<1600, 가운데에
IMG_AREA = (20, 210, 1040, 900)
CROP_ASPECT = 4 / 3   # 가로로 긴 그림은 정답이 모두 들어가는 선에서 4:3으로 잘라 크게 보여줌


def smart_crop(A, B, ans, aspect=CROP_ASPECT, margin=30):
    w, h = A.size
    if aspect is None or w / h <= aspect:
        return A, B, ans
    cw = round(h * aspect)
    lo = max(a["x"] + a["r"] for a in ans) + margin - cw    # 왼쪽 끝 가능한 최소
    hi = min(a["x"] - a["r"] for a in ans) - margin          # 왼쪽 끝 가능한 최대
    if lo > hi:
        return A, B, ans                                     # 정답이 다 안 들어가면 자르지 않음
    x0 = int(min(max((w - cw) / 2, lo, 0), hi, w - cw))      # 가능하면 가운데 기준
    box = (x0, 0, x0 + cw, h)
    return A.crop(box), B.crop(box), [dict(a, x=a["x"] - x0) for a in ans]


def fit_box(img):
    x, y, w, h = IMG_AREA
    s = min(w / img.width, h / img.height)
    bw, bh = round(img.width * s), round(img.height * s)
    return (x + (w - bw) // 2, y + (h - bh) // 2, bw, bh)


def paste_img(fr, img, box, radius=24, border=10):
    x, y, w, h = box
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle((x - border, y - border, x + w + border, y + h + border), radius + 6, fill=INK)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius, fill=255)
    fr.paste(img.resize((w, h), Image.LANCZOS), (x, y), mask)


def frame(img, box, header, color, hy):
    fr = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle((30, hy - 55, W - 30, hy + 55), 55, fill=color)
    size = 60
    while d.textlength(header, font=F(size)) > W - 140:
        size -= 2
    d.text((W // 2, hy), header, font=F(size), fill="#fff", anchor="mm")
    paste_img(fr, img, box)
    return fr


def thumbnail(img, n):
    fr = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(fr)
    d.rectangle((0, 0, W, 620), fill=GREEN)
    d.ellipse((-200, 480, W + 200, 760), fill=GREEN)
    d.text((W // 2, 250), "두뇌 건강을 위한", font=F(92), fill="#ffe3a3", anchor="mm")
    d.text((W // 2, 420), "틀린그림 찾기", font=F(150), fill="#fff", anchor="mm",
           stroke_width=8, stroke_fill="#2c6b4e")
    s = min(1000 / img.width, 820 / img.height)
    box = ((W - round(img.width * s)) // 2, 780, round(img.width * s), round(img.height * s))
    paste_img(fr, img, box)
    by = box[1] + box[3] + 90
    d.rounded_rectangle((170, by - 70, W - 170, by + 70), 70, fill=RED)
    d.text((W // 2, by), f"달라진 곳 {n}곳, 찾아보세요!", font=F(64), fill="#fff", anchor="mm")
    if os.path.exists(MASCOT):
        m = Image.open(MASCOT).convert("RGBA").resize((260, 260), Image.LANCZOS)
        fr.paste(m, (W - 300, box[1] - 170), m)
    return fr


def hourglass(d, cx, cy, f):
    """모래시계. f = 남은 비율(1→0): 위 모래가 줄고 아래 모래가 쌓임."""
    hw, hh, neck = 46, 66, 7
    wood = "#a0693f"
    d.rounded_rectangle((cx - hw - 12, cy - hh - 16, cx + hw + 12, cy - hh), 6, fill=wood, outline=INK, width=4)
    d.rounded_rectangle((cx - hw - 12, cy + hh, cx + hw + 12, cy + hh + 16), 6, fill=wood, outline=INK, width=4)
    top = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + neck, cy), (cx - neck, cy)]
    bot = [(cx - neck, cy), (cx + neck, cy), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    d.polygon(top, fill="#e6f3fa"); d.polygon(bot, fill="#e6f3fa")
    sand = "#f2b84b"
    if f > 0:  # 위쪽: 목 부분부터 남은 만큼
        ys = cy - (hh - 6) * f
        wy = neck + (hw - neck) * (cy - ys) / hh
        d.polygon([(cx - wy, ys), (cx + wy, ys), (cx + neck, cy), (cx - neck, cy)], fill=sand)
        d.line((cx, cy, cx, cy + hh - 4), fill=sand, width=4)   # 떨어지는 모래
    hb = (hh - 8) * (1 - f)   # 아래쪽 쌓인 모래 (봉긋하게)
    if hb > 1:
        yb = cy + hh - hb
        wb = neck + (hw - neck) * (yb - cy) / hh
        d.polygon([(cx - hw, cy + hh), (cx + hw, cy + hh), (cx + wb, yb + hb * .35), (cx, yb), (cx - wb, yb + hb * .35)], fill=sand)
    d.line(top + [top[0]], fill=INK, width=5, joint="curve"); d.line(bot + [bot[0]], fill=INK, width=5, joint="curve")


def ring(d, remain, total, label, top):
    """그림 아래: 모래시계 + 남은 초 + 가로 막대."""
    col = RED if remain <= 5 else GREEN
    hourglass(d, 150, top + 90, remain / total)
    d.text((260, top + 45), label, font=F(52), fill=INK, anchor="lm")
    d.text((W - 90, top + 45), f"{max(1, math.ceil(remain))}초", font=F(64), fill=col, anchor="rm")
    x0, x1, y0 = 260, W - 90, top + 105
    d.rounded_rectangle((x0, y0, x1, y0 + 34), 17, fill="#eadfcc")
    if remain > 0:
        d.rounded_rectangle((x0, y0, x0 + max(34, (x1 - x0) * remain / total), y0 + 34), 17, fill=col)


def music(total):
    """84BPM 오르골풍: C-Am-F-G 아르페지오 + 부드러운 베이스."""
    beat = 60 / 84
    chords = [[261.6, 329.6, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7]]
    out = np.zeros(int(SR * (total + 2)))
    def put(at, sig):
        i = int(at * SR); j = min(len(out), i + len(sig)); out[i:j] += sig[: j - i]
    t, bar = 0.0, 0
    while t < total:
        c = chords[bar % 4]
        notes = [c[0] * 2, c[1] * 2, c[2] * 2, c[0] * 4, c[2] * 2, c[1] * 2, c[2] * 2, c[1] * 2]
        for k, f in enumerate(notes):
            put(t + k * beat / 2, tone([f, f * 2, f * 3], 1.2, .45, .16))
        put(t, tone([c[0] / 2, c[0]], beat * 4, 1.2, .22))
        t += beat * 4; bar += 1
    out = out[: int(SR * total)]
    fade = int(SR * 1.5)
    out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return out


def audio(path, total, intro, t1, t2, reveal, with_music=True):
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    chime = lambda: np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)])
    put(0.1, chime()); put(intro, chime()); put(intro + t1, chime())
    for start, dur in ((intro, t1), (intro + t1, t2)):
        for s in range(dur - 5, dur):
            put(start + s, tone([1200 if s < dur - 1 else 1600], .08, .03, .35))
    for i, f in enumerate([523, 659, 784]):
        put(intro + t1 + t2 + i * .12, tone([f, f * 2], .4, .2, .35))
    for r in reveal:
        put(r, np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .8, .35, .45)]))
    sfx_peak = np.abs(a).max()
    if with_music:
        m = music(total)
        a[: len(m)] += m / np.abs(m).max() * sfx_peak * 0.35   # 효과음보다 작게 깔기
    a = (a / np.abs(a).max() * 0.7 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.tobytes())


def render(folder, out, times=(15, 15, 10), intro=2, with_music=True, crop=True):
    A = Image.open(f"{folder}/base.png").convert("RGB")
    B = Image.open(f"{folder}/b.png").convert("RGB")
    ans = json.load(open(f"{folder}/answers.json"))
    if crop:
        A, B, ans = smart_crop(A, B, ans)
    n = len(ans)
    t1, t2, t3 = times
    total = intro + t1 + t2 + t3
    box = fit_box(A)
    # 머리띠 + 그림 + 타이머 묶음을 화면 세로 가운데에 (쇼츠 하단 자막 영역 고려해 살짝 위로)
    group_h = 110 + 40 + box[3] + 40 + 190
    top = max(30, (H - group_h) // 2 - 40)
    hy = top + 55
    box = (box[0], top + 150, box[2], box[3])
    sx, sy = box[2] / A.width, box[3] / A.height
    below = box[1] + box[3] + 40

    thumb = thumbnail(A, n)
    thumb.save(os.path.join(os.path.dirname(out), "thumbnail.png"))
    f1 = frame(A, box, "그림을 잘 기억해 두세요!", GREEN, hy)
    f2 = frame(B, box, f"무엇이 달라졌을까요? ({n}곳)", ORANGE, hy)
    f3 = frame(B, box, "정답 공개!", RED, hy)
    f3cta = frame(B, box, "몇 곳 찾으셨나요? 댓글 남겨주세요!", GREEN, hy)
    p3 = intro + t1 + t2
    reveal = [p3 + 0.6 + i * 1.5 for i in range(n)]
    cta_at = total - 4

    wav = out + ".wav"
    audio(wav, total, intro, t1, t2, reveal, with_music)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)

    for k in range(int(total * FPS)):
        t = k / FPS
        if t < intro:
            fr = thumb
        elif t < intro + t1:
            tt = t - intro
            fr = f1.copy(); ring(ImageDraw.Draw(fr), t1 - tt, t1, "1단계 · 기억하기", below)
            if tt < 0.4:
                fr = Image.blend(fr, thumb, 1 - tt / 0.4)
        elif t < p3:
            tt = t - intro - t1
            fr = f2.copy(); ring(ImageDraw.Draw(fr), t2 - tt, t2, "2단계 · 찾아보기", below)
            if tt < 0.5:  # 그림이 바뀌었다는 신호
                fr = Image.blend(fr, Image.new("RGB", (W, H), "#ffffff"), 1 - tt / 0.5)
        else:
            fr = (f3cta if t >= cta_at else f3).copy(); d = ImageDraw.Draw(fr)
            rows = n if n <= 3 else math.ceil(n / 2)
            for i, a in enumerate(ans):
                if t < reveal[i]:
                    continue
                pop = 1 + 0.5 * max(0.0, 1 - (t - reveal[i]) / 0.3)
                x = box[0] + a["x"] * sx; y = box[1] + a["y"] * sy
                r = max(a["r"] * sx, 40) * pop
                d.ellipse((x - r, y - r, x + r, y + r), outline=RED, width=11)
                bx, by = x + r * 0.72, y - r * 0.72
                d.ellipse((bx - 28, by - 28, bx + 28, by + 28), fill=RED)
                d.text((bx, by), str(i + 1), font=F(38), fill="#fff", anchor="mm")
                lx = 130 + (i // rows) * 470
                ly = below + 45 + (i % rows) * 85
                d.ellipse((lx, ly - 32, lx + 64, ly + 32), fill=RED)
                d.text((lx + 32, ly), str(i + 1), font=F(40), fill="#fff", anchor="mm")
                d.text((lx + 90, ly), a["label"], font=F(56), fill=INK, anchor="lm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("완료:", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    times = tuple(int(x) for x in args[args.index("--times") + 1].split(",")) if "--times" in args else (15, 15, 10)
    intro = float(args[args.index("--intro") + 1]) if "--intro" in args else 2
    render(args[0], args[1], times, intro, "--no-music" not in args, "--no-crop" not in args)
