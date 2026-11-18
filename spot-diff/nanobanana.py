"""나노바나나(Gemini 이미지 모델)로 틀린그림찾기 만들기.

흐름:
 1) 테마 프롬프트로 원본(A) 1장 생성
 2) 원본을 기준으로 차이점마다 따로 부분 편집 요청
 3) 편집본과 원본을 픽셀 비교해 '가장 큰 변화 덩어리'만 잘라 B에 붙임
    → AI가 다른 곳을 미세하게 바꿔도 B에는 의도한 차이만 남음
 4) 쇼츠용 문제/정답 이미지(1080x1920) 렌더

사용법:
  export GEMINI_API_KEY=...   (클라우드 세션에선 프록시가 자동 주입)
  python3 nanobanana.py themes/park.json out/park
  python3 nanobanana.py themes/park.json out/park --reuse   # 받은 이미지 재사용, 합성만 다시
"""
import base64, io, json, os, sys, time, urllib.request, urllib.error
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

MODEL = os.environ.get("NANOBANANA_MODEL", "gemini-2.5-flash-image")
API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
W, H = 1024, 768  # 작업 해상도 (4:3)


def call(parts, aspect="4:3", tries=3):
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": aspect}}}
    req = urllib.request.Request(
        API.format(MODEL), data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": os.environ.get("GEMINI_API_KEY", "dummy")})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            for p in data["candidates"][0]["content"]["parts"]:
                if "inlineData" in p:
                    return Image.open(io.BytesIO(base64.b64decode(p["inlineData"]["data"]))).convert("RGB")
            raise RuntimeError("이미지 없음: " + json.dumps(data)[:300])
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code in (429, 500, 503) and i < tries - 1:
                time.sleep(5 * (i + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")


def img_part(im):
    buf = io.BytesIO(); im.save(buf, "PNG")
    return {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}}


def change_mask(a, b, thresh=40, min_frac=0.0008, max_frac=0.08):
    """원본 a와 편집본 b 사이에서 가장 큰 변화 영역 마스크를 돌려준다(없거나 너무 크면 None)."""
    d = np.abs(np.asarray(a, int) - np.asarray(b, int)).sum(2)
    m = ndimage.binary_opening(d > thresh, iterations=2)
    m = ndimage.binary_dilation(m, iterations=6)
    lab, n = ndimage.label(m)
    if n == 0:
        return None, "변화 없음"
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    frac = sizes[k - 1] / m.size
    if frac < min_frac:
        return None, f"변화가 너무 작음({frac:.4f})"
    if frac > max_frac:
        return None, f"변화가 너무 큼({frac:.3f}) - 그림 전체가 바뀐 듯"
    region = ndimage.binary_fill_holes(lab == k)
    return ndimage.binary_dilation(region, iterations=4), "ok"


def build(theme, out, reuse=False):
    os.makedirs(out, exist_ok=True)
    base_p = f"{out}/base.png"
    if reuse and os.path.exists(base_p):
        base = Image.open(base_p).convert("RGB")
    else:
        print("원본 생성 중...")
        base = call([{"text": theme["base_prompt"]}]).resize((W, H), Image.LANCZOS)
        base.save(base_p)

    b = np.asarray(base).copy()
    answers = []
    for i, e in enumerate(theme["edits"]):
        p = f"{out}/edit_{i}.png"
        if reuse and os.path.exists(p):
            ed = Image.open(p).convert("RGB")
        else:
            print(f"편집 {i+1}/{len(theme['edits'])}: {e['label']}")
            prompt = (f"Edit this illustration: {e['instruction']} "
                      "Change ONLY that one thing. Keep every other pixel, the composition, "
                      "framing, colors, line style and all other objects exactly the same.")
            try:
                ed = call([img_part(base), {"text": prompt}]).resize((W, H), Image.LANCZOS)
            except Exception as ex:
                print("  실패:", ex); continue
            ed.save(p)
        mask, why = change_mask(base, ed)
        if mask is None:
            print(f"  건너뜀 ({e['label']}): {why}"); continue
        b[mask] = np.asarray(ed)[mask]
        ys, xs = np.nonzero(mask)
        cx, cy = xs.mean(), ys.mean()
        r = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + 12
        answers.append({"label": e["label"], "x": float(cx), "y": float(cy), "r": float(r)})
        print(f"  적용 ({e['label']})")

    B = Image.fromarray(b)
    B.save(f"{out}/b.png")
    json.dump(answers, open(f"{out}/answers.json", "w"), ensure_ascii=False, indent=1)
    render(base, B, answers, theme.get("title", "틀린 곳을 찾아보세요!"), out)
    print(f"완료: 차이점 {len(answers)}개 → {out}/quiz.png, {out}/answer.png")


def render(A, B, answers, title, out):
    n = len(answers)
    pw, ph = 1000, 750
    def canvas(head, img_b, foot):
        c = Image.new("RGB", (1080, 1920), "#fff3dc")
        d = ImageDraw.Draw(c)
        f1, f2 = ImageFont.truetype(FONT, 70), ImageFont.truetype(FONT, 42)
        d.text((540, 110), head, font=f1, fill="#2b2b2b", anchor="mm")
        for y, im in ((200, A), (990, img_b)):
            d.rounded_rectangle((32, y - 8, 1048, y + ph + 8), 28, fill="#2b2b2b")
            mask = Image.new("L", (pw, ph), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, ph), 22, fill=255)
            c.paste(im.resize((pw, ph), Image.LANCZOS), (40, y), mask)
        d.text((540, 1840), foot, font=f2, fill="#555", anchor="mm")
        return c
    canvas(title.replace("{n}", str(n)), B, "상위 1%만 다 찾아요 · 몇 개 찾으셨나요?").save(f"{out}/quiz.png")
    s = pw / W
    Bc = B.resize((pw, ph), Image.LANCZOS)
    d = ImageDraw.Draw(Bc)
    for a in answers:
        x, y, r = a["x"] * s, a["y"] * s, a["r"] * s
        d.ellipse((x - r, y - r, x + r, y + r), outline="#ff2d55", width=9)
    canvas("정답 공개!", Bc, " · ".join(a["label"] for a in answers)).save(f"{out}/answer.png")


if __name__ == "__main__":
    theme = json.load(open(sys.argv[1]))
    build(theme, sys.argv[2], "--reuse" in sys.argv)
