"""몸풀기 '기억력 틀린그림' 영상 만들기 (1920x1080, TV 시청용).

구성 (기본값):
  1단계 0~15초  : 원본 그림 → "잘 기억해 두세요"
  2단계 15~30초 : 바뀐 그림 → "달라진 곳을 찾아보세요"
  3단계 30~40초 : 정답 동그라미가 하나씩 '딩동'과 함께 등장

입력 폴더에는 nanobanana.py 결과와 같은 구조가 있어야 함:
  base.png (원본), b.png (바뀐 그림), answers.json ([{label,x,y,r}], 이미지 픽셀 좌표)

사용법:
  python3 video.py out/camp out/camp/warmup.mp4
  python3 video.py out/camp out.mp4 --times 15,15,10 --title "오늘의 몸풀기"
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SR = 1920, 1080, 30, 44100
BG, INK, ACCENT, RED, GREEN = "#fff3dc", "#3a2a2a", "#3f8f6a", "#e53935", "#3f8f6a"
FONT_PATHS = ["/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]
FONT = next(p for p in FONT_PATHS if os.path.exists(p))
F = lambda s: ImageFont.truetype(FONT, s)

IMG_BOX = (60, 150, 1200, 900)   # x, y, w, h
PANEL_X = 1590                    # 오른쪽 패널 가운데


# ---------- 그림 ----------
def base_frame(img, header, header_color):
    fr = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle((40, 20, W - 40, 125), 50, fill=header_color)
    d.text((W // 2, 73), header, font=F(62), fill="#fff", anchor="mm")
    x, y, w, h = IMG_BOX
    d.rounded_rectangle((x - 10, y - 10, x + w + 10, y + h + 10), 30, fill=INK)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 22, fill=255)
    fr.paste(img.resize((w, h), Image.LANCZOS), (x, y), mask)
    return fr


def ring(d, remain, total, step_label, step_name):
    d.text((PANEL_X, 215), step_label, font=F(50), fill="#8a7a6a", anchor="mm")
    d.text((PANEL_X, 295), step_name, font=F(76), fill=INK, anchor="mm")
    cx, cy, r, t = PANEL_X, 600, 200, 34
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline="#eadfcc", width=t)
    frac = max(0.0, remain / total)
    col = RED if remain <= 5 else ACCENT
    if frac > 0:
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * frac, fill=col, width=t)
    d.text((cx, cy - 10), str(max(1, math.ceil(remain))), font=F(200), fill=col, anchor="mm")
    d.text((cx, cy + 290), "초", font=F(44), fill="#8a7a6a", anchor="mm")


def render(folder, out, times=(15, 15, 10), title=None):
    A = Image.open(f"{folder}/base.png").convert("RGB")
    B = Image.open(f"{folder}/b.png").convert("RGB")
    ans = json.load(open(f"{folder}/answers.json"))
    n = len(ans)
    t1, t2, t3 = times
    total = t1 + t2 + t3
    sx = IMG_BOX[2] / A.width; sy = IMG_BOX[3] / A.height

    f1 = base_frame(A, title or "그림을 잘 기억해 두세요!", ACCENT)
    f2 = base_frame(B, f"무엇이 달라졌을까요? ({n}곳)", "#e08a2e")
    f3 = base_frame(B, "정답 공개!", RED)
    # 정답 등장 시각: 3단계 시작 0.6초 뒤부터 1.5초 간격
    reveal = [t1 + t2 + 0.6 + i * 1.5 for i in range(n)]
    cta_at = total - 4

    write_audio(out + ".wav", total, t1, t2, reveal)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", out + ".wav",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)

    for k in range(int(total * FPS)):
        t = k / FPS
        if t < t1:
            fr = f1.copy(); d = ImageDraw.Draw(fr)
            ring(d, t1 - t, t1, "1단계", "기억하기")
        elif t < t1 + t2:
            tt = t - t1
            fr = f2.copy(); d = ImageDraw.Draw(fr)
            ring(d, t2 - tt, t2, "2단계", "찾아보기")
            if tt < 0.5:  # 그림이 바뀌었다는 신호: 흰 번쩍임
                fr = Image.blend(fr, Image.new("RGB", (W, H), "#ffffff"), 1 - tt / 0.5)
        else:
            fr = f3.copy(); d = ImageDraw.Draw(fr)
            d.text((PANEL_X, 230), "정답", font=F(84), fill=RED, anchor="mm")
            for i, a in enumerate(ans):
                if t < reveal[i]:
                    continue
                age = t - reveal[i]
                pop = 1 + 0.5 * max(0.0, 1 - age / 0.3)          # 커졌다가 제자리로
                x = IMG_BOX[0] + a["x"] * sx; y = IMG_BOX[1] + a["y"] * sy
                r = max(a["r"] * sx, 45) * pop
                d.ellipse((x - r, y - r, x + r, y + r), outline=RED, width=12)
                bx, by = x + r * 0.72, y - r * 0.72            # 번호 배지
                d.ellipse((bx - 30, by - 30, bx + 30, by + 30), fill=RED)
                d.text((bx, by), str(i + 1), font=F(40), fill="#fff", anchor="mm")
                ly = 370 + i * 105
                d.ellipse((PANEL_X - 250, ly - 34, PANEL_X - 182, ly + 34), fill=RED)
                d.text((PANEL_X - 216, ly), str(i + 1), font=F(42), fill="#fff", anchor="mm")
                d.text((PANEL_X - 160, ly), a["label"], font=F(56), fill=INK, anchor="lm")
            if t >= cta_at:
                d.rounded_rectangle((PANEL_X - 280, 860, PANEL_X + 280, 1020), 30, fill=ACCENT)
                d.text((PANEL_X, 910), f"{n}곳 다 찾으셨나요?", font=F(46), fill="#fff", anchor="mm")
                d.text((PANEL_X, 972), "댓글로 알려주세요!", font=F(46), fill="#ffe3a3", anchor="mm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(out + ".wav")
    print("완료:", out)


# ---------- 소리 (직접 합성, 저작권 걱정 없음) ----------
def tone(freqs, dur, decay, vol=0.5):
    t = np.arange(int(SR * dur)) / SR
    s = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate(freqs))
    return vol * s * np.exp(-t / decay)


def write_audio(path, total, t1, t2, reveal):
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); a[i:i + len(sig)] += sig[: len(a) - i]
    chime = lambda: np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)])
    put(0, chime()); put(t1, chime())
    for start, dur in ((0, t1), (t1, t2)):
        for s in range(dur - 5, dur):                     # 마지막 5초 째깍
            put(start + s, tone([1200 if s < dur - 1 else 1600], .08, .03, .35))
    for i, f in enumerate([523, 659, 784]):              # 정답 공개 팡파르
        put(t1 + t2 + i * .12, tone([f, f * 2], .4, .2, .35))
    for r in reveal:                                      # 딩동
        put(r, np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .8, .35, .45)]))
    a = (a / max(1e-9, np.abs(a).max()) * 0.6 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.tobytes())


if __name__ == "__main__":
    args = sys.argv[1:]
    times = (15, 15, 10); title = None
    if "--times" in args:
        times = tuple(int(x) for x in args[args.index("--times") + 1].split(","))
    if "--title" in args:
        title = args[args.index("--title") + 1]
    render(args[0], args[1], times, title)
