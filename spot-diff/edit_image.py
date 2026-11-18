"""AI 없이 기존 그림에 차이점을 직접 넣기 (색 바꾸기 / 지우기).
결과: base.png, b.png, answers.json → video.py 로 바로 영상화."""
import json, colorsys
import numpy as np
from PIL import Image, ImageFilter

def hue_mask(a, box, hmin, hmax, smin):
    x0, y0, x1, y1 = box
    rgb = a[y0:y1, x0:x1] / 255.0
    mx, mn = rgb.max(2), rgb.min(2)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    h = np.select([mx == r, mx == g], [((g - b) / d) % 6, (b - r) / d + 2], (r - g) / d + 4) * 60
    m = np.zeros(a.shape[:2], bool)
    m[y0:y1, x0:x1] = (h >= hmin) & (h <= hmax) & (s >= smin)
    return m

def shift_hue(a, mask, deg, sat=1.0, light=1.0):
    out = a.copy()
    for y, x in zip(*np.nonzero(mask)):
        h, l, s = colorsys.rgb_to_hls(*(a[y, x] / 255.0))
        out[y, x] = np.array(colorsys.hls_to_rgb((h + deg / 360) % 1, min(1, l * light), s * sat)) * 255
    return out

def erase_disk(a, cx, cy, R):
    """원 영역을 좌우 바깥 하늘색으로 보간해 지움 (부드러운 하늘 배경용)."""
    out = a.astype(float).copy()
    for y in range(cy - R, cy + R + 1):
        w = int((R * R - (y - cy) ** 2) ** 0.5)
        win = lambda x0: np.median(a[y - 4:y + 5, x0 - 4:x0 + 5].reshape(-1, 3), 0)  # 별 무시
        L, Rr = win(cx - w - 6), win(cx + w + 6)
        for x in range(cx - w - 2, cx + w + 3):
            t = (x - (cx - w - 3)) / (2 * w + 6)
            out[y, x] = L * (1 - t) + Rr * t
    return out.astype(np.uint8)

def feather(orig, edited, mask, px=2):
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(px))
    m = np.asarray(m)[..., None] / 255.0
    return (orig * (1 - m) + edited * m).astype(np.uint8)

if __name__ == "__main__":
    folder = "out/camping2"
    A = np.asarray(Image.open(f"{folder}/base.png").convert("RGB"))
    B = A.copy()
    answers = []

    # 1) 노란 후드티 → 초록 후드티
    m = hue_mask(A, (632, 335, 738, 425), 20, 55, 0.5)
    B = feather(B, shift_hue(B, m, 80, sat=0.45, light=0.75), m, 1)
    answers.append({"label": "후드티 색", "x": 688, "y": 378, "r": 58})

    # 2) 파란 아이스박스 → 빨간 아이스박스
    m = hue_mask(A, (190, 498, 292, 572), 190, 235, 0.3)
    B = feather(B, shift_hue(B, m, 150), m, 1)
    answers.append({"label": "아이스박스 색", "x": 238, "y": 535, "r": 55})

    # 3) 보름달 사라짐
    cx, cy, R = 693, 83, 66
    E = erase_disk(B, cx, cy, R)
    mm = np.zeros(A.shape[:2], bool)
    yy, xx = np.ogrid[:A.shape[0], :A.shape[1]]
    mm[(xx - cx) ** 2 + (yy - cy) ** 2 <= (R - 2) ** 2] = True
    B = feather(B, E, mm, 4)
    for sx, sy in ((672, 60), (715, 104), (700, 70)):
        B[sy - 1:sy + 2, sx - 1:sx + 2] = (235, 235, 245)
    answers.append({"label": "보름달 사라짐", "x": cx, "y": cy, "r": 52})

    Image.fromarray(B).save(f"{folder}/b.png")
    json.dump(answers, open(f"{folder}/answers.json", "w"), ensure_ascii=False, indent=1)
    print("완료", [a["label"] for a in answers])
