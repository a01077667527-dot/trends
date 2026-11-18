"""우주 그림 틀린그림 3곳: 별 풍선 색, 보라 행성 색, 작은 소행성 사라짐."""
import json
import cv2
import numpy as np
from PIL import Image
from edit_image import hue_mask, shift_hue, feather

folder = "out/space"
A = np.asarray(Image.open(f"{folder}/base.png").convert("RGB"))
B = A.copy(); ans = []

# 1) 노란 별 풍선 → 분홍 별 풍선
m = hue_mask(A, (330, 45, 445, 150), 30, 65, 0.4)
B = feather(B, shift_hue(B, m, 295, sat=0.9), m, 1)
ans.append({"label": "풍선 색", "x": 388, "y": 97, "r": 58})

# 2) 보라 행성 → 초록 행성 (옆 구름은 색이 달라 제외됨)
m = hue_mask(A, (558, 25, 720, 128), 252, 335, 0.15)
B = feather(B, shift_hue(B, m, -150, sat=0.9), m, 1)
ans.append({"label": "행성 색", "x": 640, "y": 76, "r": 72})

# 3) 작은 소행성 사라짐 — 밤하늘이 아닌 덩어리 중 소행성만 골라 하늘색으로
sky = np.median(A[300:440, 300:440].reshape(-1, 3), 0)
far = (np.abs(A.astype(int) - sky).sum(2) > 45).astype(np.uint8)
_, lab, st, _ = cv2.connectedComponentsWithStats(far, connectivity=8)
k = lab[378, 352]; print("소행성 덩어리:", st[k])
blob = cv2.dilate((lab == k).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
ring = cv2.dilate(blob.astype(np.uint8), np.ones((21, 21), np.uint8)).astype(bool) & ~blob & (far == 0)
E = B.copy(); E[blob] = np.median(A[ring], 0)
B = feather(B, E, blob, 1)
ys, xs = np.nonzero(blob)
ans.append({"label": "소행성 사라짐", "x": float(xs.mean()), "y": float(ys.mean()), "r": 48})

Image.fromarray(B).save(f"{folder}/b.png")
json.dump(ans, open(f"{folder}/answers.json", "w"), ensure_ascii=False, indent=1)
print("완료", [a["label"] for a in ans])
