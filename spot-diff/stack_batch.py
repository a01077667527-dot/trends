"""L1~L10 그림으로 위아래 쇼츠 10편 일괄 제작 → out/stack/N_장면.mp4 + 정답 이미지 + 고정 댓글 + 제목"""
import os, shutil
from concurrent.futures import ProcessPoolExecutor
from shorts_stack import render

NAMES = ["시골마당", "과일가게", "김장", "구멍가게", "명절", "텃밭", "벚꽃나들이", "옛날교실", "이발소", "바닷가"]
EMO = ["🏡", "🍎", "🥬", "🏪", "🎑", "🌶️", "🌸", "🏫", "💈", "🏖️"]
TITLES = [
    "30초 안에 3곳 찾으면 눈썰미 상위 1%! {e}",
    "어디가 달라졌을까? 끝까지 못 찾는 사람 많아요 {e}",
    "3곳 다 찾으면 두뇌 나이 30대! {e}",
    "마지막 하나에서 다들 막힙니다 {e}",
]
DESC = """🧠 두뇌 건강 강화 프로젝트 – {n} 편

위아래 두 그림에서 다른 곳 3군데를 찾아보세요!
정답은 고정 댓글에 있어요 😊

#틀린그림찾기 #다른그림찾기 #두뇌운동 #집중력 #두뇌게임 #뇌건강 #shorts"""

def job(i):
    os.makedirs("out/stack", exist_ok=True)
    out = f"out/stack/{i+1:02d}_{NAMES[i]}.mp4"
    render(f"out/L{i+1}", out, 30, style=i, bgm=["pluck", "musicbox"][i % 2])
    title = TITLES[i % len(TITLES)].format(e=EMO[i]) + " #shorts"
    comment = open(out[:-4] + "_comment.txt").read()
    open(out[:-4] + "_업로드.txt", "w").write(f"[제목]\n{title}\n\n[설명]\n{DESC.format(n=NAMES[i])}\n\n[고정 댓글]\n{comment}")
    os.remove(out[:-4] + "_comment.txt")
    return out

if __name__ == "__main__":
    with ProcessPoolExecutor(4) as ex:
        print(list(ex.map(job, range(10))))
