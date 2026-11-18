"""일주일 치 숨은 단어 찾기 쇼츠 일괄 제작 → out/week1/dayN/ (shorts.mp4, thumbnail.png, upload.txt)"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
from ws_shorts import render

EMOJI = {"꽃": "🌸", "동물": "🐯", "나라": "🌏", "한식": "🍚", "바다 생물": "🦑", "옛날 놀이": "🪁", "도시": "🏙️"}
PLAN = [  # (주제, 단어, 판 크기, 찾기 시간, 배경음악, 제목)
 ("꽃", "장미,국화,개나리,진달래,무궁화,튤립", 6, 20, "musicbox", "숨은 꽃 6개, 다 찾으면 두뇌 나이 30대! {e}"),
 ("동물", "호랑이,토끼,강아지,고양이,다람쥐,코끼리", 7, 25, "pluck", "99%가 마지막 동물을 못 찾습니다 {e} 숨은 동물 6개"),
 ("나라", "한국,미국,일본,중국,프랑스,독일,영국", 7, 25, "musicbox", "나라 이름 7개, 몇 개 찾으세요? {e} 상위 1% 도전"),
 ("한식", "김치,불고기,비빔밥,된장,떡국,잡채", 6, 20, "pluck", "보기만 해도 배고픈 단어 찾기 {e} 숨은 한식 6개"),
 ("바다 생물", "고등어,오징어,문어,새우,꽃게,멸치", 6, 20, "musicbox", "60대 이상 다 찾으면 두뇌 천재! {e} 숨은 바다 생물"),
 ("옛날 놀이", "윷놀이,제기,팽이,고무줄,술래,구슬", 7, 25, "pluck", "그 시절 추억의 놀이 6개 {e} 다 찾으면 진짜 대단해요"),
 ("도시", "서울,부산,대구,인천,광주,대전,울산,제주", 7, 25, "musicbox", "우리나라 도시 8개, 다 찾으면 상위 1%! {e}"),
]
DESC = """🧠 두뇌 건강 강화 프로젝트 {d}일차 – 숨은 단어 찾기 ({t} 편)

글자판 속에 {t} 이름 {k}개가 숨어 있어요.
가로(→), 세로(↓)로 찾아보세요!

몇 개 찾으셨나요? 댓글로 알려주세요 😊
매일 새로운 문제로 함께 두뇌 운동해요.

#단어찾기 #두뇌운동 #숨은단어찾기 #두뇌게임 #뇌건강 #집중력 #시니어 #shorts"""

def job(i):
    t, words, n, find, bgm, title = PLAN[i]
    out = f"out/week1/day{i+1}"
    render(t, words.split(","), out, n, seed=i + 11, find=find, bgm=bgm)
    k = len(words.split(","))
    text = f"[제목]\n{title.format(e=EMOJI[t])} #shorts\n\n[설명]\n{DESC.format(d=i+1, t=t, k=k)}\n"
    open(f"{out}/upload.txt", "w").write(text)
    return i + 1, title.format(e=EMOJI[t])

if __name__ == "__main__":
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(job, range(len(PLAN))))
    with open("out/week1/업로드_목록.txt", "w") as f:
        for d, _ in res:
            f.write(f"===== {d}일차 (day{d}/shorts.mp4) =====\n" + open(f"out/week1/day{d}/upload.txt").read() + "\n")
    print(res)
