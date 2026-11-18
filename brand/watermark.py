# 유튜브 동영상 워터마크 (정사각, 투명 배경). 오른쪽 아래 작게 뜨므로 단순하게.
from logo import brain, legs, INK, FONT
def wm(inner):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600">{inner}</svg>'
# 1) 캐릭터 배지
A = wm('<circle cx="300" cy="300" r="285" fill="#ffe3a3" stroke="#fff" stroke-width="18"/>'
       + legs(300, 250, 1.05) + brain(300, 250, 1.05))
# 2) 캐릭터 + '구독' 리본
B = wm('<circle cx="300" cy="300" r="285" fill="#ffe3a3" stroke="#fff" stroke-width="18"/>'
       + brain(300, 250, 1.1)
       + '<rect x="95" y="400" width="410" height="130" rx="65" fill="#e53935" stroke="#fff" stroke-width="12"/>'
       + f'<text x="300" y="495" font-size="96" {FONT} fill="#fff">구독</text>')
open("watermark_A.svg","w").write(A); open("watermark_B.svg","w").write(B)
