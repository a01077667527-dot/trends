"""내 수익률 찾기 – 5×5 수익률 카드 중 딱 하나만 플러스 (쇼츠 1080x1920).

카드 숫자는 실시간 시세처럼 조금씩 바뀌고, 하나만 플러스.
사용법:
  python3 stock_grid.py out/stock/stock_a.mp4 [--minus red|blue] [--hard] [--seed 3] [--time 15]
  --minus red  : 마이너스 빨강, 플러스 파랑 (요청 버전)
  --minus blue : 마이너스 파랑, 플러스 빨강 (한국 증권 앱 방식)
  --hard       : 색은 모두 같게, 부호(+/-)와 화살표만 다름
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shorts import music, tone, SR

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
F = lambda s: ImageFont.truetype(FONT, s)
REDC, BLUEC, INK, BG = "#e8343b", "#2a6fdb", "#1f2430", "#f4f6fa"


def arrow(d, x, y, s, up, col):
    if up:
        d.polygon([(x, y - s), (x - s, y + s * .7), (x + s, y + s * .7)], fill=col)
    else:
        d.polygon([(x, y + s), (x - s, y - s * .7), (x + s, y - s * .7)], fill=col)


def render(out, minus="red", hard=False, seed=3, find=15, n=5):
    rnd = random.Random(seed)
    cmin, cplus = (REDC, BLUEC) if minus == "red" else (BLUEC, REDC)
    if hard:
        cplus = cmin
    k_odd = rnd.randrange(n * n)
    vals = [-rnd.uniform(3, 38) for _ in range(n * n)]
    vals[k_odd] = rnd.uniform(1.2, 4.9)
    names = ["반도체", "2차전지", "바이오", "조선", "방산", "게임", "엔터", "건설", "화학", "은행",
             "증권", "통신", "철강", "항공", "자동차", "화장품", "식품", "여행", "해운", "로봇",
             "AI", "원전", "제약", "유통", "코인"]
    rnd.shuffle(names)
    names = [f"{x} 계좌" for x in names]  # 실제 종목 시세가 아님을 분명히 (가상)

    margin, gap = 36, 14
    cw = (W - 2 * margin - (n - 1) * gap) // n
    ch = 190
    top = 520
    grid_h = n * ch + (n - 1) * gap
    rev, end = 3.5, 3.0
    total = find + rev + end

    base = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(base)
    d.rectangle((0, 0, W, 330), fill="#141a26")
    d.text((W // 2, 120), "폭락장 속 내 수익률 찾기", font=F(82), fill="#fff", anchor="mm")
    d.text((W // 2, 230), "25개 계좌 중 딱 하나만 플러스!", font=F(52), fill="#ffd43b", anchor="mm")
    d.rounded_rectangle((60, 380, W - 60, 470), 45, fill="#fff", outline="#d0d5de", width=3)
    d.text((W // 2, 425), "※ 재미로 보는 가상 수익률입니다", font=F(36), fill="#8a93a3", anchor="mm")

    # 소리
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    put(.05, np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)]))
    for s in range(find - 5, find):
        put(s, tone([1200 if s < find - 1 else 1600], .08, .03, .35))
    for i, f in enumerate([523, 659, 784, 1047]):
        put(find + .1 + i * .12, tone([f, f * 2], .5, .25, .4))
    mus = music(total, "pluck"); a[: len(mus)] += mus / np.abs(mus).max() * np.abs(a).max() * .3
    wav = out + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a / np.abs(a).max() * .7 * 32767).astype(np.int16).tobytes())

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                           "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    jitter = [[rnd.uniform(-.4, .4) for _ in range(int(total * 2) + 2)] for _ in range(n * n)]
    flash = [rnd.random() * .5 for _ in range(n * n)]
    by = top + grid_h + 50
    for f in range(int(total * FPS)):
        t = f / FPS
        fr = base.copy(); dd = ImageDraw.Draw(fr)
        tick = int((t + 0) * 2)
        for k in range(n * n):
            r_, c_ = divmod(k, n)
            x, y = margin + c_ * (cw + gap), top + r_ * (ch + gap)
            v = vals[k] + (jitter[k][tick] if t < find else 0)
            if k == k_odd:
                v = max(.3, v)
            else:
                v = min(-.3, v)
            up = v > 0
            col = cplus if up else cmin
            blink = t < find and ((t + flash[k]) % .5) < .08     # 시세 갱신 깜빡
            dd.rounded_rectangle((x, y, x + cw, y + ch), 22, fill="#fff3f3" if blink else "#ffffff",
                                 outline="#dfe3ea", width=3)
            dd.text((x + cw / 2, y + 40), names[k], font=F(28), fill="#6b7383", anchor="mm")
            arrow(dd, x + cw / 2, y + 88, 16, up, col)
            dd.text((x + cw / 2, y + 145), f"{'+' if up else ''}{v:.2f}%", font=F(40), fill=col, anchor="mm")
        remain = max(0.0, find - t)
        tc = REDC if remain <= 5 else INK
        dd.text((80, by + 40), "찾아보기" if remain > 0 else "찾았다! 내 계좌", font=F(54), fill=INK, anchor="lm")
        dd.text((W - 80, by + 40), f"{math.ceil(remain)}초" if remain > 0 else "", font=F(64), fill=tc, anchor="rm")
        dd.rounded_rectangle((80, by + 100, W - 80, by + 134), 17, fill="#dfe3ea")
        if remain > 0:
            dd.rounded_rectangle((80, by + 100, 80 + max(34, (W - 160) * remain / find), by + 134), 17, fill=tc)
        if t >= find:
            r_, c_ = divmod(k_odd, n)
            cx, cy = margin + c_ * (cw + gap) + cw / 2, top + r_ * (ch + gap) + ch / 2
            pop = 1 + .3 * max(0, 1 - (t - find) / .3)
            rr = cw * .75 * pop
            dd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline="#ffb300", width=12)
        if t >= find + rev:
            dd.rounded_rectangle((70, by + 170, W - 70, by + 300), 65, fill="#141a26")
            dd.text((W / 2, by + 235), "여러분 계좌는 어떠신가요? 댓글로!", font=F(48), fill="#fff", anchor="mm")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    r_, c_ = divmod(k_odd, n)
    print(f"완료: {out}  정답 = {r_+1}번째 줄 {c_+1}번째 칸 (+{vals[k_odd]:.2f}%)  {total:.1f}초")


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    render(a[0], opt("--minus", "red"), "--hard" in a, opt("--seed", 3), opt("--time", 15))
