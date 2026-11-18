# 유튜브 채널 배너 2560x1440. 핵심 요소는 안전영역(1546x423, 가운데) 안에.
from logo import brain, legs, INK, FONT
SX, SY, SW, SH = 507, 508, 1546, 424
def cloud(x, y, s):
    return ''.join(f'<circle cx="{x+dx*s}" cy="{y+dy*s}" r="{r*s}" fill="#fff"/>' for dx,dy,r in [(0,0,50),(55,-20,60),(115,0,48),(55,15,50)])
def tulip(x, y, c):
    return (f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+70}" stroke="#3f8f6a" stroke-width="8"/>'
            f'<path d="M{x-24} {y-30} L{x-12} {y-5} L{x} {y-30} L{x+12} {y-5} L{x+24} {y-30} Q{x+26} {y+10} {x} {y+12} Q{x-26} {y+10} {x-24} {y-30}Z" fill="{c}" stroke="{INK}" stroke-width="5"/>')
s = ['<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfeaff"/><stop offset="1" stop-color="#fff4dc"/></linearGradient></defs>',
     '<rect width="2560" height="1440" fill="url(#sky)"/>',
     '<circle cx="2250" cy="260" r="110" fill="#ffd166"/>',
     cloud(300, 250, 1.4), cloud(1500, 180, 1.1), cloud(1900, 420, .9),
     '<path d="M0 1000 Q700 860 1400 980 T2560 940 V1440 H0Z" fill="#7cc46a"/>',
     '<path d="M0 1080 Q900 980 1700 1060 T2560 1050 V1440 H0Z" fill="#9bd77a"/>',
     '<path d="M560 1440 Q680 1150 760 980 Q860 1150 1060 1440Z" fill="#f3d9a4"/>']
s += [tulip(x, 1150 + (i % 2) * 40, c) for i, (x, c) in enumerate([(1250,"#ff8fa3"),(1340,"#ffd166"),(1430,"#ff8fa3"),(1900,"#ffb3c1"),(1990,"#ff8fa3"),(2080,"#ffd166"),(2170,"#ffb3c1")])]
# 캐릭터 (안전영역 왼쪽)
s += [legs(720, 670, .82), brain(720, 670, .82)]
s += [f'<circle cx="855" cy="690" r="48" fill="#ffffffaa" stroke="{INK}" stroke-width="13"/>',
      f'<line x1="890" y1="725" x2="935" y2="770" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>']
# 글씨 (안전영역 오른쪽)
s += [f'<text x="1470" y="680" font-size="140" {FONT} fill="{INK}">매일 두뇌 산책</text>',
      f'<rect x="1100" y="725" width="740" height="96" rx="48" fill="#3f8f6a"/>',
      f'<text x="1470" y="792" font-size="56" {FONT} fill="#fff">틀린그림 찾기로 두뇌 운동</text>',
      f'<text x="1470" y="895" font-size="48" {FONT} fill="#6b5a4a">천천히, 즐겁게 · 오늘도 함께 걸어요</text>']
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2560 1440" width="2560" height="1440">{"".join(s)}</svg>'
open("banner.svg", "w").write(svg)
guide = svg.replace("</svg>", f'<rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" fill="none" stroke="red" stroke-width="6" stroke-dasharray="20 12"/></svg>')
open("banner_guide.svg", "w").write(guide)
