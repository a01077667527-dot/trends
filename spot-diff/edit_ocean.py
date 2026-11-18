"""바닷속 그림 틀린그림 3곳: 문어 색, 해파리 하나 사라짐, 잠수부 오리발 색."""
import json
import numpy as np
from PIL import Image
from edit_image import hue_mask, shift_hue, feather

def erase_rect(a, x0, y0, x1, y1):
    """사각 영역을 좌우 바깥 물색(별·거품 무시한 중간값)으로 보간해 지움."""
    out = a.astype(float).copy()
    for y in range(y0, y1):
        L = np.median(a[y - 3:y + 4, x0 - 10:x0 - 2].reshape(-1, 3), 0)
        R = np.median(a[y - 3:y + 4, x1 + 2:x1 + 10].reshape(-1, 3), 0)
        for x in range(x0, x1):
            t = (x - x0) / (x1 - x0)
            out[y, x] = L * (1 - t) + R * t
    return out.astype(np.uint8)

folder = "out/ocean"
A = np.asarray(Image.open(f"{folder}/base.png").convert("RGB"))
B = A.copy(); ans = []

# 1) 빨간 문어 → 보라 문어
box = (512, 412, 698, 562)
m = hue_mask(A, box, 0, 22, 0.4) | hue_mask(A, box, 338, 360, 0.4)
B = feather(B, shift_hue(B, m, -85, sat=0.85), m, 1)
ans.append({"label": "문어 색", "x": 605, "y": 485, "r": 85})

# 2) 왼쪽 아래 해파리 사라짐
import cv2
mm = np.zeros(A.shape[:2], np.uint8)
mm[84:172, 726:779] = 1
mm[122:168, 779:793] = 1          # 옆으로 흘러간 다리
E = cv2.inpaint(np.ascontiguousarray(B), mm * 255, 9, cv2.INPAINT_TELEA)
B = feather(B, E, mm.astype(bool), 3)
ans.append({"label": "해파리 하나", "x": 752, "y": 140, "r": 45})

# 3) 노란 오리발 → 빨간 오리발
m = hue_mask(A, (772, 175, 862, 262), 33, 68, 0.35)
B = feather(B, shift_hue(B, m, -48, sat=1.0, light=0.9), m, 1)
ans.append({"label": "오리발 색", "x": 808, "y": 210, "r": 42})

Image.fromarray(B).save(f"{folder}/b.png")
json.dump(ans, open(f"{folder}/answers.json", "w"), ensure_ascii=False, indent=1)
print("완료", [a["label"] for a in ans])
