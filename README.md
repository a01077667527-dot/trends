# 실시간 키워드 모아보기

네이버 · 구글 · 다음의 인기 키워드를 한 페이지에서 봅니다.
GitHub Actions가 약 10분마다 키워드를 모아 `data.json`을 갱신하고, GitHub Pages가 페이지를 공개 주소로 보여 줍니다. PC를 꺼도 동작하고 휴대폰에서도 볼 수 있습니다.

## 처음 한 번만 하는 설정 (약 5분, 설치 불필요)

1. **GitHub 가입/로그인** — https://github.com
2. **저장소 만들기** — 오른쪽 위 `+` → `New repository`
   - Repository name: 예) `trends`
   - **Public** 선택 (무료 Pages는 공개 저장소에서 동작)
   - `Create repository`
3. **파일 올리기** — 새 저장소 화면의 `uploading an existing file` 링크 클릭 →
   이 폴더의 **모든 파일과 `.github` 폴더를 함께** 끌어다 놓기 → `Commit changes`
   - 윈도우 탐색기에서 `.github` 폴더가 안 보이면: 탐색기 상단 `보기` → `표시` → `숨긴 항목` 체크
   - 올린 뒤 저장소에 `.github/workflows/update.yml` 이 보이는지 확인
4. **Pages 켜기** — 저장소 `Settings` → 왼쪽 `Pages` →
   Source: `Deploy from a branch`, Branch: `main` / `/ (root)` → `Save`
5. **첫 수집 실행** — 저장소 `Actions` 탭 → (안내가 나오면 활성화 버튼 클릭) →
   왼쪽 `Update keywords` → `Run workflow` → 초록 체크가 뜰 때까지 1분 정도 대기
6. **접속** — `https://<내 GitHub 아이디>.github.io/trends/`
   (Settings → Pages 화면 위쪽에도 주소가 표시됩니다. 첫 게시까지 1~2분 걸릴 수 있어요)

휴대폰에서는 위 주소를 열고 브라우저 메뉴의 `홈 화면에 추가`를 누르면 앱처럼 쓸 수 있습니다.

## 알아 두기

- 갱신 주기: 약 10분. GitHub 사정으로 몇 분씩 늦어질 때가 있습니다. 페이지 상단에 "몇 분 전" 데이터인지 표시됩니다.
- 네이버는 실시간 검색어를 종료하여 **Signal.bz 집계 + 네이버 많이 본 뉴스**로 대신합니다.
- 다음 실시간 트렌드는 다음 정책상 새벽 1~6시에는 제한적으로 나옵니다.
- 사이트 구조가 바뀌면 해당 열에만 "불러오지 못했습니다"가 표시됩니다. `keywords.ps1`의 해당 함수만 고치면 됩니다.
- 수집이 실패하면 GitHub가 가입 메일로 알림을 보냅니다.

## 내 PC에서만 보기 (선택)

`실행.bat`을 더블클릭하면 `http://localhost:8787` 에서 실시간으로(1분 캐시) 볼 수 있습니다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `index.html` | 화면 |
| `data.json` | 수집된 키워드 (Actions가 자동 갱신) |
| `keywords.ps1` | 네이버/구글/다음 수집 코드 |
| `build.ps1` | `data.json` 생성 (Actions에서 실행) |
| `.github/workflows/update.yml` | 10분마다 수집하는 예약 작업 |
| `trends.ps1`, `실행.bat` | PC용 로컬 서버 |
