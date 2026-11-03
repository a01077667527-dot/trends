@echo off
chcp 65001 >nul
cd /d %~dp0
echo === 동물 친구들과 숫자 놀이 3D - 그래픽카드 렌더링 ===
where node >nul 2>nul || (echo [!] Node.js 가 필요해요: https://nodejs.org 에서 LTS 설치 후 다시 실행하세요 & pause & exit /b 1)
where python >nul 2>nul || (echo [!] Python 이 필요해요: https://www.python.org 에서 설치 ^(Add to PATH 체크^) 후 다시 실행하세요 & pause & exit /b 1)
if not exist node_modules\playwright (
  call npm install playwright@1.49.1 || (pause & exit /b 1)
  call npx playwright install chromium || (pause & exit /b 1)
)
python -m pip install --quiet pycairo numpy fonttools pillow imageio-ffmpeg || (pause & exit /b 1)
set GPU=1
if "%WORKERS%"=="" set WORKERS=2
python compose3d.py
echo.
echo 완성! kids-video\animal_numbers_3d.mp4 를 확인하세요.
pause
