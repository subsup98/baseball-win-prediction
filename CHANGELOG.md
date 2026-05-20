# Changelog

이 프로젝트는 `major.minor.patch` 형태의 SemVer 스타일 버전을 사용합니다.

## 0.1.5 - 2026-05-15

- MLB Stats API 기반 시즌 단위 데이터셋 생성 명령을 추가했습니다.
  - `collect-mlb-season-dataset`
  - 시즌별 schedule 수집
  - 누락 boxscore JSON만 이어받기
  - people metadata 수집
  - 표준 CSV 재생성
  - confirmed lineup feature CSV 생성
- 장시간 수집 중 중단되어도 기존 boxscore 파일을 건너뛰고 재개할 수 있게 했습니다.
- `collect-mlb-boxscores`, `collect-mlb-feeds`에 `--no-skip-existing` 옵션을 추가했습니다.
- 2024 시즌 5경기 smoke test로 다년치 수집 파이프라인을 검증했습니다.
  - schedule rows: `2429`
  - boxscore files: `5`
  - people rows: `119`
  - feature shape: `5 x 90`

## 0.1.4 - 2026-05-15

- MLB Stats API `people` metadata 수집 기능을 추가했습니다.
  - `collect-mlb-people`
  - `batSide.code`를 `bats`로 저장
  - `pitchHand.code`를 `throws`로 저장
- `standardize-mlb-boxscores`에 `--people` 옵션을 추가했습니다.
- 표준 변환 과정에서 다음 값을 보강하도록 했습니다.
  - `lineups.bats`
  - `batting_logs.opposing_pitcher_hand`
- 2024-04-01부터 2024-04-07까지 실제 MLB Stats API 데이터로 다음 파일을 재생성했습니다.
  - `data/raw/mlb_stats_api/people_2024-04-01_2024-04-07.csv`
  - `data/standardized/mlb_stats_api_2024-04-01_2024-04-07/*.csv`
  - `data/processed/features_confirmed_2024-04-01_2024-04-07.csv`
- lineup handedness 보강 검증 결과:
  - `lineups.bats` non-null ratio: `1.0`
  - feature table shape: `90 x 90`
- 수집/정규화 테스트를 추가했고 `7 passed`를 확인했습니다.

## 0.1.3 - 2026-05-15

- API/CSV 원천 데이터 수집 로직을 추가했습니다.
- MLB Stats API 수집 기능 추가:
  - `collect-mlb-schedule`
  - `collect-mlb-boxscores`
  - `collect-mlb-feeds`
- Retrosheet CSV/ZIP 다운로드 기능 추가:
  - `collect-retrosheet`
- Lahman/Baseball Databank 다운로드 기능 추가:
  - `collect-lahman`
- Chadwick Register player ID map 다운로드 기능 추가:
  - `collect-chadwick-people`
- FanGraphs leaderboard 수집 명령 추가:
  - `collect-fangraphs`
- 일반 URL 다운로드 명령 추가:
  - `download-url`
- MLB Stats API schedule JSON을 `games.csv` 초안에 가까운 tabular CSV로 정규화하는 테스트를 추가했습니다.
- 실제 MLB Stats API schedule 하루치 수집을 검증해 `data/raw/mlb_stats_api/schedule_2024-04-01.csv`를 생성했습니다.

## 0.1.2 - 2026-05-15

- 설계된 Feature를 만들기 위해 필요한 원천 데이터 요구사항을 `DATA_REQUIREMENTS.md`에 정리했습니다.
- 데이터 source별 역할을 확정했습니다.
  - MLB Stats API: 경기/일정/라인업/boxscore backbone
  - Baseball Savant / Statcast: pitch/PA 이벤트와 고급 타구/투구 품질
  - Retrosheet: historical game log와 라인업/날씨 백업
  - FanGraphs: 고급 세이버 지표와 park factor 보조
  - Lahman: ID/meta/시즌 누적 보조
- `PROJECT_CHECKLIST.md`, `PROJECT_DIRECTION.md`, `WORKLOG.md`에 데이터 수집 설계 내용을 반영했습니다.

## 0.1.1 - 2026-05-15

- 프로젝트 운영 문서 추가:
  - `PROJECT_CHECKLIST.md`
  - `WORKLOG.md`
  - `PROJECT_DIRECTION.md`
- `src` 기술 문서 추가:
  - `src/README.md`
  - `src/mlb_winprob/README.md`
  - `src/mlb_winprob/FEATURES.md`
  - `src/mlb_winprob/MODELS_AND_EXPERIMENTS.md`
  - `src/mlb_winprob/DATA_AND_CLI.md`
  - `src/mlb_winprob/SCHEMAS_AND_EVALUATION.md`
- 패키지 버전을 `0.1.0`에서 `0.1.1`로 업데이트했습니다.
- Windows 한글 경로에서 editable install `.pth`가 깨지지 않도록 로컬 venv의 editable path를 ASCII 상대경로로 정리했습니다.

## 0.1.0 - 2026-05-15

- MLB 승률 예측 연구용 Python 패키지 초기 구현.
- 경기 단위 Feature Builder 구현.
- 선발투수, 라인업, 팀 흐름, 불펜, 구장/날씨 Feature 생성.
- `pre_lineup` / `confirmed_lineup` 예측 모드 분리.
- Elo, Logistic Regression, Random Forest, MLP, optional booster, stacking 실험 구조 추가.
- Log Loss, Brier Score, Accuracy, confidence-band Accuracy, Calibration 평가 추가.
- CLI 명령 추가:
  - `build-features`
  - `train`
  - `predict`
  - `collect-statcast`
- 데이터 누수 방지 및 diff 방향 테스트 추가.

## 0.1.6 - 2026-05-19

- MLB Stats API boxscore/feed JSON 수집을 병렬화했습니다.
  - 기본 worker 수는 `min(32, CPU count * 2)`입니다.
  - `collect-mlb-boxscores`, `collect-mlb-feeds`, `collect-mlb-season-dataset`에 `--workers` 옵션을 추가했습니다.
  - 수집 진행 카운트로 `downloaded`, `skipped`, `failed`, `total`을 출력합니다.
- 2021-2025 최근 5시즌 MLB Stats API 데이터셋 구축을 완료했습니다.
  - boxscore JSON: 2021 `2429`, 2022 `2430`, 2023 `2430`, 2024 `2429`, 2025 `2430`
  - confirmed lineup feature CSV: 2021 `2429`, 2022 `2430`, 2023 `2430`, 2024 `2429`, 2025 `2430` rows

## 0.1.7 - 2026-05-19

- Feature 리포트 CLI를 추가했습니다.
  - `combine-features`
  - `feature-quality-report`
  - `season-holdout-report`
- 2021-2025 confirmed lineup feature를 통합해 `data/processed/features_confirmed_2021_2025.csv`를 생성했습니다.
  - total rows: `12148`
- 실제 feature 기준 null-rate 및 rolling feature readiness 리포트를 생성했습니다.
- 2022-2025 시즌별 holdout 백테스트 리포트를 생성했습니다.
  - models: `elo`, `logistic`, `random_forest`
  - best model by log_loss: `random_forest`
- 품질 리포트와 holdout 리포트 테스트를 추가했고 `13 passed`를 확인했습니다.

## 0.1.8 - 2026-05-19

- Empirical park factor 생성 기능을 추가했습니다.
  - `build-empirical-park-factors`
  - 표준 `games.csv`와 `batting_logs.csv`에서 구장별 run/HR factor를 계산합니다.
  - 데이터 누수를 피하기 위해 전 시즌 factor를 다음 시즌 feature에 적용합니다.
- 2021-2025 feature를 park factor 포함 버전으로 재생성했습니다.
  - `data/processed/features_confirmed_2021_2025_with_park_factors.csv`
- park factor 포함 품질 리포트와 시즌별 holdout 리포트를 생성했습니다.
  - `park_factor_run` null-rate: `1.0000` -> `0.2149`
  - `park_factor_hr` null-rate: `1.0000` -> `0.2149`
- park factor 테스트를 추가했고 `14 passed`를 확인했습니다.
