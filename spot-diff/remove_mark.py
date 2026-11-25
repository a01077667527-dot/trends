"""제미나이 별 표시(오른쪽 아래) 제거 – 번짐 없는 '반투명 흰색 역계산' 방식.
그림 크기별(A: 1024 원본, B: 1200→1024, C: 2000→1024, D: 1024x687) 별 모양을 미리 측정해 두고,
그림마다 위치(±3px)와 진하기를 맞춘 뒤 '원래 색 = (보이는 색 - 흰색×투명도) / (1-투명도)'로 되돌림.
덧칠·뭉개기를 하지 않으므로 별 밑의 선과 무늬가 그대로 살아남음.
사용법: python3 remove_mark.py A out/W1 out/W2 ...   (base.png 수정, 처음 원본은 base_orig.png 보관)"""
import sys, os, json
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
WIN = json.load(open(os.path.join(HERE, "mark_windows.json")))


def ideal(c):
    """측정한 투명도에서 별 부분만 남김(안티에일리어싱 가장자리 값은 그대로 사용)"""
    al = np.load(os.path.join(HERE, f"mark_{c}.npy")).astype(np.float32)
    h, w = al.shape
    lab, _ = ndimage.label(al > 0.12)
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    star = ndimage.binary_fill_holes(lab == sizes.argmax())
    keep = cv2.dilate(star.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    out = np.where(keep, al, 0)
    out[star] = np.maximum(out[star], 0)
    return out


def unblend(reg, A):
    A = np.clip(A, 0, 0.92)[..., None]
    return np.clip((reg - A * 255) / (1 - A), 0, 255)


def roughness(img, ring):
    g = cv2.Laplacian(img.mean(2).astype(np.float32), cv2.CV_32F)
    return np.abs(g)[ring].mean()


def hp(x, sg=3):
    x = x.astype(np.float32)
    return x - cv2.GaussianBlur(x, (0, 0), sg)


def clean(c, folder):
    p, o = f"{folder}/base.png", f"{folder}/base_orig.png"
    if not os.path.exists(o):
        Image.open(p).save(o)
    cur = np.asarray(Image.open(p).convert("RGB")).astype(float)
    x0, y0, x1, y1 = WIN[c]
    A0 = ideal(c)
    h, w = A0.shape
    core = cv2.erode((A0 > .05).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    reg = cur[y0:y0 + h, x0:x0 + w]
    best = None
    for k in np.arange(0.85, 1.16, 0.05):     # 진하기는 미세하게만 조정, 위치는 고정
        u = hp(unblend(reg, A0 * k).mean(2), 4)
        ghost = abs(float(u[core].mean()))
        if best is None or ghost < best[0]:
            best = (ghost, k)
    k = best[1]
    u = unblend(reg, A0 * k).astype(np.uint8)
    # 별 가장자리 띠에 남는 자잘한 점을 중간값으로 정리 (굵은 선은 유지됨)
    band = (A0 > 0.01).astype(np.uint8)
    band = (cv2.dilate(band, np.ones((3, 3), np.uint8)) - cv2.erode(band, np.ones((5, 5), np.uint8))).astype(bool)
    med = cv2.medianBlur(cv2.medianBlur(u, 3), 3)
    u[band] = med[band]
    cur[y0:y0 + h, x0:x0 + w] = u
    Image.fromarray(cur.astype(np.uint8)).save(p)
    print(f"{folder}: 제거 (진하기 {k:.2f})")
    return True


if __name__ == "__main__":
    c = sys.argv[1]
    for f in sys.argv[2:]:
        clean(c, f)
