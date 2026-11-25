"""쇼츠 – 위아래 두 그림 나란히, 바로 찾기 (레퍼런스 구조).

검은 바탕 / 위 제목 / 왼쪽 세로 글씨 / 위아래 그림 / 오른쪽 위 원형 타이머 / 아래 '정답은 댓글'
정답은 영상에 넣지 않고 고정 댓글로 (댓글 유도). --reveal 을 주면 마지막에 동그라미 3초.

사용법: python3 shorts_stack.py out/L1 out/L1/stack.mp4 [--time 30] [--style 0] [--reveal] [--bgm pluck]
결과: stack.mp4, stack_answer.png(고정 댓글용 정답 이미지), stack_comment.txt
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shorts import music, tone, SR

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
F = lambda s: ImageFont.truetype(FONT, s)
YEL, GRN, PINK, WHITE, RED, LIME = "#ffd43b", "#51cf66", "#f06595", "#ffffff", "#ff3b3b", "#94d82d"

# (위 제목 [(글자, 색)...], 왼쪽 세로 [(글자, 색)...], 아래 안내)
STYLES = [
    ([("눈썰미", PINK), (" 챌린지", YEL)], [("숨", YEL), ("은", YEL), ("차", GRN), ("이", GRN), ("3", WHITE), ("곳", WHITE)], "정답은 댓글에 적어주세요"),
    ([("매의 눈", YEL), (" 테스트", PINK)], [("어", WHITE), ("디", WHITE), ("가", WHITE), ("달", YEL), ("라", YEL), ("졌", YEL), ("을", GRN), ("까", GRN), ("?", GRN)], "정답은 댓글에 적어주세요"),
    ([("두뇌", GRN), (" 집중 ", WHITE), ("타임", YEL)], [("3", PINK), ("곳", PINK), ("만", WHITE), ("찾", YEL), ("으", YEL), ("면", YEL), ("합", GRN), ("격", GRN)], "정답은 댓글에 적어주세요"),
    ([("오늘의", YEL), (" 틀린그림", PINK)], [("다", WHITE), ("른", WHITE), ("곳", YEL), ("세", YEL), ("군", GRN), ("데", GRN)], "정답은 댓글에 적어주세요"),
    ([("추억", YEL), (" 다른그림 찾기", WHITE)], [("그", YEL), ("때", YEL), ("그", WHITE), ("시", WHITE), ("절", WHITE), ("3", PINK), ("곳", PINK)], "정답은 댓글에 적어주세요"),
    ([("추억", YEL), (" 다른그림 찾기", WHITE)], [("그", YEL), ("때", YEL), ("그", WHITE), ("시", WHITE), ("절", WHITE), ("5", PINK), ("곳", PINK)], "정답은 댓글에 적어주세요"),
]


def text_runs(d, cx, y, runs, size, stroke=6):
    total = sum(d.textlength(t, font=F(size)) for t, _ in runs)
    x = cx - total / 2
    for t, c in runs:
        d.text((x, y), t, font=F(size), fill=c, anchor="lm", stroke_width=stroke, stroke_fill="#000")
        x += d.textlength(t, font=F(size))


def render(folder, out, find=30, style=0, reveal=False, bgm="pluck", ai_note=False):
    A = Image.open(f"{folder}/base.png").convert("RGB")
    B = Image.open(f"{folder}/b.png").convert("RGB")
    ans = json.load(open(f"{folder}/answers.json"))
    title, vert, note = STYLES[style % len(STYLES)]
    note = note.replace(" 👇", "")

    # 레이아웃: 왼쪽 세로 글씨 칸 + 오른쪽 그림 두 장
    col = 210
    iw = W - col - 40
    ih = round(iw * A.height / A.width)
    gap = 14
    top = 330
    boxes = [(col + 10, top, iw, ih), (col + 10, top + ih + gap, iw, ih)]
    bottom = top + 2 * ih + gap

    base = Image.new("RGB", (W, H), "#000")
    d = ImageDraw.Draw(base)
    text_runs(d, W / 2 - 40, 225, title, 92)
    if ai_note:
        d.text((W - 30, H - 30), "AI로 재현한 그 시절 풍경", font=F(30), fill="#888888", anchor="rd")
    d.rectangle((col, top - 10, col + iw + 20, bottom + 10), fill=LIME)
    for (x, y, w, h), im in zip(boxes, (A, B)):
        base.paste(im.resize((w, h), Image.LANCZOS), (x, y))
    # 세로 글씨 (그림 높이에 맞춰 크기 조절)
    size = min(150, int((bottom - top) / len(vert) * 0.92))
    step = (bottom - top) / len(vert)
    for i, (ch, c) in enumerate(vert):
        d.text((col / 2, top + step * (i + .5)), ch, font=F(size), fill=c, anchor="mm", stroke_width=5, stroke_fill="#000")
    d.text((col + 10 + iw - 10, bottom + 55), f"<{note}>", font=F(40), fill=YEL, anchor="rm")

    rev = 3.0 if reveal else 0.0
    end = 2.5
    total = find + rev + end
    # 소리
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    put(0.05, np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)]))
    for s in range(find - 5, find):
        put(s, tone([1200 if s < find - 1 else 1600], .08, .03, .35))
    if reveal:
        for k in range(len(ans)):
            put(find + .3 + k * .8, np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .6, .3, .45)]))
    put(find + rev, np.concatenate([tone([784, 1568], .15, .1, .4), tone([1047, 2094], .2, .12, .4), tone([1568, 3136], .6, .3, .4)]))
    m = music(total, bgm); a[: len(m)] += m / np.abs(m).max() * np.abs(a).max() * .3
    wav = out + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a / np.abs(a).max() * .7 * 32767).astype(np.int16).tobytes())

    def circles(img, k_shown, t_rel=None):
        dd = ImageDraw.Draw(img)
        s = iw / A.width
        for k, x in enumerate(ans[:k_shown]):
            pop = 1 + .4 * max(0, 1 - (t_rel - k * .8 - .3) / .25) if t_rel is not None else 1
            for bx in boxes:
                cx, cy, r = bx[0] + x["x"] * s, bx[1] + x["y"] * s, max(x["r"] * s, 34) * pop
                dd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=RED, width=9)

    # 고정 댓글용 정답 이미지
    ansimg = base.copy(); circles(ansimg, len(ans))
    ansimg.crop((col, top - 10, col + iw + 20, bottom + 10)).save(os.path.splitext(out)[0] + "_answer.png")
    open(os.path.splitext(out)[0] + "_comment.txt", "w").write(
        "📌 찾으신 곳을 댓글에 적어주세요! 😊\n예) ○○ 색이 달라요, ○○이 없어졌어요\n\n"
        "[참고: 실제 정답 – 나중에 답글로 공개할 때 쓰세요]\n" +
        "\n".join(f"{i+1}. {x['label']}" for i, x in enumerate(ans)) + "\n")

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    tcx, tcy, tr = W - 95, 215, 70
    for f in range(int(total * FPS)):
        t = f / FPS
        fr = base.copy(); d = ImageDraw.Draw(fr)
        remain = max(0.0, find - t)
        colr = RED if remain <= 5 else WHITE
        d.ellipse((tcx - tr, tcy - tr, tcx + tr, tcy + tr), fill="#000", outline="#444", width=10)
        if remain > 0:
            d.arc((tcx - tr, tcy - tr, tcx + tr, tcy + tr), -90, -90 + 360 * remain / find, fill=colr, width=10)
        d.text((tcx, tcy), str(math.ceil(remain)), font=F(74), fill=colr, anchor="mm")
        if t >= find and reveal:
            circles(fr, min(len(ans), int((t - find - .3) / .8) + 1) if t - find >= .3 else 0, t - find)
        if t >= find + rev:   # 마무리: 댓글 유도 띠
            yb = bottom + 25
            d.rectangle((0, bottom + 12, W, bottom + 100), fill="#000")   # 아래 안내 글씨 지우고
            d.rounded_rectangle((90, yb, W - 90, yb + 150), 75, fill=RED)
            d.text((W / 2, yb + 75), "정답은 댓글에 적어주세요!", font=F(50), fill="#fff", anchor="mm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("완료:", out, f"{total:.1f}초")


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, dft: type(dft)(a[a.index(k) + 1]) if k in a else dft
    render(a[0], a[1], opt("--time", 30), opt("--style", 0), "--reveal" in a, opt("--bgm", "pluck"), "--ai" in a)
