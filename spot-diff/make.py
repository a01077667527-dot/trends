# 코드로 그리는 틀린그림찾기 생성기: 같은 장면 함수에 '차이점 키'만 넣어 B를 만든다
import json, sys
O = 'stroke="#2b2b2b" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"'
STARS = [(80,70),(190,140),(300,60),(420,110),(620,70),(700,160),(560,190),(950,230),(130,250),(760,60)]
DIFFS = {  # 키: (설명, 정답 원 위치 x,y,r)
 'star':   ('별 하나 사라짐', 700,160,40),
 'flag':   ('깃발 색',       525,140,45),
 'ribbon': ('고양이 리본',    680,470,50),
 'mug':    ('머그컵 색',     880,560,50),
 'marsh':  ('마시멜로 개수',  330,585,65),
}
def scene(d):
    s = []
    s.append('<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b1f4b"/><stop offset="1" stop-color="#3d4796"/></linearGradient></defs>')
    s.append('<rect width="1000" height="750" fill="url(#sky)"/>')
    for i,(x,y) in enumerate(STARS):
        if 'star' in d and (x,y)==(700,160): continue
        s.append(f'<path d="M{x} {y-12} L{x+4} {y-4} L{x+12} {y} L{x+4} {y+4} L{x} {y+12} L{x-4} {y+4} L{x-12} {y} L{x-4} {y-4}Z" fill="#ffe680"/>')
    s.append('<circle cx="880" cy="110" r="55" fill="#fff4c2"/><circle cx="860" cy="95" r="10" fill="#efe0a0"/><circle cx="900" cy="130" r="7" fill="#efe0a0"/>')
    s.append('<path d="M0 470 Q250 400 500 450 T1000 430 V750 H0Z" fill="#4f8f5a"/>')
    s.append('<path d="M0 500 Q300 460 600 490 T1000 480 V750 H0Z" fill="#9bd77a"/>')
    # 나무
    for tx in (70, 950):
        s.append(f'<rect x="{tx-12}" y="380" width="24" height="120" fill="#8a5a3b" {O}/>')
        for k,(w,y) in enumerate([(90,260),(110,320),(130,380)]):
            s.append(f'<polygon points="{tx},{y-80} {tx-w/2*1.0},{y+20} {tx+w/2},{y+20}" fill="#3f9d5d" {O}/>')
    # 텐트 + 깃발
    s.append(f'<polygon points="330,500 500,190 670,500" fill="#7fd6a4" {O}/>')
    s.append(f'<polygon points="500,260 445,500 555,500" fill="#2f5e44" {O}/>')
    s.append(f'<line x1="500" y1="190" x2="500" y2="120" {O}/>')
    fc = '#3b82f6' if 'flag' in d else '#ef4444'
    s.append(f'<polygon points="500,120 555,137 500,154" fill="{fc}" {O}/>')
    # 전구 줄
    s.append('<path d="M70 300 Q280 380 420 330" fill="none" stroke="#2b2b2b" stroke-width="3"/>')
    for i,(x,y) in enumerate([(120,322),(180,342),(240,352),(300,350),(360,342)]):
        c = ['#ffd84d','#ff8fb1','#8fd3ff'][i%3]
        s.append(f'<circle cx="{x}" cy="{y+10}" r="11" fill="{c}" stroke="#2b2b2b" stroke-width="3"/>')
    # 모닥불
    s.append(f'<rect x="150" y="625" width="130" height="22" rx="10" fill="#8a5a3b" transform="rotate(15 215 636)" {O}/>')
    s.append(f'<rect x="150" y="625" width="130" height="22" rx="10" fill="#a0693f" transform="rotate(-15 215 636)" {O}/>')
    s.append(f'<path d="M215 520 Q260 580 245 620 Q215 640 185 620 Q170 580 215 520Z" fill="#ff7a3d" {O}/>')
    s.append('<path d="M215 565 Q238 595 228 618 Q215 628 202 618 Q195 595 215 565Z" fill="#ffd84d"/>')
    # 마시멜로 꼬치
    s.append(f'<line x1="400" y1="640" x2="270" y2="540" stroke="#8a5a3b" stroke-width="7" stroke-linecap="round"/>')
    n = 3 if 'marsh' in d else 2
    for k in range(n):
        x, y = 290 + k*30, 556 + k*23
        s.append(f'<rect x="{x-13}" y="{y-13}" width="26" height="26" rx="7" fill="#fff8ee" transform="rotate(-38 {x} {y})" stroke="#2b2b2b" stroke-width="4"/>')
    # 고양이
    cx, cy = 690, 580
    s.append(f'<ellipse cx="{cx}" cy="{cy+60}" rx="75" ry="55" fill="#f6c48b" {O}/>')
    s.append(f'<polygon points="{cx-55},{cy-35} {cx-45},{cy-100} {cx-10},{cy-55}" fill="#f6c48b" {O}/>')
    s.append(f'<polygon points="{cx+55},{cy-35} {cx+45},{cy-100} {cx+10},{cy-55}" fill="#f6c48b" {O}/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="65" fill="#f6c48b" {O}/>')
    s.append(f'<path d="M{cx-35} {cy-5} q10 -12 20 0 M{cx+15} {cy-5} q10 -12 20 0" fill="none" {O}/>')
    s.append(f'<circle cx="{cx-40}" cy="{cy+20}" r="11" fill="#ff9fb0"/><circle cx="{cx+40}" cy="{cy+20}" r="11" fill="#ff9fb0"/>')
    s.append(f'<path d="M{cx-8} {cy+15} q8 10 16 0" fill="none" {O}/>')
    if 'ribbon' in d:
        rx, ry = cx-15, cy-85
        s.append(f'<polygon points="{rx},{ry} {rx-30},{ry-18} {rx-30},{ry+18}" fill="#ff6fa3" {O}/>')
        s.append(f'<polygon points="{rx},{ry} {rx+30},{ry-18} {rx+30},{ry+18}" fill="#ff6fa3" {O}/>')
        s.append(f'<circle cx="{rx}" cy="{ry}" r="9" fill="#ff6fa3" {O}/>')
    # 그루터기 + 머그
    s.append(f'<path d="M820 650 L830 600 H930 L940 650Z" fill="#a0693f" {O}/><ellipse cx="880" cy="600" rx="50" ry="14" fill="#e3b07a" {O}/>')
    mc = '#f2c94c' if 'mug' in d else '#e85d75'
    s.append(f'<path d="M905 555 q22 0 22 18 q0 18 -22 18" fill="none" {O}/><rect x="855" y="540" width="50" height="58" rx="8" fill="{mc}" {O}/>')
    s.append('<path d="M870 525 q-8 -12 0 -24 M890 525 q-8 -12 0 -24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".8"/>')
    # 덤불
    for bx in (40, 120, 520, 600, 980):
        s.append(f'<circle cx="{bx}" cy="735" r="45" fill="#3f9d5d" {O}/><circle cx="{bx+40}" cy="745" r="38" fill="#4fae6b" {O}/>')
    return ''.join(s)

def svg(d, answers=False):
    extra = ''
    if answers:
        for k in DIFFS:
            _,x,y,r = DIFFS[k]
            extra += f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#ff2d55" stroke-width="9"/>'
    return f'<svg viewBox="0 0 1000 750" width="1000" height="750">{scene(d)}{extra}</svg>'

def page(title, a, b, foot):
    return f'''<html><body style="margin:0;width:1080px;height:1920px;background:#fff3dc;font-family:'WenQuanYi Zen Hei';display:flex;flex-direction:column;align-items:center">
<div style="height:200px;display:flex;flex-direction:column;justify-content:center;align-items:center"><div style="font-size:72px;font-weight:bold;color:#2b2b2b">{title}</div></div>
<div style="border-radius:28px;overflow:hidden;border:8px solid #2b2b2b;line-height:0">{a}</div>
<div style="height:40px"></div>
<div style="border-radius:28px;overflow:hidden;border:8px solid #2b2b2b;line-height:0">{b}</div>
<div style="flex:1;display:flex;align-items:center;font-size:40px;color:#555;padding:0 40px;text-align:center">{foot}</div></body></html>'''

allk = set(DIFFS)
open('quiz.html','w').write(page('틀린 곳 5개를 찾아보세요! 👀', svg(set()), svg(allk), '상위 1%만 다 찾아요 · 몇 개 찾으셨나요?'))
open('answer.html','w').write(page('정답 공개!', svg(set()), svg(allk, True), '・'.join(v[0] for v in DIFFS.values())))
