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


def run(folder, spec):
    A = np.asarray(Image.open(f"{folder}/base.png").convert("RGB"))
    B = A.copy(); ans = []
    for op in spec:
        B, m = (do_hue if op["type"] == "hue" else do_remove)(A, B, op)
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
