"""그림 속 글자 지우기 (원본 자체를 수정 → 비교 그림 양쪽 모두에서 사라짐). 좌표는 1200px 원본 기준."""
import sys, cv2, numpy as np
from PIL import Image
S = 1024 / 1200
JOBS = {
 "Q5":  [((950, 175, 1035, 210), "fill")],
 "Q8":  [((622, 550, 682, 580), "dark"), ((272, 655, 345, 690), "dark"), ((325, 765, 400, 805), "dark"),
         ((400, 780, 455, 815), "dark"), ((1072, 755, 1135, 790), "dark"), ((1030, 803, 1090, 840), "dark"),
         ((735, 843, 795, 880), "dark")],
 "Q10": [((0, 0, 140, 205), "dark"), ((180, 0, 355, 205), "dark"), ((1100, 40, 1200, 300), "dark")],
 "Q7":  [((0, 255, 110, 300), "dark")],
}
for name, boxes in JOBS.items():
    p = f"out/{name}/base.png"
    a = np.asarray(Image.open(p).convert("RGB")).copy()
    m = np.zeros(a.shape[:2], np.uint8)
    for (x0, y0, x1, y1), mode in boxes:
        x0, y0, x1, y1 = [int(v * S) for v in (x0, y0, x1, y1)]
        if mode == "fill":
            m[y0:y1, x0:x1] = 1
        else:
            sub = a[y0:y1, x0:x1].max(2)
            m[y0:y1, x0:x1] |= (sub < 120).astype(np.uint8)
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    a = cv2.inpaint(np.ascontiguousarray(a), m * 255, 5, cv2.INPAINT_TELEA)
    Image.fromarray(a).save(p)
    print(name, "지운 픽셀", int(m.sum()))
