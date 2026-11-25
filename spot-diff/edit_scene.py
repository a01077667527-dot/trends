"""설정(JSON)대로 그림에 차이점 넣기 – 색 바꾸기(hue) / 지우기(remove).

spec.json 예:
[
 {"type": "hue", "label": "티셔츠 색", "box": [x0,y0,x1,y1], "hue": [190,240], "smin": 0.3, "shift": 120, "sat": 1.0, "light": 1.0},
 {"type": "remove", "label": "강아지 사라짐", "box": [x0,y0,x1,y1], "thresh": 40}
]
- hue: 상자 안에서 색상(0~360)·채도 조건에 맞는 픽셀만 색을 돌림. 빨강처럼 0을 걸치면 hue: [340, 20]
- remove: 상자 테두리의 바탕색과 다른 픽셀(=물건)을 찾아 지우고 주변으로 메움(인페인팅)
사용법: python3 edit_scene.py out/L1 spec_L1.json  → out/L1/b.png, answers.json, check.png
"""
import json, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw
from edit_image import hue_mask, shift_hue, feather


def do_hue(A, B, op):
    h0, h1 = op["hue"]
    box = tuple(op["box"])
    if h0 <= h1:
        m = hue_mask(A, box, h0, h1, op.get("smin", 0.3))
    else:
        m = hue_mask(A, box, h0, 360, op.get("smin", 0.3)) | hue_mask(A, box, 0, h1, op.get("smin", 0.3))
    if op.get("vmin"):
        m &= A.max(2) >= op["vmin"]
    if op.get("vmax"):
        m &= A.max(2) <= op["vmax"]
    if op.get("seed"):   # 씨앗 점과 이어진 덩어리만 (옆의 같은 색 물건은 제외)
        from scipy import ndimage
        lab, _ = ndimage.label(m)
        sx, sy = op["seed"]
        k = lab[sy, sx]
        if k == 0:   # 씨앗이 선 위 등에 있으면 가장 가까운 덩어리
            ys, xs = np.nonzero(lab)
            j = int(np.argmin((xs - sx) ** 2 + (ys - sy) ** 2))
            k = lab[ys[j], xs[j]]
        m = lab == k
        m = ndimage.binary_fill_holes(m) & (m | ndimage.binary_dilation(m, iterations=2))
    B = feather(B, shift_hue(B, m, op["shift"], op.get("sat", 1.0), op.get("light", 1.0)), m, 1)
    return B, m


def do_remove(A, B, op):
    x0, y0, x1, y1 = op["box"]
    ring = np.zeros(A.shape[:2], bool)
    ring[max(0, y0 - 6):y1 + 6, max(0, x0 - 6):x1 + 6] = True
    ring[y0:y1, x0:x1] = False
    bg = np.median(A[ring], 0)
    diff = np.abs(A.astype(int) - bg).sum(2) > op.get("thresh", 40)
    m = np.zeros(A.shape[:2], np.uint8)
    m[y0:y1, x0:x1] = diff[y0:y1, x0:x1]
    if op.get("fill_box"):
        m[y0:y1, x0:x1] = 1
    m = cv2.dilate(m, np.ones((7, 7), np.uint8))
    if op.get("flat"):   # 바탕이 단색이면 바탕색 한 가지로 채움 (번짐 없음)
        E = B.copy(); E[m.astype(bool)] = bg
    else:
        E = cv2.inpaint(np.ascontiguousarray(B), m * 255, op.get("radius", 6), cv2.INPAINT_TELEA)
    return feather(B, E, m.astype(bool), 1), m.astype(bool)


def do_tint(A, B, op):
    """씨앗 점에서 비슷한 색으로 이어진 영역(외곽선에서 멈춤)을 목표 색으로 바꿈. 명암은 유지."""
    x0, y0, x1, y1 = op["box"]
    sub = np.ascontiguousarray(A[y0:y1, x0:x1])
    t = op.get("tol", 18)
    sx, sy = op["seed"]

    def fill(px, py):
        mk = np.zeros((sub.shape[0] + 2, sub.shape[1] + 2), np.uint8)
        cv2.floodFill(sub.copy(), mk, (px - x0, py - y0), (0, 0, 0), (t, t, t), (t, t, t),
                      4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
        mk[0, :] = mk[-1, :] = 0; mk[:, 0] = mk[:, -1] = 0
        return mk

    def touches(mk):
        inner = mk[1:-1, 1:-1] > 0
        return inner[0].any() or inner[-1].any() or inner[:, 0].any() or inner[:, -1].any()

    mask = fill(sx, sy)
    limit = 0.7 * sub.shape[0] * sub.shape[1]
    if op.get("closed", True) and touches(mask):
        mask = np.zeros_like(mask)
    if (mask > 0).sum() < 150:   # 씨앗이 외곽선 위면 근처에서 가장 넓게 칠해지는 점을 찾음
        best = mask
        r = op.get("search", 16)
        for py in range(sy - r, sy + r + 1, 3):
            for px in range(sx - r, sx + r + 1, 3):
                if not (x0 <= px < x1 and y0 <= py < y1) or A[py, px].max() < 90:
                    continue
                mk = fill(px, py)
                n = (mk > 0).sum()
                if (best > 0).sum() < n < limit and not (op.get("closed", True) and touches(mk)):
                    best = mk
        mask = best
    m = np.zeros(A.shape[:2], bool)
    m[y0:y1, x0:x1] = mask[1:-1, 1:-1] > 0
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
    src = A.astype(float)
    lum = src.mean(2, keepdims=True)
    ref = np.median(lum[m]) if m.any() else 1
    tgt = np.array(op["color"], float)
    E = np.clip(tgt * (lum / max(ref, 1)), 0, 255).astype(np.uint8)
    out = B.copy(); out[m] = E[m]
    return feather(B, out, m, 1), m


def do_erase_line(A, B, op):
    """상자 안의 검은 선(외곽선·주름·눈썹 조각 등)만 지우고 주변 바탕색으로 채움. mode=light 이면 밝은 하이라이트를 지움."""
    x0, y0, x1, y1 = op["box"]
    sub = A[y0:y1, x0:x1].astype(int)
    v = sub.max(2)
    if op.get("mode") == "light":
        line = (v > op.get("vmin", 235)) & ((sub.max(2) - sub.min(2)) < 30)
    else:
        line = v < op.get("vmax", 90)
    fill_px = sub[~line]
    if op.get("fill_vmin"):
        fill_px = fill_px[fill_px.max(-1) >= op["fill_vmin"]]
    if len(fill_px) == 0:
        return B, np.zeros(A.shape[:2], bool)
    col = np.median(fill_px.reshape(-1, 3), 0)
    m = np.zeros(A.shape[:2], bool)
    m[y0:y1, x0:x1] = line
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    keep = np.zeros_like(m); keep[y0:y1, x0:x1] = True
    m &= keep
    if op.get("fill") == "median":
        out = B.copy(); out[m] = col
    else:   # 주변 색을 자연스럽게 이어서 채움 (단색 면 위의 선에 적합)
        out = cv2.inpaint(np.ascontiguousarray(B), m.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA)
    return feather(B, out, m, 1), m


def do_flip(A, B, op):
    """상자 안 그림을 좌우(또는 상하) 뒤집기 – 머리카락 한 가닥, 주머니, 무늬 방향 등."""
    x0, y0, x1, y1 = op["box"]
    patch = B[y0:y1, x0:x1]
    patch = patch[::-1] if op.get("axis") == "v" else patch[:, ::-1]
    out = B.copy(); out[y0:y1, x0:x1] = patch
    m = np.zeros(A.shape[:2], bool); m[y0:y1, x0:x1] = np.abs(out[y0:y1, x0:x1].astype(int) - B[y0:y1, x0:x1]).sum(2) > 30
    return out, m


def do_copy(A, B, op):
    """작은 조각(src 상자)을 다른 위치(dst 좌상단)에 복사 – 단추 하나 추가, 줄무늬 하나 더 등."""
    x0, y0, x1, y1 = op["box"]
    dx, dy = op["dst"]
    patch = A[y0:y1, x0:x1]
    out = B.copy(); out[dy:dy + (y1 - y0), dx:dx + (x1 - x0)] = patch
    m = np.zeros(A.shape[:2], bool)
    m[dy:dy + (y1 - y0), dx:dx + (x1 - x0)] = np.abs(patch.astype(int) - B[dy:dy + (y1 - y0), dx:dx + (x1 - x0)]).sum(2) > 30
    return out, m


def run(folder, spec):
    A = np.asarray(Image.open(f"{folder}/base.png").convert("RGB"))
    B = A.copy(); ans = []
    for op in spec:
        B, m = {"hue": do_hue, "remove": do_remove, "tint": do_tint, "erase_line": do_erase_line, "flip": do_flip, "copy": do_copy}[op["type"]](A, B, op)
        ys, xs = np.nonzero(m)
        if len(xs) == 0:
            print("  ⚠ 바뀐 픽셀 없음:", op["label"]); continue
        cx, cy = op.get("center", (float(xs.mean()), float(ys.mean())))
        r = op.get("r", max(40.0, min(110.0, 0.6 * max(xs.max() - xs.min(), ys.max() - ys.min()))))
        ans.append({"label": op["label"], "x": cx, "y": cy, "r": r})
        print(f"  {op['label']}: {len(xs)}픽셀, 중심=({cx:.0f},{cy:.0f}) r={r:.0f}")
    Image.fromarray(B).save(f"{folder}/b.png")
    json.dump(ans, open(f"{folder}/answers.json", "w"), ensure_ascii=False, indent=1)
    # 확인용: 위 원본 / 아래 수정본 + 정답 원
    a, b = Image.fromarray(A), Image.fromarray(B)
    c = Image.new("RGB", (a.width, a.height * 2 + 10), "white"); c.paste(a, (0, 0)); c.paste(b, (0, a.height + 10))
    d = ImageDraw.Draw(c)
    for x in ans:
        for oy in (0, a.height + 10):
            d.ellipse((x["x"] - x["r"], oy + x["y"] - x["r"], x["x"] + x["r"], oy + x["y"] + x["r"]), outline="red", width=4)
    c.resize((c.width // 2, c.height // 2)).save(f"{folder}/check.png")


if __name__ == "__main__":
    run(sys.argv[1], json.load(open(sys.argv[2])))
