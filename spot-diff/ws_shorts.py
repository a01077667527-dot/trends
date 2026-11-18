"""숨은 단어 찾기 쇼츠 영상 (1080x1920).

구성: 인트로(썸네일) 2초 → 찾기 20초(모래시계) → 정답이 하나씩 색칠되며 '딩동' → 댓글 유도
사용법:
  python3 ws_shorts.py 과일 사과,바나나,포도,수박,딸기,참외 out/ws_fruit [--size 6] [--seed 1] [--time 20]
  --bgm musicbox|pluck (배경음악 종류)
결과: out/.../shorts.mp4, thumbnail.png, puzzle.json
"""
import json, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw
from wordsearch import build, F, W, H, INK, RED, GREEN, ORANGE, COLORS
from shorts import hourglass, music, tone, SR, FPS
import math
import outro

HERE = os.path.dirname(os.path.abspath(__file__))
MASCOT = os.path.join(HERE, "..", "brand", "v2", "logo_A.png")
TOP = 470          # 글자판 위치
BG = "#fff8ec"


def board(grid, shown, cell_hi=None):
    n = len(grid)
    cell = min(150, 980 // n)
    x0 = (W - cell * n) // 2
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((x0, TOP, x0 + cell * n, TOP + cell * n), fill="#ffffff")
    for k, p in shown:
        (r1, c1), (r2, c2) = p["cells"][0], p["cells"][-1]
        pad = 14
        d.rounded_rectangle((x0 + c1 * cell + pad, TOP + r1 * cell + pad,
                             x0 + (c2 + 1) * cell - pad, TOP + (r2 + 1) * cell - pad), cell // 2, fill=COLORS[k % len(COLORS)])
    for r in range(n):
        for c in range(n):
            x, y = x0 + c * cell, TOP + r * cell
            d.rectangle((x, y, x + cell, y + cell), outline=ORANGE, width=6)
            d.text((x + cell / 2, y + cell / 2 + 4), grid[r][c], font=F(int(cell * .58)), fill=INK, anchor="mm")
    d.rectangle((x0 - 4, TOP - 4, x0 + cell * n + 4, TOP + cell * n + 4), outline=ORANGE, width=12)
    return im, d, TOP + cell * n


def titles(d, theme, k, line2, color):
    d.text((W // 2, 170), f"숨은 {theme} {k}개", font=F(104), fill=INK, anchor="mm")
    d.text((W // 2, 300), line2, font=F(110), fill=color, anchor="mm")
    d.text((W // 2, 400), "가로(→) 세로(↓)로 숨어 있어요", font=F(44), fill="#868e96", anchor="mm")


def timer(d, remain, total, top):
    col = RED if remain <= 5 else GREEN
    hourglass(d, 150, top + 90, remain / total)
    d.text((260, top + 45), "찾아보기", font=F(52), fill=INK, anchor="lm")
    d.text((W - 90, top + 45), f"{max(1, math.ceil(remain))}초", font=F(64), fill=col, anchor="rm")
    d.rounded_rectangle((260, top + 105, W - 90, top + 139), 17, fill="#eadfcc")
    if remain > 0:
        d.rounded_rectangle((260, top + 105, 260 + max(34, (W - 350) * remain / total), top + 139), 17, fill=col)


def chips(d, words_shown, y0):
    x, y = 90, y0
    for k, w in words_shown:
        tw = d.textlength(w, font=F(56)) + 60
        if x + tw > W - 90:
            x = 90; y += 100
        d.rounded_rectangle((x, y - 40, x + tw, y + 40), 40, fill=COLORS[k % len(COLORS)])
        d.text((x + tw / 2, y), w, font=F(56), fill=INK, anchor="mm")
        x += tw + 24


def render(theme, words, out_dir, n=6, seed=1, find=20, intro=2, bgm="musicbox"):
    os.makedirs(out_dir, exist_ok=True)
    grid, placed = build(words, n, seed)
    k = len(placed)
    json.dump({"theme": theme, "grid": grid, "answers": placed}, open(f"{out_dir}/puzzle.json", "w"), ensure_ascii=False, indent=1)

    # 썸네일/인트로
    thumb, d, bottom = board(grid, [])
    titles(d, theme, k, "찾아보세요!", RED)
    d.rounded_rectangle((150, bottom + 50, W - 150, bottom + 170), 60, fill=GREEN)
    d.text((W // 2, bottom + 110), "두뇌 건강 강화 프로젝트", font=F(54), fill="#fff", anchor="mm")
    if os.path.exists(MASCOT):
        m = Image.open(MASCOT).convert("RGB").resize((190, 190), Image.LANCZOS)
        mask = Image.new("L", (190, 190), 0); ImageDraw.Draw(mask).ellipse((0, 0, 190, 190), fill=255)
        thumb.paste(m, (W - 215, 20), mask)
    thumb.save(f"{out_dir}/thumbnail.png")

    base, d, bottom = board(grid, [])
    titles(d, theme, k, "찾아보세요!", RED)
    a_start = intro + find
    reveal = [a_start + 0.8 + i * 1.2 for i in range(k)]
    ans_end = reveal[-1] + 4.5
    total = ans_end + outro.OUTRO_SEC
    cta_at = ans_end - 3.5

    # 소리
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    chime = lambda: np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)])
    put(0.1, chime()); put(intro, chime()); put(ans_end, outro.sound(tone))
    for s in range(find - 5, find):
        put(intro + s, tone([1200 if s < find - 1 else 1600], .08, .03, .35))
    for i, f in enumerate([523, 659, 784]):
        put(a_start + i * .12, tone([f, f * 2], .4, .2, .35))
    for r in reveal:
        put(r, np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .8, .35, .45)]))
    m = music(total, bgm); a[: len(m)] += m / np.abs(m).max() * np.abs(a).max() * .35
    wav = f"{out_dir}/_a.wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a / np.abs(a).max() * .7 * 32767).astype(np.int16).tobytes())

    out = f"{out_dir}/shorts.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    cache = {}
    for f in range(int(total * FPS)):
        t = f / FPS
        if t >= ans_end:
            fr = outro.frame(t - ans_end)
        elif t < intro:
            fr = thumb
        elif t < a_start:
            fr = base.copy(); timer(ImageDraw.Draw(fr), a_start - t, find, bottom + 40)
            if t - intro < .4:
                fr = Image.blend(fr, thumb, 1 - (t - intro) / .4)
        else:
            shown = sum(t >= r for r in reveal)
            cta = t >= cta_at
            key = (shown, cta)
            if key not in cache:
                im, d, _ = board(grid, [(i, placed[i]) for i in range(shown)])
                titles(d, theme, k, "몇 개 찾으셨나요?" if cta else "정답 공개!", ORANGE if cta else GREEN)
                chips(d, [(i, placed[i]["word"]) for i in range(shown)], bottom + 80)
                if cta:
                    d.rectangle((0, 365, W, 440), fill=BG)   # 안내문 자리를 댓글 유도로 교체
                    d.text((W // 2, 400), "댓글로 알려주세요! 😊".replace(" 😊", ""), font=F(54), fill=GREEN, anchor="mm")
                cache[key] = im
            fr = cache[key]
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("완료:", out, [p["word"] for p in placed], f"{total:.1f}초")


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    render(a[0], a[1].split(","), a[2], opt("--size", 6), opt("--seed", 1), opt("--time", 20), bgm=opt("--bgm", "musicbox"))
