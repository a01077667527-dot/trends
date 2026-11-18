"""캠핑장2 그림 틀린그림 3곳: 강아지 사라짐, 여자 점퍼 색, 앞쪽 그루터기 사라짐."""
import json
import cv2
import numpy as np
from PIL import Image
from edit_image import hue_mask, shift_hue, feather

folder = "out/camping3"
A = np.asarray(Image.open(f"{folder}/base.png").convert("RGB"))
B = A.copy(); ans = []
green = hue_mask(A, (0, 0, A.shape[1], A.shape[0]), 70, 160, 0.15)

def remove(B, box, top_limit=None):
    """상자 안(텐트 아래)을 주변 잔디색 한 가지로 채움 – 이 그림은 잔디가 단색이라 가장 깔끔."""
    x0, y0, x1, y1 = box
    m = np.zeros(A.shape[:2], bool)
    m[y0:y1, x0:x1] = True
    if top_limit is not None:
        for x in range(x0, x1):
            m[:top_limit(x), x] = False
    ring = np.zeros_like(m); ring[y0 - 12:y1 + 12, x0 - 12:x1 + 12] = True; ring &= ~m & green
    col = np.median(A[ring], 0)
    E = B.copy(); E[m] = col
    return feather(B, E, m, 2)

# 1) 강아지 사라짐 — 잔디가 아닌 덩어리 중 강아지가 속한 것만 골라 잔디색으로 채움 (텐트는 별도 덩어리라 안전)
ng = (~green).astype(np.uint8); ng[:, :220] = 0; ng[:, 380:] = 0; ng[:395] = 0; ng[515:] = 0
_, lab, _, _ = cv2.connectedComponentsWithStats(ng, connectivity=8)
dog = cv2.dilate((lab == lab[470, 300]).astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
ring = cv2.dilate(dog.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) & ~dog & green
E = B.copy(); E[dog] = np.median(A[ring], 0)
B = feather(B, E, dog, 1)
ans.append({"label": "강아지 사라짐", "x": 300, "y": 467, "r": 72})

# 2) 주황 점퍼 → 보라 점퍼
m = hue_mask(A, (783, 300, 888, 395), 12, 40, 0.55)
B = feather(B, shift_hue(B, m, 245, sat=0.75), m, 1)
ans.append({"label": "점퍼 색", "x": 835, "y": 345, "r": 62})

# 3) 앞쪽 가운데 그루터기 사라짐
B = remove(B, (526, 456, 614, 540))
ans.append({"label": "그루터기 사라짐", "x": 570, "y": 497, "r": 58})

Image.fromarray(B).save(f"{folder}/b.png")
json.dump(ans, open(f"{folder}/answers.json", "w"), ensure_ascii=False, indent=1)
print("완료", [a["label"] for a in ans])
