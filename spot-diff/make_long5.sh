#!/bin/bash
# 롱폼 기본 형식: 5문제 × 찾기 90초 + 정답 10초, 문제당 차이 5곳 (약 8분 50초, 중간 광고 가능)
# 사용법: ./make_long5.sh 세트이름 out/X1 out/X2 out/X3 out/X4 out/X5
#   - 각 폴더: base.png(마크 제거 후) + specs/X?.json 으로 만든 b.png, answers.json
#   - 인트로: "다섯 문제" 목소리 그대로 쓰는 out/intro/intro_5_bg.mp4
set -e
cd "$(dirname "$0")"
name=$1; shift
python3 longform.py out/$name "$@" --time 90 --intro out/intro/intro_5_bg.mp4
