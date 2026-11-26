"""롱폼 틀린그림 (1920x1080, 좌우 나란히) – 레퍼런스 채널 구성.

구성: 인사·구독/좋아요 요청(5초) → [ROUND 카드 2초 → 찾기 N초 → 정답 10초] × 문제 수 → 마무리(8초)
문제 수 × 찾기 시간을 조절해 8분 이상(중간 광고 가능)으로 맞추기 좋음.

사용법:
  python3 longform.py out/long1 out/L1 out/L2 ... [--time 60] [--bgm musicbox|pluck] [--intro out/intro/intro_A_voice.mp4]
  각 문제 폴더에는 base.png, b.png, answers.json 이 있어야 함 (edit_*.py 결과)
결과: out/long1/long.mp4, thumbnail.png
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shorts import smart_crop, music, tone, SR

W, H, FPS = 1920, 1080, 15
BLUE, YELLOW, RED, GREEN, INK = "#2f6fd6", "#ffd43b", "#e53935", "#3f8f6a", "#3a2a2a"
FONT = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
F = lambda s: ImageFont.truetype(FONT, s)
HERE = os.path.dirname(os.path.abspath(__file__))
MASCOT = os.path.join(HERE, "..", "brand", "v2", "logo_A.png")
TOP = 165       # 머리띠 높이
GAP = 24        # 두 그림 사이 파란 칸


def mascot(size):
    m = Image.open(MASCOT).convert("RGB").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0); ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    return m, mask


def load(folder):
    A = Image.open(f"{folder}/base.png").convert("RGB")
    B = Image.open(f"{folder}/b.png").convert("RGB")
    ans = json.load(open(f"{folder}/answers.json"))
    for asp in (4 / 3,):                    # 양옆을 조금만 잘라 크게 (정답이 다 들어갈 때만)
        A2, B2, ans2 = smart_crop(A, B, ans, aspect=asp)
        if A2.size != A.size:
            return A2, B2, ans2
    return A, B, ans


def layout(A):
    cw, ch = (W - GAP) // 2, H - TOP
    s = min(cw / A.width, ch / A.height)
    w, h = round(A.width * s), round(A.height * s)
    y = TOP + (ch - h) // 2
    return [((cw - w) // 2, y, w, h), (cw + GAP + (cw - w) // 2, y, w, h)], s


def header(d, rnd, text, remain=None, total=None):
    d.rectangle((0, 0, W, TOP), fill=BLUE)
    d.polygon([(0, 0), (330, 0), (290, TOP), (0, TOP)], fill=YELLOW)
    d.text((24, 12), "ROUND", font=F(40), fill=BLUE, stroke_width=4, stroke_fill="#fff")
    d.text((150, 105), str(rnd), font=F(130), fill=BLUE, anchor="mm", stroke_width=8, stroke_fill="#fff")
    d.text((1010, 62), text, font=F(78), fill=YELLOW, anchor="mm", stroke_width=8, stroke_fill=INK)
    if remain is not None:
        d.rounded_rectangle((420, 118, 1600, 146), 10, fill="#d9cfd2")
        if remain > 0:
            d.rounded_rectangle((420, 118, 420 + max(20, 1180 * remain / total), 146), 10, fill="#ff2d2d")
        d.text((1790, 85), str(max(0, math.ceil(remain))), font=F(130),
               fill="#ff6b6b" if remain <= 10 else "#fff", anchor="mm")


def board(A, B, boxes):
    fr = Image.new("RGB", (W, H), "#ffffff")
    fr.paste(A.resize(boxes[0][2:], Image.LANCZOS), boxes[0][:2])
    fr.paste(B.resize(boxes[1][2:], Image.LANCZOS), boxes[1][:2])
    ImageDraw.Draw(fr).rectangle(((W - GAP) // 2, TOP, (W - GAP) // 2 + GAP, H), fill=BLUE)
    return fr


def intro_frame(t, n):
    fr = Image.new("RGB", (W, H), "#fff3dc")
    d = ImageDraw.Draw(fr)
    d.rectangle((0, 0, W, 300), fill=GREEN)
    d.text((W // 2, 110), "안녕하세요! 두뇌 건강 강화 프로젝트입니다", font=F(70), fill="#fff", anchor="mm")
    d.text((W // 2, 215), f"오늘의 틀린그림 {n}문제, 함께 풀어봐요!", font=F(58), fill="#ffe3a3", anchor="mm")
    m, mask = mascot(340); fr.paste(m, (210, 420), mask)
    d.text((1180, 470), "시작하기 전에", font=F(64), fill=INK, anchor="mm")
    d.text((1180, 570), "구독 · 좋아요 부탁드려요!", font=F(80), fill=INK, anchor="mm")
    s = 1 + 0.06 * math.sin(t * 2 * math.pi * 1.4)
    for k, (label, col, cx) in enumerate((("구독", RED, 960), ("좋아요 👍".replace(" 👍", ""), BLUE, 1400))):
        on = t > 1.2 + k * 0.8                 # 차례로 '눌린' 느낌
        bw, bh = 340 * s, 120 * s
        d.rounded_rectangle((cx - bw / 2, 720 - bh / 2, cx + bw / 2, 720 + bh / 2), bh / 2,
                            fill=col if on else "#bdbdbd")
        d.text((cx, 720), label + (" ✓" if on else ""), font=F(int(58 * s)), fill="#fff", anchor="mm")
    d.text((W // 2, 930), "알림 설정을 하시면 매일 새 문제를 받아보실 수 있어요", font=F(46), fill="#6b5a4a", anchor="mm")
    return fr


def round_card(rnd, n):
    fr = Image.new("RGB", (W, H), BLUE)
    d = ImageDraw.Draw(fr)
    d.text((W // 2, 430), f"ROUND {rnd}", font=F(220), fill=YELLOW, anchor="mm", stroke_width=12, stroke_fill=INK)
    d.text((W // 2, 640), f"{rnd} / {n}", font=F(80), fill="#fff", anchor="mm")
    return fr


def ending_frame(t, n):
    fr = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(fr)
    m, mask = mascot(320); fr.paste(m, (W // 2 - 160, 90), mask)
    d.text((W // 2, 520), "오늘도 수고 많으셨어요!", font=F(96), fill="#fff", anchor="mm")
    d.text((W // 2, 650), f"{n}문제 중 몇 문제 다 찾으셨나요? 댓글로 알려주세요", font=F(58), fill="#ffe3a3", anchor="mm")
    s = 1 + 0.06 * math.sin(t * 2 * math.pi * 1.4)
    bw, bh = 700 * s, 130 * s
    d.rounded_rectangle((W / 2 - bw / 2, 800 - bh / 2, W / 2 + bw / 2, 800 + bh / 2), bh / 2, fill=RED)
    d.text((W / 2, 800), "구독하고 내일 또 만나요!", font=F(int(60 * s)), fill="#fff", anchor="mm")
    return fr


THUMB_TEXT = "100명 중 100명이 다 찾는다!"
THUMB_POOL = [  # 영상마다 다른 문구를 순서대로 사용 (thumb_used.json에 기록)
    "100명 중 100명이 다 찾는다!",
    "끝까지 다 찾으면 눈썰미 대장!",
    "마지막 문제에서 다들 멈춥니다",
    "10문제 다 맞히면 두뇌 나이 30대!",
    "천천히 보면 누구나 찾아요!",
    "딱 1개가 안 보인다는 그 문제!",
    "오늘은 몇 문제나 찾으실까요?",
    "어제보다 하나 더 찾아보세요!",
    "엄마 아빠랑 같이 풀어보세요!",
    "다 찾으셨다면 댓글로 자랑하기!",
]


def next_thumb_text(path=os.path.join(HERE, "thumb_used.json")):
    import json as _j
    used = _j.load(open(path)) if os.path.exists(path) else []
    left = [t for t in THUMB_POOL if t not in used] or THUMB_POOL
    pick = left[0]
    used = (used + [pick])[-len(THUMB_POOL) + 1:]
    _j.dump(used, open(path, "w"), ensure_ascii=False, indent=1)
    return pick


def make_thumb(probs, out_dir, text=THUMB_TEXT):
    """썸네일 (레퍼런스 스타일: 빨간 띠 + 노란 글씨 + 좌우 그림 + 문제 수 배지)"""
    n = len(probs)
    A0, B0, _ = probs[0]
    th = Image.new("RGB", (1280, 720), "#fff"); d = ImageDraw.Draw(th)
    hw = 630; h0 = min(560, round(hw * A0.height / A0.width))
    th.paste(A0.resize((hw, h0)), (0, 720 - h0)); th.paste(B0.resize((hw, h0)), (650, 720 - h0))
    d.rectangle((630, 140, 650, 720), fill=BLUE)
    d.rectangle((0, 0, 1280, 150), fill="#8b1a1a")
    size = 84
    while d.textlength(text, font=F(size)) > 1220:
        size -= 2
    d.text((640, 75), text, font=F(size), fill=YELLOW, anchor="mm", stroke_width=7, stroke_fill="#000")
    d.rounded_rectangle((1090, 165, 1265, 235), 18, fill=RED)
    d.text((1177, 200), f"{n}문제", font=F(46), fill="#fff", anchor="mm")
    th.save(f"{out_dir}/thumbnail.png")


def render(out_dir, folders, find=90, bgm="musicbox", intro=None, ans_sec=10.0, thumb_text=None):
    os.makedirs(out_dir, exist_ok=True)
    probs = [load(f) for f in folders]
    n = len(probs)
    INTRO, CARD, ANS, END = 0.0, 1.5, ans_sec, 8.0   # 인트로는 따로 만든 영상(목소리 포함)을 앞에 이어 붙임
    seg = CARD + find + ANS
    total = INTRO + n * seg + END
    print(f"문제 {n}개 · 찾기 {find}초 → 총 {total/60:.1f}분" + ("" if total >= 480 else "  (8분 미만: 중간 광고 불가)"))

    # 소리
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    chime = lambda: np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)])
    ding = lambda: np.concatenate([tone([1319, 2637], .3, .2, .45), tone([1047, 2093], .8, .35, .45)])
    reveals = []
    for i in range(n):
        s0 = INTRO + i * seg
        put(s0, np.concatenate([tone([784, 1568], .15, .1, .4), tone([1047, 2094], .5, .25, .4)]))
        put(s0 + CARD, chime())
        for s in range(int(find) - 5, int(find)):
            put(s0 + CARD + s, tone([1200 if s < find - 1 else 1600], .08, .03, .35))
        ra = s0 + CARD + find
        for k, f in enumerate([523, 659, 784]):
            put(ra + k * .12, tone([f, f * 2], .4, .2, .35))
        rv = [ra + 0.8 + k * 1.2 for k in range(len(probs[i][2]))]
        reveals.append(rv)
        for r in rv:
            put(r, ding())
    put(total - END, chime())
    m = music(total, bgm); a[: len(m)] += m / np.abs(m).max() * np.abs(a).max() * .3
    wav = f"{out_dir}/_a.wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a / np.abs(a).max() * .7 * 32767).astype(np.int16).tobytes())

    make_thumb(probs, out_dir, thumb_text or next_thumb_text())

    out = f"{out_dir}/body.mp4" if intro else f"{out_dir}/long.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "22", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    boards = []
    for A, B, ans in probs:
        boxes, s = layout(A)
        boards.append((board(A, B, boxes), boxes, s, ans))
    cards = [round_card(i + 1, n) for i in range(n)]
    for k in range(int(total * FPS)):
        t = k / FPS
        if t < INTRO:
            fr = intro_frame(t, n)
        elif t >= total - END:
            fr = ending_frame(t - (total - END), n)
        else:
            i = min(n - 1, int((t - INTRO) // seg)); tt = t - INTRO - i * seg
            bd, boxes, s, ans = boards[i]
            if tt < CARD:
                fr = cards[i]
            elif tt < CARD + find:
                fr = bd.copy(); header(ImageDraw.Draw(fr), i + 1, f"다른 곳 {len(ans)}군데를 찾아보세요", CARD + find - tt, find)
            else:
                fr = bd.copy(); d = ImageDraw.Draw(fr)
                header(d, i + 1, "정답 공개!")
                for j, a_ in enumerate(ans):
                    if t < reveals[i][j]:
                        continue
                    pop = 1 + 0.4 * max(0.0, 1 - (t - reveals[i][j]) / 0.3)
                    for bx in boxes:                      # 양쪽 그림 모두에 동그라미만
                        x, y, r = bx[0] + a_["x"] * s, bx[1] + a_["y"] * s, max(a_["r"] * s, 40) * pop
                        d.ellipse((x - r, y - r, x + r, y + r), outline=RED, width=10)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    if intro:  # 인트로(목소리) + 본편 이어 붙이기
        final = f"{out_dir}/long.mp4"
        fc = ("[0:v]fps=15,scale=1920:1080,format=yuv420p,setsar=1[v0];[1:v]fps=15,format=yuv420p,setsar=1[v1];"
              "[0:a]aresample=44100,aformat=channel_layouts=mono[a0];[1:a]aresample=44100,aformat=channel_layouts=mono[a1];"
              "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", intro, "-i", out, "-filter_complex", fc,
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-tune", "stillimage", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", final], check=True)
        os.remove(out); out = final
    print("완료:", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    opts = {"--time": 90, "--bgm": "musicbox", "--intro": ""}
    rest = []
    i = 0
    while i < len(a):
        if a[i] in opts:
            opts[a[i]] = type(opts[a[i]])(a[i + 1]); i += 2
        else:
            rest.append(a[i]); i += 1
    render(rest[0], rest[1:], opts["--time"], opts["--bgm"], opts["--intro"] or None)
