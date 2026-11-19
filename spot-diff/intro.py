"""롱폼 시작 인사 (A안, 약 10초, 1920x1080).

대본(A안)
  0~3초  안녕하세요! 두뇌 건강 강화 프로젝트입니다.
  3~6초  오늘도 재미있는 틀린그림 다섯 문제를 준비했어요.
  6~9초  시작하기 전에 구독과 좋아요 한 번 눌러주시면 큰 힘이 됩니다.
  9~10초 그럼, 시작해 볼까요?

사용법:
  python3 intro.py out/intro/intro_A.mp4                       # 목소리 없이 (자막 + 음악 + 효과음)
  python3 intro.py out/intro/intro_A.mp4 --voice 내레이션.mp3    # 목소리 파일을 받으면 입혀서
  옵션: --n 5 (오늘 문제 수)
목소리 파일이 10초보다 길면 영상 길이를 목소리에 맞춰 늘림.
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shorts import music, tone, SR

W, H, FPS = 1920, 1080, 30
GREEN, RED, BLUE, INK, CREAM = "#3f8f6a", "#e53935", "#2f6fd6", "#3a2a2a", "#fff3dc"
FONT = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
F = lambda s: ImageFont.truetype(FONT, s)
HERE = os.path.dirname(os.path.abspath(__file__))
MASCOT = os.path.join(HERE, "..", "brand", "v2", "logo_A.png")
KOR_NUM = {3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열"}

LINES = [  # (시작초, 자막)
    (0.0, "안녕하세요! 두뇌 건강 강화 프로젝트입니다."),
    (3.0, "오늘도 재미있는 틀린그림 {k} 문제를 준비했어요."),
    (6.0, "시작하기 전에 구독과 좋아요 한 번 눌러주시면 큰 힘이 됩니다."),
    (9.0, "그럼, 시작해 볼까요?"),
]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def frame(t, n, scale_t, mas):
    """scale_t: 원래 10초 기준 시각 (목소리가 길면 늘어난 시간을 10초로 환산)"""
    st = scale_t
    fr = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(fr)
    # 위 초록 띠
    d.rectangle((0, 0, W, 170), fill=GREEN)
    d.text((W // 2, 88), "두뇌 건강 강화 프로젝트", font=F(84), fill="#fff", anchor="mm")
    # 캐릭터: 통통 튀며 등장
    m, mask = mas
    y = 260 - 40 * abs(math.sin(t * 2.4)) if st > .6 else 260 + 400 * (1 - ease(st / .6))
    d.ellipse((150, y - 10, 590, y + 430), fill="#ffffff")
    fr.paste(m, (160, int(y)), mask)
    cx = 1220
    if st < 3:                                    # 1) 인사
        a = ease(st / .5)
        d.text((cx, 470), "안녕하세요!", font=F(int(150 * (.6 + .4 * a))), fill=INK, anchor="mm")
    elif st < 6:                                  # 2) 오늘의 문제
        d.text((cx, 400), "오늘의 틀린그림", font=F(90), fill=INK, anchor="mm")
        p = 1 + .25 * max(0, 1 - (st - 3) / .3)
        d.rounded_rectangle((cx - 250 * p, 480, cx + 250 * p, 480 + 170 * p), 50, fill=RED)
        d.text((cx, 480 + 85 * p), f"{n}문제", font=F(int(120 * p)), fill="#fff", anchor="mm")
    elif st < 9:                                  # 3) 구독·좋아요 (차례로 눌림)
        d.text((cx, 360), "구독 · 좋아요 부탁드려요!", font=F(84), fill=INK, anchor="mm")
        for k, (label, col, x) in enumerate((("구독", RED, cx - 260), ("좋아요", BLUE, cx + 260))):
            on = st > 6.8 + k * .9
            p = 1 + .2 * max(0, 1 - (st - (6.8 + k * .9)) / .25) if on else 1
            bw, bh = 400 * p, 150 * p
            d.rounded_rectangle((x - bw / 2, 560 - bh / 2, x + bw / 2, 560 + bh / 2), bh / 2,
                                fill=col if on else "#bdbdbd")
            tx = x - (28 * p if on else 0)
            d.text((tx, 560), label, font=F(int(72 * p)), fill="#fff", anchor="mm")
            if on:  # 체크 표시 직접 그리기
                ex = tx + d.textlength(label, font=F(int(72 * p))) / 2 + 22 * p
                d.line([(ex, 560), (ex + 16 * p, 578 * 1 + 0), (ex + 46 * p, 536)], fill="#fff", width=int(10 * p), joint="curve")
            if on and st - (6.8 + k * .9) < .5:      # 손가락 대신 반짝 원
                r = 60 + 200 * (st - (6.8 + k * .9))
                d.ellipse((x - r, 560 - r, x + r, 560 + r), outline="#ffd43b", width=8)
    else:                                         # 4) 시작!
        p = ease((st - 9) / .4)
        d.text((cx, 500), "그럼, 시작해 볼까요?", font=F(int(110 * (.5 + .5 * p))), fill=GREEN, anchor="mm")
    # 아래 자막
    line = [s for t0, s in LINES if st >= t0][-1].format(k=KOR_NUM.get(n, str(n)))
    d.rectangle((0, H - 170, W, H), fill="#00000099" if False else "#2b2b2b")
    d.text((W // 2, H - 85), line, font=F(56), fill="#fff", anchor="mm")
    return fr


DELAY = 0.3  # 목소리 시작 지연


def sentence_starts(voice, k=3):
    """목소리에서 가장 긴 쉼 k개를 찾아 2~4번째 문장 시작 시각(영상 기준)을 돌려줌."""
    log = subprocess.run(["ffmpeg", "-i", voice, "-af", "silencedetect=noise=-32dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    import re
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    pauses = sorted(zip(st, en), key=lambda p: p[0] - p[1])[:k]   # 긴 쉼 순
    return sorted(e + DELAY for _, e in pauses)


def render(out, n=5, voice=None):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    vlen = 0.0
    if voice:
        vlen = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                              "-of", "csv=p=0", voice]).decode().strip())
    total = max(10.0, vlen + 0.6)
    # 화면 장면(원래 0·3·6·9·10초)을 목소리 문장 시작에 맞춰 구간별로 늘림
    real = [0.0, 3.0, 6.0, 9.0, 10.0]
    if voice:
        b = sentence_starts(voice)
        if len(b) == 3:
            real = [0.0] + b + [total]
        else:
            real = [x * total / 10 for x in real]
    scene = [0.0, 3.0, 6.0, 9.0, 10.0]
    to_scene = lambda t: float(np.interp(t, real, scene))
    to_real = lambda x: float(np.interp(x, scene, real))
    print("문장 시작(초):", [round(x, 2) for x in real[1:4]])
    a = np.zeros(int(SR * (total + 1)))
    def put(at, sig):
        i = int(at * SR); j = min(len(a), i + len(sig)); a[i:j] += sig[: j - i]
    put(.1, np.concatenate([tone([1047, 2094], .25, .15), tone([1319, 2638], .6, .3)]))
    put(to_real(3), np.concatenate([tone([784, 1568], .15, .1, .4), tone([1047, 2094], .4, .2, .4)]))
    put(to_real(6.8), tone([1568, 3136], .3, .15, .45)); put(to_real(7.7), tone([1568, 3136], .3, .15, .45))
    put(to_real(9), np.concatenate([tone([784, 1568], .15, .1, .4), tone([1047, 2094], .2, .12, .4), tone([1568, 3136], .6, .3, .4)]))
    m = music(total, "pluck"); a[: len(m)] += m / np.abs(m).max() * np.abs(a).max() * (.18 if voice else .35)
    a = a / np.abs(a).max() * .6
    wav = out + ".bg.wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((a * 32767).astype(np.int16).tobytes())

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav]
    if voice:  # 목소리를 0.3초 뒤에 시작, 배경과 섞기
        cmd += ["-i", voice, "-filter_complex", f"[2:a]adelay={int(DELAY*1000)}|{int(DELAY*1000)},volume=1.3[v];[1:a][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.7[a]",
                "-map", "0:v", "-map", "[a]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    mas = (Image.open(MASCOT).convert("RGB").resize((420, 420), Image.LANCZOS),)
    mk = Image.new("L", (420, 420), 0); ImageDraw.Draw(mk).ellipse((0, 0, 420, 420), fill=255)
    mas = (mas[0], mk)
    for f in range(int(total * FPS)):
        t = f / FPS
        ff.stdin.write(frame(t, n, to_scene(t), mas).tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print(f"완료: {out} ({total:.1f}초)")


if __name__ == "__main__":
    a = sys.argv[1:]
    n = int(a[a.index("--n") + 1]) if "--n" in a else 5
    voice = a[a.index("--voice") + 1] if "--voice" in a else None
    render(a[0], n, voice)
