"""16:9(1024x572) 그림의 작은 별 표시 제거: 큰 별 모양(B)을 줄여 크기·위치·진하기를 맞춘 뒤 역계산."""
import sys, os
import numpy as np, cv2
from PIL import Image
import remove_mark as RM

A70 = RM.ideal("B")


def fit(cur, cx, cy):
    best = None
    for sc in np.arange(0.4, 0.86, 0.03):
        t = cv2.resize(A70, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        h, w = t.shape
        core = cv2.erode((t > .03).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        ring = cv2.dilate((t > .01).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~(t > .01)
        for dy in range(-4, 5, 2):
            for dx in range(-4, 5, 2):
                x0, y0 = int(cx + dx - w / 2), int(cy + dy - h / 2)
                reg = cur[y0:y0 + h, x0:x0 + w]
                for k in np.arange(0.2, 1.6, 0.05):
                    u = RM.unblend(reg, t * k).mean(2)
                    ghost = abs(u[core].mean() - u[ring].mean()) + 0.5 * u[core].std()
                    if best is None or ghost < best[0]:
                        best = (ghost, sc, dx, dy, k, x0, y0, t)
    return best


if __name__ == "__main__":
    for f in sys.argv[1:]:
        p, o = f"{f}/base.png", f"{f}/base_orig.png"
        cur = np.asarray(Image.open(o).convert("RGB")).astype(float)
        g, sc, dx, dy, k, x0, y0, t = fit(cur, 934, 484)
        h, w = t.shape
        cur[y0:y0 + h, x0:x0 + w] = RM.unblend(cur[y0:y0 + h, x0:x0 + w], t * k)
        Image.fromarray(cur.astype(np.uint8)).save(p)
        print(f, f"크기 {sc:.2f} 위치 {dx:+d},{dy:+d} 진하기 {k:.2f}")
