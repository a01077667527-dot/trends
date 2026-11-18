# '두뇌 건강 강화 프로젝트' 로고/배너: 머리띠 두르고 아령 든 뇌 캐릭터
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logo import brain, legs, INK, FONT

def strong_brain(cx, cy, s=1.0):
    o = ''
    # 팔 (뇌 뒤에서 위로 아령을 듦)
    for side in (-1, 1):
        o += f'<path d="M{cx+side*110*s} {cy+20*s} Q{cx+side*175*s} {cy-60*s} {cx+side*125*s} {cy-185*s}" fill="none" stroke="{INK}" stroke-width="{14*s}" stroke-linecap="round"/>'
    # 아령
    o += f'<rect x="{cx-170*s}" y="{cy-197*s}" width="{340*s}" height="{20*s}" rx="{10*s}" fill="#8a96a8" stroke="{INK}" stroke-width="{5*s}"/>'
    for side in (-1, 1):
        x = cx + side * 165 * s
        o += f'<rect x="{x-22*s}" y="{cy-245*s}" width="{44*s}" height="{116*s}" rx="{12*s}" fill="#3b5bdb" stroke="{INK}" stroke-width="{6*s}"/>'
        o += f'<rect x="{x-side*30*s-12*s}" y="{cy-228*s}" width="{24*s}" height="{82*s}" rx="{8*s}" fill="#5c7cfa" stroke="{INK}" stroke-width="{5*s}"/>'
    # 주먹
    for side in (-1, 1):
        o += f'<circle cx="{cx+side*125*s}" cy="{cy-187*s}" r="{17*s}" fill="#ffb3c1" stroke="{INK}" stroke-width="{5*s}"/>'
    o += legs(cx, cy, s) + brain(cx, cy, s)
    # 머리띠
    o += f'<path d="M{cx-150*s} {cy-48*s} Q{cx} {cy-78*s} {cx+150*s} {cy-48*s} L{cx+148*s} {cy-22*s} Q{cx} {cy-52*s} {cx-148*s} {cy-22*s}Z" fill="#e53935" stroke="{INK}" stroke-width="{5*s}"/>'
    o += f'<path d="M{cx+145*s} {cy-38*s} l{45*s} {-25*s} l{-5*s} {30*s}Z M{cx+145*s} {cy-36*s} l{50*s} {12*s} l{-22*s} {22*s}Z" fill="#e53935" stroke="{INK}" stroke-width="{5*s}" stroke-linejoin="round"/>'
    # 반짝이
    for x, y, r in ((-215, -110, 16), (225, 40, 13)):
        X, Y, R = cx + x * s, cy + y * s, r * s
        o += f'<path d="M{X} {Y-R*2} L{X+R*.5} {Y-R*.5} L{X+R*2} {Y} L{X+R*.5} {Y+R*.5} L{X} {Y+R*2} L{X-R*.5} {Y+R*.5} L{X-R*2} {Y} L{X-R*.5} {Y-R*.5}Z" fill="#ffd166"/>'
    return o

def svg(w, h, inner, bg="none"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="{bg}"/>{inner}</svg>'

# 로고 A: 캐릭터만
LA = svg(800, 800, '<circle cx="400" cy="400" r="380" fill="#ffe3a3"/>' + strong_brain(400, 440, 1.05), "#fff1d6")
# 로고 B: 캐릭터 + 글씨
LB = svg(800, 800, '<circle cx="400" cy="400" r="380" fill="#3f8f6a"/>' + strong_brain(400, 330, .78)
         + f'<text x="400" y="575" font-size="76" {FONT} fill="#ffe3a3">두뇌 건강</text>'
         + f'<text x="400" y="670" font-size="76" {FONT} fill="#fff">강화 프로젝트</text>', "#fff1d6")

# 배너 2560x1440 (안전영역 x507~2053, y508~932)
def cloud(x, y, s):
    return ''.join(f'<circle cx="{x+dx*s}" cy="{y+dy*s}" r="{r*s}" fill="#fff"/>' for dx, dy, r in [(0,0,50),(55,-20,60),(115,0,48),(55,15,50)])
bn = ['<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfeaff"/><stop offset="1" stop-color="#fff4dc"/></linearGradient></defs>',
      '<rect width="2560" height="1440" fill="url(#sky)"/>', '<circle cx="2250" cy="260" r="110" fill="#ffd166"/>',
      cloud(300, 250, 1.4), cloud(1500, 180, 1.1), cloud(1950, 400, .9),
      '<path d="M0 1000 Q700 860 1400 980 T2560 940 V1440 H0Z" fill="#7cc46a"/>',
      '<path d="M0 1080 Q900 980 1700 1060 T2560 1050 V1440 H0Z" fill="#9bd77a"/>',
      strong_brain(765, 728, .85),
      f'<text x="1500" y="660" font-size="92" {FONT} fill="{INK}">두뇌 건강 강화 프로젝트</text>',
      '<rect x="1130" y="705" width="740" height="96" rx="48" fill="#3f8f6a"/>',
      f'<text x="1500" y="772" font-size="56" {FONT} fill="#fff">틀린그림 찾기로 두뇌 운동</text>',
      f'<text x="1500" y="870" font-size="48" {FONT} fill="#6b5a4a">하루 1분 · 오늘도 함께 도전해요!</text>']
BN = svg(2560, 1440, ''.join(bn))
GUIDE = BN.replace('</svg>', '<rect x="507" y="508" width="1546" height="424" fill="none" stroke="red" stroke-width="6" stroke-dasharray="20 12"/></svg>')

here = os.path.dirname(os.path.abspath(__file__))
for n, s in (("logo_A", LA), ("logo_B", LB), ("banner", BN), ("banner_guide", GUIDE)):
    open(os.path.join(here, n + ".svg"), "w").write(s)
