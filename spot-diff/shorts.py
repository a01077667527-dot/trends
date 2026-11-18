"""쇼츠용(1080x1920) 기억력 틀린그림 영상.

구성: 인트로/썸네일 2초 → 기억하기 15초 → 찾아보기 15초 → 정답 10초
배경음악: 직접 합성한 잔잔한 오르골풍 음악(저작권 걱정 없음) + 효과음

사용법:
  python3 shorts.py out/camping2 out/camping2/shorts.mp4
  옵션: --times 15,15,10  --intro 2  --no-music
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
IMG_AREA = (40, 250, 1000, 760)
RING = (540, 1300, 165)


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


def frame(img, box, header, color):
    fr = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle((30, 70, W - 30, 200), 60, fill=color)
    d.text((W // 2, 135), header, font=F(64), fill="#fff", anchor="mm")
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
    s = 960 / img.width
    box = (60, 820, 960, round(img.height * s))
    paste_img(fr, img, box)
    by = box[1] + box[3] + 90
    d.rounded_rectangle((170, by - 70, W - 170, by + 70), 70, fill=RED)
    d.text((W // 2, by), f"달라진 곳 {n}곳, 찾아보세요!", font=F(64), fill="#fff", anchor="mm")
    if os.path.exists(MASCOT):
        m = Image.open(MASCOT).convert("RGBA").resize((260, 260), Image.LANCZOS)
        fr.paste(m, (W - 300, box[1] - 170), m)
    return fr


def ring(d, remain, total, label):
    cx, cy, r = RING
    d.text((cx, cy - r - 75), label, font=F(66), fill=INK, anchor="mm")
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline="#eadfcc", width=30)
    col = RED if remain <= 5 else GREEN
    if remain > 0:
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * remain / total, fill=col, width=30)
    d.text((cx, cy - 8), str(max(1, math.ceil(remain))), font=F(170), fill=col, anchor="mm")


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


def render(folder, out, times=(15, 15, 10), intro=2, with_music=True):
    A = Image.open(f"{folder}/base.png").convert("RGB")
    B = Image.open(f"{folder}/b.png").convert("RGB")
    ans = json.load(open(f"{folder}/answers.json"))
    n = len(ans)
    t1, t2, t3 = times
    total = intro + t1 + t2 + t3
    box = fit_box(A)
    sx, sy = box[2] / A.width, box[3] / A.height

    thumb = thumbnail(A, n)
    thumb.save(os.path.join(os.path.dirname(out), "thumbnail.png"))
    f1 = frame(A, box, "그림을 잘 기억해 두세요!", GREEN)
    f2 = frame(B, box, f"무엇이 달라졌을까요? ({n}곳)", ORANGE)
    f3 = frame(B, box, "정답 공개!", RED)
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
            fr = f1.copy(); ring(ImageDraw.Draw(fr), t1 - tt, t1, "1단계 · 기억하기")
            if tt < 0.4:
                fr = Image.blend(fr, thumb, 1 - tt / 0.4)
        elif t < p3:
            tt = t - intro - t1
            fr = f2.copy(); ring(ImageDraw.Draw(fr), t2 - tt, t2, "2단계 · 찾아보기")
            if tt < 0.5:  # 그림이 바뀌었다는 신호
                fr = Image.blend(fr, Image.new("RGB", (W, H), "#ffffff"), 1 - tt / 0.5)
        else:
            fr = f3.copy(); d = ImageDraw.Draw(fr)
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
                ly = box[1] + box[3] + 110 + i * 100
                d.ellipse((150, ly - 34, 218, ly + 34), fill=RED)
                d.text((184, ly), str(i + 1), font=F(42), fill="#fff", anchor="mm")
                d.text((250, ly), a["label"], font=F(62), fill=INK, anchor="lm")
            if t >= cta_at:
                d.rounded_rectangle((120, 1420, W - 120, 1590), 40, fill=GREEN)
                d.text((W // 2, 1475), f"{n}곳 다 찾으셨나요?", font=F(54), fill="#fff", anchor="mm")
                d.text((W // 2, 1543), "댓글로 알려주세요!", font=F(54), fill="#ffe3a3", anchor="mm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("완료:", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    times = tuple(int(x) for x in args[args.index("--times") + 1].split(",")) if "--times" in args else (15, 15, 10)
    intro = float(args[args.index("--intro") + 1]) if "--intro" in args else 2
    render(args[0], args[1], times, intro, "--no-music" not in args)
