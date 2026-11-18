"""숨은 단어 찾기(글자판) 생성기 – 쇼츠 세로(1080x1920) 문제/정답 이미지.

시니어용이라 가로(→)와 세로(↓)로만 숨김. 각 단어가 판 전체에서 정확히 1번만 나오도록 검사.

사용법:
  python3 wordsearch.py 과일 사과,바나나,포도,수박,딸기 out/ws_fruit [--size 6] [--seed 1]
"""
import json, os, random, sys
from PIL import Image, ImageDraw, ImageFont

FONT = next(p for p in ["/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
                        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"] if os.path.exists(p))
F = lambda s: ImageFont.truetype(FONT, s)
W, H = 1080, 1920
BG, INK, ORANGE, RED, GREEN = "#ffffff", "#222222", "#f08c00", "#e03131", "#2f9e44"
COLORS = ["#ffd43b", "#74c0fc", "#8ce99a", "#ffa8a8", "#d0bfff", "#ffc078", "#99e9f2", "#fcc2d7"]
# 채움 글자: 흔한 음절 (단어처럼 보여서 헷갈리게)
FILL = list("가나다라마바사아자차카타파하고노도로모보소오조초코토포호구누두루무부수우주추쿠투푸후"
            "기니디리미비시이지치키티피히강산물불길돌밤별꽃눈비해달문집손발인정성전대한민국")


def occurrences(grid, word):
    n = len(grid); c = 0
    for r in range(n):
        for col in range(n):
            for dr, dc in ((0, 1), (1, 0)):
                if all(0 <= r + dr * i < n and 0 <= col + dc * i < n and grid[r + dr * i][col + dc * i] == ch
                       for i, ch in enumerate(word)):
                    c += 1
    return c


def build(words, n, seed):
    rnd = random.Random(seed)
    for _ in range(2000):
        grid = [[None] * n for _ in range(n)]
        placed = []
        ok = True
        for w in sorted(words, key=len, reverse=True):
            spots = []
            for r in range(n):
                for c in range(n):
                    for dr, dc in ((0, 1), (1, 0)):
                        if r + dr * (len(w) - 1) >= n or c + dc * (len(w) - 1) >= n:
                            continue
                        if all(grid[r + dr * i][c + dc * i] in (None, ch) for i, ch in enumerate(w)):
                            spots.append((r, c, dr, dc))
            if not spots:
                ok = False; break
            r, c, dr, dc = rnd.choice(spots)
            for i, ch in enumerate(w):
                grid[r + dr * i][c + dc * i] = ch
            placed.append({"word": w, "cells": [[r + dr * i, c + dc * i] for i in range(len(w))]})
        if not ok:
            continue
        pool = [ch for ch in FILL if ch not in "".join(words)] + list("".join(words))  # 단어 글자도 섞어 헷갈리게
        for r in range(n):
            for c in range(n):
                if grid[r][c] is None:
                    grid[r][c] = rnd.choice(pool)
        if all(occurrences(grid, w) == 1 for w in words):
            placed.sort(key=lambda p: words.index(p["word"]))
            return grid, placed
    raise RuntimeError("배치 실패: 단어를 줄이거나 --size 를 키워보세요")


def draw_board(grid, placed=None, top=560):
    n = len(grid)
    cell = min(150, 980 // n)
    x0 = (W - cell * n) // 2
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    if placed:  # 정답: 단어 위에 둥근 색 띠
        for k, p in enumerate(placed):
            (r1, c1), (r2, c2) = p["cells"][0], p["cells"][-1]
            pad = 14
            d.rounded_rectangle((x0 + c1 * cell + pad, top + r1 * cell + pad,
                                 x0 + (c2 + 1) * cell - pad, top + (r2 + 1) * cell - pad),
                                cell // 2, fill=COLORS[k % len(COLORS)])
    for r in range(n):
        for c in range(n):
            x, y = x0 + c * cell, top + r * cell
            d.rectangle((x, y, x + cell, y + cell), outline=ORANGE, width=6)
            d.text((x + cell / 2, y + cell / 2 + 4), grid[r][c], font=F(int(cell * .58)), fill=INK, anchor="mm")
    d.rectangle((x0 - 4, top - 4, x0 + cell * n + 4, top + cell * n + 4), outline=ORANGE, width=12)
    return im, d, top + cell * n


def render(theme, words, out, n=6, seed=1):
    os.makedirs(out, exist_ok=True)
    grid, placed = build(words, n, seed)
    k = len(words)
    for name, ans in (("quiz", None), ("answer", placed)):
        im, d, bottom = draw_board(grid, ans)
        d.text((W // 2, 230), f"숨은 {theme} {k}개", font=F(110), fill=INK, anchor="mm")
        d.text((W // 2, 380), "찾아보세요!" if not ans else "정답 공개!", font=F(120),
               fill=RED if not ans else GREEN, anchor="mm")
        d.text((W // 2, 480), "가로(→) 세로(↓)로 숨어 있어요", font=F(46), fill="#868e96", anchor="mm")
        if ans:
            x = 90; y = bottom + 90
            for i, p in enumerate(placed):  # 정답 단어 목록 (색 칩)
                tw = d.textlength(p["word"], font=F(56)) + 60
                if x + tw > W - 90:
                    x = 90; y += 100
                d.rounded_rectangle((x, y - 40, x + tw, y + 40), 40, fill=COLORS[i % len(COLORS)])
                d.text((x + tw / 2, y), p["word"], font=F(56), fill=INK, anchor="mm")
                x += tw + 24
        else:
            d.text((W // 2, bottom + 100), f"{k}개 다 찾으면 두뇌 건강 합격! 👍".replace(" 👍", ""),
                   font=F(56), fill=INK, anchor="mm")
        im.save(f"{out}/{name}.png")
    json.dump({"theme": theme, "grid": grid, "answers": placed}, open(f"{out}/puzzle.json", "w"),
              ensure_ascii=False, indent=1)
    print("완료:", out, [p["word"] for p in placed])


if __name__ == "__main__":
    a = sys.argv[1:]
    size = int(a[a.index("--size") + 1]) if "--size" in a else 6
    seed = int(a[a.index("--seed") + 1]) if "--seed" in a else 1
    render(a[0], a[1].split(","), a[2], size, seed)
