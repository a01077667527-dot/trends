# '매일 두뇌 산책' 채널 로고 3종 (800x800, 원형 크롭 안전영역 고려)
INK = "#3a2a2a"
def brain(cx, cy, s=1.0, look=None):
    # 원 여러 개의 합집합으로 몽글몽글한 뇌 실루엣 → 외곽선층 + 채움층
    blobs = [(-95,-20,75),(-45,-75,80),(40,-80,82),(100,-25,72),(80,45,70),(0,40,85),(-80,45,68)]
    c = lambda x,y,r,extra: f'<circle cx="{cx+x*s}" cy="{cy+y*s}" r="{r*s}" {extra}/>'
    out = ''.join(c(x,y,r+7,f'fill="{INK}"') for x,y,r in blobs)
    out += ''.join(c(x,y,r,'fill="#ffb3c1"') for x,y,r in blobs)
    sw = 7*s
    folds = [f"M{cx} {cy-140*s} Q{cx-12*s} {cy-60*s} {cx} {cy+10*s}",
             f"M{cx-120*s} {cy-30*s} q30 -25 55 0", f"M{cx-70*s} {cy-100*s} q20 25 45 5",
             f"M{cx+60*s} {cy-110*s} q-10 30 20 45", f"M{cx+125*s} {cy-20*s} q-30 -10 -45 15"]
    out += ''.join(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" opacity=".55"/>' for d in folds)
    # 얼굴
    ey = cy+25*s
    out += f'<circle cx="{cx-40*s}" cy="{ey}" r="{11*s}" fill="{INK}"/><circle cx="{cx+40*s}" cy="{ey}" r="{11*s}" fill="{INK}"/>'
    out += f'<circle cx="{cx-36*s}" cy="{ey-4*s}" r="{4*s}" fill="#fff"/><circle cx="{cx+44*s}" cy="{ey-4*s}" r="{4*s}" fill="#fff"/>'
    out += f'<ellipse cx="{cx-72*s}" cy="{ey+22*s}" rx="{17*s}" ry="{11*s}" fill="#ff7f98" opacity=".7"/><ellipse cx="{cx+72*s}" cy="{ey+22*s}" rx="{17*s}" ry="{11*s}" fill="#ff7f98" opacity=".7"/>'
    out += f'<path d="M{cx-22*s} {ey+28*s} q{22*s} {24*s} {44*s} 0" fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>'
    return out

def legs(cx, cy, s=1.0):
    sw = 12*s
    o = f'<path d="M{cx-35*s} {cy+110*s} l-18 {60*s}" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>'
    o += f'<path d="M{cx+35*s} {cy+110*s} l22 {55*s}" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>'
    o += f'<ellipse cx="{cx-62*s}" cy="{cy+175*s}" rx="{30*s}" ry="{16*s}" fill="#4f8ef7" stroke="{INK}" stroke-width="{6*s}"/>'
    o += f'<ellipse cx="{cx+68*s}" cy="{cy+170*s}" rx="{30*s}" ry="{16*s}" fill="#4f8ef7" stroke="{INK}" stroke-width="{6*s}"/>'
    return o

def frame(inner, bg="#fff1d6"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="800" height="800"><rect width="800" height="800" fill="{bg}"/>{inner}</svg>'

FONT = "font-family=\"'WenQuanYi Zen Hei'\" font-weight=\"bold\" text-anchor=\"middle\""

# A: 산책하는 뇌 캐릭터 (글자 없음 - 작게 봐도 또렷)
A = frame(
    '<circle cx="610" cy="190" r="60" fill="#ffd166"/>'
    '<path d="M0 600 Q400 500 800 600 V800 H0Z" fill="#9bd77a"/>'
    '<path d="M250 800 Q350 640 420 560 Q470 640 560 800Z" fill="#f3d9a4"/>'
    + legs(400, 360) + brain(400, 360))

# B: 돋보기 든 뇌 + '두뇌산책' 글씨
B = frame(
    '<circle cx="400" cy="400" r="370" fill="#ffe3a3"/>'
    + legs(400, 300, .85) + brain(400, 300, .85)
    + f'<circle cx="560" cy="330" r="62" fill="#ffffffaa" stroke="{INK}" stroke-width="14"/>'
    + f'<line x1="605" y1="375" x2="660" y2="430" stroke="{INK}" stroke-width="20" stroke-linecap="round"/>'
    + f'<text x="400" y="640" font-size="112" {FONT} fill="{INK}">두뇌산책</text>')

# C: 글씨 중심 배지
C = frame(
    '<circle cx="400" cy="400" r="380" fill="#3f8f6a"/>'
    '<circle cx="400" cy="400" r="345" fill="none" stroke="#fff1d6" stroke-width="8" stroke-dasharray="4 22" stroke-linecap="round"/>'
    + brain(400, 300, .72)
    + f'<text x="400" y="535" font-size="64" {FONT} fill="#ffe3a3">매일</text>'
    + f'<text x="400" y="650" font-size="120" {FONT} fill="#fff">두뇌산책</text>', bg="#fff1d6")

for n, s in (("logo_A", A), ("logo_B", B), ("logo_C", C)):
    open(n + ".svg", "w").write(s)
# 비교용: 원형 크롭 미리보기 (큰 것 + 실제 표시 크기 88px)
cards = ''.join(f'<div style="text-align:center;margin:20px"><img src="{n}.svg" style="width:300px;height:300px;border-radius:50%;display:block"/>'
                f'<img src="{n}.svg" style="width:88px;height:88px;border-radius:50%;margin-top:14px"/>'
                f'<img src="{n}.svg" style="width:36px;height:36px;border-radius:50%;margin-left:10px"/>'
                f'<div style="font:bold 40px sans-serif;margin-top:6px">{n[-1]}</div></div>' for n in ("logo_A","logo_B","logo_C"))
open("preview.html","w").write(f'<html><body style="margin:0;background:#fff;display:flex;padding:10px">{cards}</body></html>')
