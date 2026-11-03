#!/usr/bin/env python3
"""3D 버전 영상 만들기.

1) config.json 작성 (타이밍은 ../make_video.py 와 동일 → 음악/효과음 그대로 재사용)
2) node render.js 로 3D 프레임 렌더링 (three.js + 헤드리스 크롬)
3) 한글 자막·말풍선·색종이 등 2D 오버레이 합성 + 음악 → animal_numbers_3d.mp4

사용:
  python3 compose3d.py                  # 전체 제작
  python3 compose3d.py --preview DIR f1,f2,...   # 일부 프레임만 PNG 로
"""
import json
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import cairo
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import make_video as mv  # noqa: E402

W, H, FPS = mv.W, mv.H, mv.FPS
FRAMES = os.environ.get("FRAMES_DIR", os.path.join(HERE, "_frames"))
OUT = os.path.join(os.path.dirname(HERE), "animal_numbers_3d.mp4")
GPU = os.environ.get("GPU") == "1"
SS = float(os.environ.get("SS", "2.0" if GPU else "1.5"))


def ffmpeg_exe():
    import shutil
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg  # pip install imageio-ffmpeg (윈도우용 ffmpeg 포함)
    return imageio_ffmpeg.get_ffmpeg_exe()


def to_hex(c):
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in c)


def write_config():
    cfg = dict(fps=FPS, ss=SS, hq=GPU, intro=mv.INTRO, outro=mv.OUTRO, head=mv.HEAD, step=mv.STEP, tail=mv.TAIL,
               fly=0.55, scenes=[list(s) for s in mv.SCENES],
               numColors=[to_hex(c) for c in mv.NUM_COLORS],
               skies=[[to_hex(lighten_sky(a, 0.0)), to_hex(b)] for a, b in mv.SKIES])
    with open(os.path.join(HERE, "config.json"), "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)


def lighten_sky(c, k):
    return mv.lighten(c, k)


# ------------------------------------------------------------------ overlays
clamp, back_out, ease_out = mv.clamp, mv.back_out, mv.ease_out
draw_text, draw_bubble = mv.draw_text, mv.draw_bubble
letter_pop, letter_wave, combine = mv.letter_pop, mv.letter_wave, mv.combine
hx, rgb = mv.hx, mv.rgb
TAU = math.tau


def vignette(ctx):
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, H * 1.05)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0.05, 0.02, 0.1, 0.28)
    ctx.set_source(g)
    ctx.paint()


def glow_sparkles(ctx, cx, cy, rad, t, n=4, col=(1, 0.95, 0.55)):
    for k in range(n):
        a = t * 1.2 + k * TAU / n
        r = 18 + 8 * math.sin(t * 6 + k)
        mv.sparkle_path(ctx, cx + math.cos(a) * rad, cy + math.sin(a) * rad * 0.9, r, t * 2 + k)
        rgb(ctx, col)
        ctx.fill()


def overlay_intro(ctx, t, meta):
    if t > 1.0:
        f = combine(letter_pop(t - 1.0, 0.08), letter_wave(t, 6, 3, 0.6))
        draw_text(ctx, "동물 친구들과", W / 2, 150, 120, hx("ff7a5c"), per_char=f)
    if t > 2.0:
        f = combine(letter_pop(t - 2.0, 0.1, 0.6), letter_wave(t, 10, 3.5, 0.7))
        draw_text(ctx, "숫자 놀이!", W / 2, 330, 210, hx("3d8ef0"), ow=28, per_char=f)
    if t > 3.6:
        a = ease_out((t - 3.6) / 0.6)
        draw_text(ctx, "1부터 10까지 같이 세어 볼까요?", W / 2, 500, 60, hx("8a5a3a"),
                  per_char=lambda i: (1, 20 * (1 - a), 0, a))


def overlay_number(ctx, idx, t, meta):
    n, word, sino, animal, josa, count_word, kind = mv.SCENES[idx]
    col = mv.NUM_COLORS[idx]
    if "numTop" in meta:
        bs = mv.elastic(clamp((t - 0.15) / 0.9))
        if bs > 0.3:
            glow_sparkles(ctx, meta["numTop"][0], meta["numTop"][1], 190 * bs, t)
    if "num" in meta:
        nx, ny = meta["num"][0], meta["num"][1]
        if t > 0.9:
            f = combine(letter_pop(t - 0.9, 0.1, 0.5), letter_wave(t, 6, 3, 0.6))
            draw_text(ctx, word, nx, ny + 40, 112, col, ow=17, per_char=f)
        if t > 1.4:
            a = ease_out((t - 1.4) / 0.4)
            draw_text(ctx, f"({sino})", nx, ny + 135, 56, hx("8a6a5a"), per_char=lambda i: (a, 0, 0, a))
    anchors = meta["anchors"]
    for i in range(n):
        tl = t - (mv.HEAD + i * mv.STEP + 0.55)
        if 0 <= tl < 0.75 and i < len(anchors) and anchors[i][2]:
            x, y = anchors[i][0], anchors[i][1]
            sc = back_out(clamp(tl / 0.25)) * (1 if tl < 0.6 else 1 - (tl - 0.6) / 0.15)
            draw_bubble(ctx, x, y - 60, mv.WORDS[i], sc, col)
    cheer0 = mv.HEAD + n * mv.STEP + 0.6
    if t > cheer0 - 0.2:
        tt = t - cheer0 + 0.2
        text = f"{animal}{josa} {count_word} 있어요!"
        _, w = mv.vfont().layout(text, 84)
        bw = w + 120
        s = back_out(clamp(tt / 0.45))
        cx, cy = W / 2 + 150, 115
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(s, s)
        mv.round_rect(ctx, -bw / 2, -56, bw, 132, 66)
        ctx.set_source_rgba(0, 0, 0, 0.15)
        ctx.fill()
        mv.round_rect(ctx, -bw / 2, -66, bw, 132, 66)
        mv.paint_shape(ctx, (1, 1, 1), col, 7)
        ctx.restore()
        if s > 0.5:
            f = combine(letter_pop(tt - 0.2, 0.045, 0.4), letter_wave(t, 5, 4, 0.5))
            draw_text(ctx, text, cx, cy, 84, col, ow=0, shadow=False, per_char=f)
            for k in range(8):
                a = t * 1.1 + k * TAU / 8
                mv.sparkle_path(ctx, cx + math.cos(a) * (bw / 2 + 40), cy + math.sin(a) * 95,
                                16 + 6 * math.sin(t * 7 + k), t * 2 + k)
                rgb(ctx, hx("ffd23a"))
                ctx.fill()
    mv.draw_confetti(ctx, t - cheer0, idx, 45)


def overlay_outro(ctx, t, meta):
    anchors = meta["anchors"]
    for i, sc in enumerate(mv.SCENES):
        hl = 2.2 + i * 0.55
        if 0 < t - hl < 0.6 and i < len(anchors) and anchors[i][2]:
            s = back_out(clamp((t - hl) / 0.2)) * (1 - clamp((t - hl - 0.45) / 0.15))
            draw_bubble(ctx, anchors[i][0], anchors[i][1] - 55, sc[1], s, mv.NUM_COLORS[i])
    if 1.8 < t < 7.6:
        a = clamp((t - 1.8) / 0.4) * clamp((7.6 - t) / 0.4)
        draw_text(ctx, "다 같이 세어 봐요!", W / 2, 200, 120, hx("8a5cf0"), per_char=lambda i: (1, 0, 0, a))
    if t > 7.8:
        f = combine(letter_pop(t - 7.8, 0.08, 0.5), letter_wave(t, 10, 4, 0.6))
        draw_text(ctx, "참 잘했어요!", W / 2, 190, 180, hx("ff6a5a"), ow=26, per_char=f)
    if t > 9.0:
        f = combine(letter_pop(t - 9.0, 0.05, 0.4), letter_wave(t, 5, 3, 0.5))
        draw_text(ctx, "다음에 또 만나요~ 안녕!", W / 2, 380, 86, hx("3d8ef0"), per_char=f)
    mv.draw_confetti(ctx, t - 7.8, 99, 90)


# ------------------------------------------------------------------ compose
def load_frame(fi):
    name = os.path.join(FRAMES, f"f{fi:05d}")
    img = np.asarray(Image.open(name + ".jpg").convert("RGB"))
    with open(name + ".json") as f:
        meta = json.load(f)
    buf = np.empty((H, W, 4), np.uint8)
    buf[..., 0] = img[..., 2]
    buf[..., 1] = img[..., 1]
    buf[..., 2] = img[..., 0]
    buf[..., 3] = 255
    return buf, meta


def compose_single(fi):
    buf, meta = load_frame(fi)
    surf = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_RGB24, W, H, W * 4)
    ctx = cairo.Context(surf)
    vignette(ctx)
    si, t = meta["si"], meta["t"]
    kind, idx, _ = mv.SEGS[si]
    if kind == "intro":
        overlay_intro(ctx, t, meta)
    elif kind == "num":
        overlay_number(ctx, idx, t, meta)
    else:
        overlay_outro(ctx, t, meta)
    surf.flush()
    return buf, si, t


_last_cache = {}


def compose_frame(fi):
    buf, si, t = compose_single(fi)
    if si > 0 and t < mv.WIPE:
        # 이전 장면 마지막 프레임 위로 원형 와이프
        prev_fi = int(round(mv.STARTS[si] * FPS)) - 1
        if prev_fi not in _last_cache:
            _last_cache.clear()
            _last_cache[prev_fi] = compose_single(prev_fi)[0]
        prev = _last_cache[prev_fi].copy()
        out = cairo.ImageSurface.create_for_data(memoryview(prev), cairo.FORMAT_RGB24, W, H, W * 4)
        cur = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_RGB24, W, H, W * 4)
        ctx = cairo.Context(out)
        r = mv.ease_io(t / mv.WIPE) * 1250
        ctx.save()
        ctx.arc(W / 2, H / 2, r, 0, TAU)
        ctx.clip()
        ctx.set_source_surface(cur, 0, 0)
        ctx.paint()
        ctx.restore()
        ctx.new_path()
        ctx.arc(W / 2, H / 2, r, 0, TAU)
        ctx.set_line_width(28)
        rgb(ctx, (1, 1, 1))
        ctx.stroke()
        ctx.arc(W / 2, H / 2, r + 21, 0, TAU)
        ctx.set_line_width(14)
        rgb(ctx, mv.NUM_COLORS[si % 10])
        ctx.stroke()
        out.flush()
        buf = prev
    T = fi / FPS
    a = min(clamp(T / 0.5), clamp((mv.TOTAL - T) / 0.8))
    if a < 1:
        buf[..., :3] = (buf[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    return buf.tobytes()


def main():
    write_config()
    if "--config" in sys.argv:
        return
    if "--preview" in sys.argv:
        outdir = sys.argv[sys.argv.index("--preview") + 1]
        frames = [int(x) for x in sys.argv[sys.argv.index("--preview") + 2].split(",")]
        need = set(frames)
        for fi in frames:  # 와이프 프레임은 이전 장면 끝 프레임도 필요
            T = fi / FPS
            si = max(i for i, s in enumerate(mv.STARTS) if s <= T + 1e-9)
            if si > 0 and T - mv.STARTS[si] < mv.WIPE:
                need.add(int(round(mv.STARTS[si] * FPS)) - 1)
        subprocess.run(["node", os.path.join(HERE, "render.js"), FRAMES, os.environ.get("WORKERS", "2"), ",".join(map(str, sorted(need)))], check=True)
        for fi in frames:
            b = compose_frame(fi)
            Image.frombuffer("RGBX", (W, H), b, "raw", "BGRX").convert("RGB").save(os.path.join(outdir, f"q{fi:05d}.png"))
        return

    nframes = int(mv.TOTAL * FPS)
    if "--skip-render" not in sys.argv:
        subprocess.run(["node", os.path.join(HERE, "render.js"), FRAMES, os.environ.get("WORKERS", "4")], check=True)
    wav_path = os.path.join(HERE, "_audio.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(mv.SR)
        w.writeframes(mv.build_audio().tobytes())
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "bgr0", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_path,
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, fr in enumerate(pool.imap(compose_frame, range(nframes), chunksize=10)):
            proc.stdin.write(fr)
            if k % 500 == 0:
                print(f"  compose {k}/{nframes}", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    os.remove(wav_path)
    print(f"완성: {OUT}")


if __name__ == "__main__":
    main()
