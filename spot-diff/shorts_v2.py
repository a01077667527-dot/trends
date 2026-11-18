"""쇼츠 v2 – 시청 지속(끝까지 보기)에 맞춘 기억력 틀린그림.

바뀐 점 (v1 대비)
  - 0초부터 바로 문제 시작: 따로 있던 제목 화면 없이 그림 위에 '상위 1%' 도전 문구
  - 기억하기 10초(마지막 3·2·1 큰 숫자), 찾아보기 12초 → 전체 약 30초
  - 찾아보기 중간에 '힌트' 등장 → 넘기려던 사람을 붙잡음
  - 정답은 하나씩: 동그라미 안에서 원래 그림↔바뀐 그림이 깜빡여 '아하!' 순간을 보여줌, 1/3·2/3·3/3 진행 표시
  - 마지막 2.5초: 댓글 유도 + 구독 띠 (별도 구독 화면 없이 짧게)

사용법: python3 shorts_v2.py out/space out/space/shorts_v2.mp4 [--times 10,12] [--bgm musicbox|pluck]
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw
from shorts import (W, H, FPS, BG, INK, GREEN, ORANGE, RED, F, fit_box, smart_crop, frame,
                    thumbnail, hourglass, music, tone, SR)


def region_word(x, y, w, h):
    s = "왼쪽" if x < w / 3 else ("오른쪽" if x > w * 2 / 3 else "")
    v = "위" if y < h / 3 else ("아래" if y > h * 2 / 3 else "")
    if s and v:
        return f"{s} {v}"
    return s or (v + "쪽" if v else "가운데")


def josa(word):  # 받침 있으면 '을', 없으면 '를'
    return "을" if (ord(word[-1]) - 0xAC00) % 28 else "를"


def bar(d, remain, total, label, top):
    col = RED if remain <= 3 else GREEN
    hourglass(d, 150, top + 90, remain / total)
    d.text((260, top + 45), label, font=F(52), fill=INK, anchor="lm")
    d.text((W - 90, top + 45), f"{max(1, math.ceil(remain))}초", font=F(64), fill=col, anchor="rm")
    d.rounded_rectangle((260, top + 105, W - 90, top + 139), 17, fill="#eadfcc")
    if remain > 0:
        d.rounded_rectangle((260, top + 105, 260 + max(34, (W - 350) * remain / total), top + 139), 17, fill=col)


def header(d, hy, text, color):
    d.rounded_rectangle((30, hy - 55, W - 30, hy + 55), 55, fill=color)
    size = 60
    while d.textlength(text, font=F(size)) > W - 140:
        size -= 2
    d.text((W // 2, hy), text, font=F(size), fill="#fff", anchor="mm")


def big_number(fr, box, n, age):
    """그림 위 가운데에 커다란 3·2·1 (반투명, 살짝 커졌다 작아짐)."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    s = 1.25 - 0.25 * min(1, age / 0.3)
    cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
    r = 150 * s
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(0, 0, 0, 110))
    d.text((cx, cy), str(n), font=F(int(220 * s)), fill=(255, 255, 255, 235), anchor="mm")
    fr.paste(ov, (0, 0), ov)


def render(folder, out, times=(10, 12), bgm="musicbox"):
    A = Image.open(f"{folder}/base.png").convert("RGB")
    B = Image.open(f"{folder}/b.png").convert("RGB")
    ans = json.load(open(f"{folder}/answers.json"))
    A, B, ans = smart_crop(A, B, ans)
    n = len(ans)
    t1, t2 = times
    box = fit_box(A)
    group_h = 110 + 40 + box[3] + 40 + 190
    top = max(30, (H - group_h) // 2 - 40)
    hy = top + 55
    box = (box[0], top + 150, box[2], box[3])
    sx, sy = box[2] / A.width, box[3] / A.height
    below = box[1] + box[3] + 40
    Ar, Br = A.resize(box[2:], Image.LANCZOS), B.resize(box[2:], Image.LANCZOS)

    thumbnail(A, n).save(os.path.join(os.path.dirname(out), "thumbnail.png"))
    fA = frame(A, box, f"{t1}초 동안 잘 기억하세요!", GREEN, hy)
    fB = frame(B, box, f"달라진 곳 {n}곳을 찾아보세요!", ORANGE, hy)
    hard = ans[-1]  # 마지막(가장 늦게 공개) 정답 위치로 힌트
    rw = region_word(hard['x'], hard['y'], A.width, A.height)
    hint_text = f"힌트! {rw}{josa(rw)} 잘 보세요"
    hint_at = t1 + t2 * 0.5
    p3 = t1 + t2
    step = 1.8
    reveal = [p3 + 0.5 + i * step for i in range(n)]
    end_at = reveal[-1] + step
    total = end_at + 2.5

    # ---- 소리 ----
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    chime = lambda: np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)])
    put(0.05, chime()); put(t1, chime())
    for s in (t1 - 3, t1 - 2, t1 - 1):
        put(s, tone([880], .25, .12, .5))                       # 3·2·1 삑
    for s in range(t1 + t2 - 3, t1 + t2):
        put(s, tone([1200 if s < t1 + t2 - 1 else 1600], .08, .03, .35))
    put(hint_at, np.concatenate([tone([1568, 3136], .12, .06, .35), tone([2093, 4186], .3, .15, .35)]))
    for i, f in enumerate([523, 659, 784]):
        put(p3 + i * .12, tone([f, f * 2], .4, .2, .35))
    for r in reveal:
        put(r, np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .8, .35, .45)]))
    put(end_at, np.concatenate([tone([784, 1568], .15, .1, .4), tone([1047, 2094], .2, .12, .4), tone([1568, 3136], .6, .3, .4)]))
    m = music(total, bgm); a[: len(m)] += m / np.abs(m).max() * np.abs(a).max() * .3
    wav = out + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a / np.abs(a).max() * .7 * 32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                           "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    def circle_xy(a_):
        return box[0] + a_["x"] * sx, box[1] + a_["y"] * sy, max(a_["r"] * sx, 40)

    for k in range(int(total * FPS)):
        t = k / FPS
        if t < t1:                                    # 기억하기 (0초부터 바로)
            fr = fA.copy(); d = ImageDraw.Draw(fr)
            bar(d, t1 - t, t1, "1단계 · 기억하기", below)
            if t < 2.2:                               # 도전 문구 (훅)
                pop = 1 + 0.15 * max(0, 1 - t / 0.25)
                cy = box[1] + box[3] - 90
                bw, bh = 760 * pop, 120 * pop
                d.rounded_rectangle((W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2), bh / 2, fill=RED,
                                    outline="#fff", width=6)
                d.text((W / 2, cy), f"{n}곳 다 찾으면 상위 1%!", font=F(int(62 * pop)), fill="#fff", anchor="mm")
            left = t1 - t
            if left <= 3:
                big_number(fr, box, math.ceil(left), math.ceil(left) - left)
        elif t < p3:                                  # 찾아보기 (+ 힌트)
            tt = t - t1
            fr = fB.copy(); d = ImageDraw.Draw(fr)
            bar(d, t2 - tt, t2, "2단계 · 찾아보기", below)
            if t >= hint_at:
                header(d, hy, hint_text, "#7b4fd6")
            if tt < 0.5:
                fr = Image.blend(fr, Image.new("RGB", (W, H), "#ffffff"), 1 - tt / 0.5)
        else:                                         # 정답 하나씩 + 깜빡 비교
            shown = sum(t >= r for r in reveal)
            fr = Image.new("RGB", (W, H), BG); fr.paste(fB, (0, 0))
            img = Br.copy()
            for i in range(shown):
                age = t - reveal[i]
                if age < 1.2 and int(age / 0.2) % 2 == 0:   # 원 안을 원래 그림으로 깜빡
                    x, y, r = circle_xy(ans[i])
                    mask = Image.new("L", img.size, 0)
                    ImageDraw.Draw(mask).ellipse((x - box[0] - r, y - box[1] - r, x - box[0] + r, y - box[1] + r), fill=255)
                    img.paste(Ar, (0, 0), mask)
            m_ = Image.new("L", img.size, 0); ImageDraw.Draw(m_).rounded_rectangle((0, 0, *img.size), 24, fill=255)
            fr.paste(img, box[:2], m_)
            d = ImageDraw.Draw(fr)
            if t < end_at:
                header(d, hy, f"정답 {shown}/{n}" if shown else "정답 공개!", RED)
            else:
                header(d, hy, "몇 곳 찾으셨나요? 댓글로 알려주세요!", GREEN)
            for i in range(shown):
                age = t - reveal[i]
                x, y, r = circle_xy(ans[i]); r *= 1 + 0.5 * max(0.0, 1 - age / 0.3)
                d.ellipse((x - r, y - r, x + r, y + r), outline=RED, width=11)
                bx, by = x + r * 0.72, y - r * 0.72
                d.ellipse((bx - 28, by - 28, bx + 28, by + 28), fill=RED)
                d.text((bx, by), str(i + 1), font=F(38), fill="#fff", anchor="mm")
                ly = below + 45 + i * 85
                d.ellipse((130, ly - 32, 194, ly + 32), fill=RED)
                d.text((162, ly), str(i + 1), font=F(40), fill="#fff", anchor="mm")
                d.text((220, ly), ans[i]["label"], font=F(56), fill=INK, anchor="lm")
            if t >= end_at:                           # 구독 띠
                yb = below + 45 + n * 85 + 30
                s = 1 + 0.05 * math.sin((t - end_at) * 2 * math.pi * 1.6)
                bw, bh = 820 * s, 110 * s
                d.rounded_rectangle((W / 2 - bw / 2, yb, W / 2 + bw / 2, yb + bh), bh / 2, fill=RED)
                d.text((W / 2, yb + bh / 2), "매일 새 문제! 구독하고 함께 해요", font=F(int(50 * s)), fill="#fff", anchor="mm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print(f"완료: {out} ({total:.1f}초)")


if __name__ == "__main__":
    a = sys.argv[1:]
    times = tuple(int(x) for x in a[a.index("--times") + 1].split(",")) if "--times" in a else (10, 12)
    bgm = a[a.index("--bgm") + 1] if "--bgm" in a else "musicbox"
    render(a[0], a[1], times, bgm)
