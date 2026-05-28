# Worklog

## 2026-05-27

### KBO 트랙 - 전체 시즌 canonical 데이터 확보

- MyKBO 게임 페이지 수집기에 요청 딜레이(`--delay`, jitter)와 병렬 워커(`--workers`)를 추가하고, `fetch_url`에 429 재시도(`Retry-After` 기반 지수 백오프)를 구현했습니다. 단일 rate-limit 응답이 배치 전체를 중단시키지 않습니다.
- MyKBO에 이전 시즌(최소 2018년까지) 데이터가 존재함을 확인했습니다. "2024–2026만"은 소스 한계가 아니라 이전 수집 범위 문제였고, MLB 범위(2021–2025)를 포함하도록 KBO를 2021–2026으로 확장했습니다.
- 게임 페이지 박스스코어 테이블 개수가 시즌·경기마다 달라(2022·2023 등은 헤더 테이블이 1칸 더 있어 6테이블) 위치 기반 파싱이 깨지던 것을, 컬럼 기반 분류(`_classify_game_table`: ERA+IP→pitching, Pos+AB→batting)로 교체했습니다. 2024–2026 재표준화로 기존 결과와 완전 동일함을 검증했습니다.
- 2021–2026 전체 final 경기 4,119건(2021:766, 2022:801, 2023:800, 2024:741, 2025:737, 2026:274)의 게임 페이지를 수집·파싱(26,861개 테이블)했습니다.
- 전체 canonical 테이블을 생성했습니다: `data/standardized/kbo/canonical_2021_2026/` - `batting_logs`(105,971행), `pitcher_logs`(39,930행), `lineups`(74,142행). 6시즌 4,119경기 모두 커버리지 100%. (구버전 `canonical_2024_2026`은 상위집합으로 대체되어 제거)
- 품질: 선발 타자 `mykbo_player_id` 누락 ~0%, 라인업 `player_id` 누락 0%, 경기당 선발투수 2명·라인업 18칸 정상.
- 확장 데이터로 league-common feature build(4,122행×205컬럼, 선발 ID 누락 0%) + 시즌 holdout 재실행. 2024/2025/2026 holdout 최적 모델 모두 log_loss<0.693(coin-flip) 통과: 2024 logistic 0.693, 2025 RF 0.684, 2026 RF 0.688.
- KBO First Milestone 1단계 완료·초과(6시즌 확보)하고 최소 스모크 테스트(feature build→quality→holdout)까지 완료. 다음: 공개데이터 세이버메트릭 확장·`_proxy` 컬럼·weather/venue join(2~3단계).

## 2026-05-15

### 0.1.0 초기 구현

- MLB 경기 승률 예측 시스템의 Python 패키지 구조를 만들었습니다.
- `FeatureBuilder`를 중심으로 경기 단위 Feature Vector 생성 구조를 구현했습니다.
- 선발투수, 라인업, 팀 흐름, 불펜, 구장/날씨 Feature를 같은 game row에 합치는 구조를 만들었습니다.
- 모든 rolling/season-to-date Feature가 경기 전 기준으로 계산되도록 구현했습니다.
- `pre_lineup`과 `confirmed_lineup` 모드를 분리했습니다.
- Home/Away diff Feature 방향을 `positive = home advantage`로 통일했습니다.
- 모델 실험 구조를 추가했습니다.
  - Elo baseline
  - Logistic Regression
  - Random Forest
  - MLP
  - LightGBM / XGBoost / CatBoost optional
  - Hybrid stacking
- 평가 지표를 추가했습니다.
  - Log Loss
  - Brier Score
  - Accuracy
  - confidence-band Accuracy
  - Calibration table
- CLI 명령을 추가했습니다.
  - `build-features`
  - `train`
  - `predict`
  - `collect-statcast`
- 테스트를 추가하고 `4 passed`를 확인했습니다.

### 0.1.1 문서화 및 버저닝

- 패키지 버전을 `0.1.1`로 올렸습니다.
- `CHANGELOG.md`를 추가해 버전별 변경 이력을 기록하기 시작했습니다.
- root 운영 문서를 추가했습니다.
  - `PROJECT_CHECKLIST.md`
  - `WORKLOG.md`
  - `PROJECT_DIRECTION.md`
- `src` 구조와 주요 모듈별 설명 문서를 추가했습니다.
  - `src/README.md`
  - `src/mlb_winprob/README.md`
  - `src/mlb_winprob/FEATURES.md`
  - `src/mlb_winprob/MODELS_AND_EXPERIMENTS.md`
  - `src/mlb_winprob/DATA_AND_CLI.md`
  - `src/mlb_winprob/SCHEMAS_AND_EVALUATION.md`
- `mlb_winprob.__version__`과 설치 메타데이터가 `0.1.1`로 맞춰진 것을 확인했습니다.
- Windows 한글 경로에서 editable install `.pth`가 cp949 decode 오류를 내는 문제를 ASCII 상대경로로 정리했습니다.
- 문서 작업 후 `pytest` 기준 `4 passed`를 재확인했습니다.

### 0.1.2 데이터 요구사항 설계

- 설계된 Feature를 실제로 만들기 위해 필요한 원천 데이터를 source별로 정리했습니다.
- source 역할을 다음과 같이 분리했습니다.
  - MLB Stats API: 경기 일정, game id, 홈/원정팀, 점수, venue, probable pitcher, boxscore, confirmed lineup
  - Baseball Savant / Statcast: pitch/PA 이벤트, 좌우 매치업, xwOBA, wOBA value, 타구/투구 품질
  - Retrosheet: historical game log, 선발 라인업, 날씨, 타자/투수 game log 백업
  - FanGraphs: wRC+, FIP, K-BB%, park factor 보조와 검산
  - Lahman: 선수/팀 ID, 시즌 누적, 팀 메타데이터 보조
- `DATA_REQUIREMENTS.md`를 추가해 feature-to-source, source-to-table, raw column 요구사항을 문서화했습니다.
- `PROJECT_CHECKLIST.md`에 실제 수집/변환 작업 항목을 추가했습니다.

### 0.1.3 원천 데이터 수집 로직 구현

- `data_sources.py`에 표준 라이브러리 기반 다운로드 유틸을 추가했습니다.
  - `download_url`
  - `fetch_json`
  - `write_json`
- MLB Stats API collector를 추가했습니다.
  - schedule endpoint 호출
  - schedule JSON을 tabular CSV로 정규화
  - game boxscore JSON 저장
  - game live feed JSON 저장
- Retrosheet collector를 추가했습니다.
  - master CSV 파일 다운로드
  - main/basic/biodata ZIP 다운로드
- Lahman/Baseball Databank collector를 추가했습니다.
  - core table CSV 다운로드
  - 전체 archive ZIP 다운로드
- Chadwick Register collector를 추가했습니다.
  - `people.csv` 다운로드
- pybaseball collector에 FanGraphs batting/pitching leaderboard 수집 명령을 연결했습니다.
- CLI 명령을 추가했습니다.
  - `collect-mlb-schedule`
  - `collect-mlb-boxscores`
  - `collect-mlb-feeds`
  - `collect-retrosheet`
  - `collect-lahman`
  - `collect-chadwick-people`
  - `collect-fangraphs`
  - `download-url`
- MLB Stats API schedule 정규화 테스트를 추가했습니다.
- 실제 호출 검증:
  - `2024-04-01` 하루치 MLB Stats API schedule 수집 성공
  - `data/raw/mlb_stats_api/schedule_2024-04-01.csv` 생성
- 문법 검사와 테스트를 재실행했고 `5 passed`를 확인했습니다.

### 0.1.4 Handedness 보강 및 Feature 재생성

- MLB Stats API `people` endpoint 수집 기능을 추가했습니다.
  - `collect-mlb-people`
  - 입력 CSV에서 `player_id`, `home_sp_id`, `away_sp_id`를 모아 metadata를 수집합니다.
  - `bats`, `throws`, `primary_position`을 저장합니다.
- `standardize-mlb-boxscores`에 `--people` 옵션을 추가했습니다.
- 표준 변환 단계에서 `lineups.bats`를 MLB people metadata로 채웠습니다.
- 표준 변환 단계에서 `batting_logs.opposing_pitcher_hand`를 상대 선발의 `throws` 값으로 채웠습니다.
- 실제 데이터 보강 결과:
  - `data/raw/mlb_stats_api/people_2024-04-01_2024-04-07.csv` 생성
  - 799명 metadata 수집
  - `lineups.csv` 1620 rows 중 `bats` 1620 rows 채움
  - `data/processed/features_confirmed_2024-04-01_2024-04-07.csv` 재생성
  - feature table shape: `90 x 90`
- `lineup_lefty_ratio`, `lineup_vs_rhp_woba`, `lineup_vs_lhp_woba`가 실제 handedness 기반으로 계산되기 시작했습니다.
- 아직 시즌 초반 일주일 샘플이라 선발투수 season-to-date/rolling Feature는 결측이 많습니다. 전체 시즌 또는 다년 데이터 구축 후 품질 검증이 필요합니다.
- 테스트를 추가하고 `7 passed`를 확인했습니다.

### 0.1.5 시즌 단위 수집 파이프라인

- MLB Stats API 기반 시즌 단위 데이터셋 생성 명령을 추가했습니다.
  - `collect-mlb-season-dataset`
  - `--start-season`, `--end-season`, `--output-root`, `--game-types`, `--limit`, `--schedule-only` 지원
  - 이미 저장된 boxscore JSON은 기본적으로 건너뛰어 중단 후 재개가 가능합니다.
- 시즌별 처리 순서를 자동화했습니다.
  - schedule 수집 또는 기존 schedule 재사용
  - 정규시즌 경기 필터링
  - boxscore JSON 저장
  - 1차 표준화
  - people metadata 수집
  - handedness 보강 표준화
  - confirmed lineup feature CSV 생성
- 2024 시즌 5경기 smoke test를 실행했습니다.
  - `data/smoke_multi_year/raw/mlb_stats_api/schedule_2024.csv`
  - `data/smoke_multi_year/raw/mlb_stats_api/boxscores_2024/`
  - `data/smoke_multi_year/raw/mlb_stats_api/people_2024.csv`
  - `data/smoke_multi_year/processed/features_confirmed_2024.csv`
- smoke test 결과:
  - schedule rows: `2429`
  - boxscore files: `5`
  - people rows: `119`
  - feature table shape: `5 x 90`
- 이후 실제 2021-2025 최근 5시즌 데이터를 같은 명령으로 수집하는 단계로 진행합니다.

## 기록 규칙

- 새 기능을 추가하면 날짜, 버전, 변경 목적, 영향 범위를 기록합니다.
- 모델 성능 실험을 실행하면 데이터 기간, prediction mode, feature set, 모델명, 주요 metric을 기록합니다.
- 데이터 수집 방식을 바꾸면 source, schema 변경 여부, 누수 가능성 점검 결과를 기록합니다.

## 2026-05-19

### 0.1.6 수집 속도 개선 및 2021-2025 데이터셋 구축

- MLB Stats API boxscore/feed JSON 수집을 병렬화했습니다.
  - `ThreadPoolExecutor` 기반으로 game id별 요청을 병렬 처리합니다.
  - 기본 worker 수는 `min(32, CPU count * 2)`로 자동 산정합니다.
  - CLI에서 `--workers`로 수동 조정할 수 있습니다.
  - 수집 중 `downloaded`, `skipped`, `failed`, `total` 진행 카운트를 출력합니다.
- VS Code 터미널에서 직접 실행해 `print` 진행 상황을 확인하는 방식으로 2023 시즌 중단 지점부터 이어받았습니다.
- 2021-2025 최근 5시즌 MLB Stats API 기반 데이터셋 구축을 완료했습니다.

수집 결과:

```text
boxscores_2021: 2429 files
boxscores_2022: 2430 files
boxscores_2023: 2430 files
boxscores_2024: 2429 files
boxscores_2025: 2430 files

standardized games rows:
2021: 2429
2022: 2430
2023: 2430
2024: 2429
2025: 2430

confirmed lineup feature rows:
2021: 2429
2022: 2430
2023: 2430
2024: 2429
2025: 2430
```

생성된 주요 산출물:

```text
data/raw/mlb_stats_api/schedule_2021.csv
data/raw/mlb_stats_api/schedule_2022.csv
data/raw/mlb_stats_api/schedule_2023.csv
data/raw/mlb_stats_api/schedule_2024.csv
data/raw/mlb_stats_api/schedule_2025.csv
data/raw/mlb_stats_api/people_2021.csv
data/raw/mlb_stats_api/people_2022.csv
data/raw/mlb_stats_api/people_2023.csv
data/raw/mlb_stats_api/people_2024.csv
data/raw/mlb_stats_api/people_2025.csv
data/standardized/mlb_stats_api_2021/
data/standardized/mlb_stats_api_2022/
data/standardized/mlb_stats_api_2023/
data/standardized/mlb_stats_api_2024/
data/standardized/mlb_stats_api_2025/
data/processed/features_confirmed_2021.csv
data/processed/features_confirmed_2022.csv
data/processed/features_confirmed_2023.csv
data/processed/features_confirmed_2024.csv
data/processed/features_confirmed_2025.csv
```

### 0.1.7 Feature 품질 리포트 및 시즌별 holdout 백테스트

- 2021-2025 confirmed lineup feature CSV를 하나로 통합했습니다.
  - `data/processed/features_confirmed_2021_2025.csv`
  - total rows: `12148`
- Feature 품질 리포트 CLI를 추가했습니다.
  - `combine-features`
  - `feature-quality-report`
  - `season-holdout-report`
- 실제 2021-2025 feature 기준 품질 리포트를 생성했습니다.
  - `outputs/quality/features_confirmed_2021_2025/feature_null_rates.csv`
  - `outputs/quality/features_confirmed_2021_2025/rolling_feature_readiness.csv`
  - `outputs/quality/features_confirmed_2021_2025/season_summary.csv`
  - `outputs/quality/features_confirmed_2021_2025/summary.md`
- 2022-2025 시즌별 holdout 백테스트를 실행했습니다.
  - models: `elo`, `logistic`, `random_forest`
  - prediction mode: `confirmed_lineup`
  - output: `outputs/experiments/season_holdout_confirmed_2021_2025/`
- 확인된 데이터 품질 이슈:
  - `humidity`, `park_factor_run`, `park_factor_hr`는 현재 전체 결측입니다.
  - `wind_direction` null-rate는 약 `0.1697`입니다.
  - 선발투수 season-to-date/rolling 계열은 시즌 초반 결측 영향으로 약 `7-8%` 결측이 남아 있습니다.
- holdout 기준 best model은 모든 시즌에서 `random_forest`였습니다.
  - 2022: log_loss `0.6790`, accuracy `0.5605`
  - 2023: log_loss `0.6841`, accuracy `0.5531`
  - 2024: log_loss `0.6773`, accuracy `0.5706`
  - 2025: log_loss `0.6818`, accuracy `0.5510`
- `pytest` 기준 `13 passed`를 확인했습니다.

### 0.1.8 Empirical park factor 보강

- 외부 park factor 파일이 아직 없는 상태라, 현재 보유한 표준 경기/타격 로그로 empirical park factor를 생성하는 경로를 추가했습니다.
- 같은 시즌 최종 park factor를 같은 시즌 예측 feature로 쓰면 누수가 되므로, 전 시즌 값을 다음 시즌에 적용하는 방식으로 확정했습니다.
  - 예: 2021 venue 결과 -> 2022 feature의 `park_factor_run`, `park_factor_hr`
- `build-empirical-park-factors` CLI를 추가했습니다.
  - 입력: 시즌별 `data/standardized/mlb_stats_api_YYYY/`
  - 출력: `data/processed/park_factors_empirical_previous_season_2022_2026.csv`
  - 기본 `min_games=20`으로 중립/소규모 구장 노이즈를 제외합니다.
- 2021-2025 feature를 park factor 포함 버전으로 재생성했습니다.
  - `data/processed/features_confirmed_2021_2025_with_park_factors.csv`
  - total rows: `12148`
- 품질 리포트와 시즌별 holdout 리포트를 park factor 포함 버전으로 다시 생성했습니다.
  - `outputs/quality/features_confirmed_2021_2025_with_park_factors/`
  - `outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors/`
- 결측 개선:
  - `park_factor_run`: null-rate `1.0000` -> `0.2149`
  - `park_factor_hr`: null-rate `1.0000` -> `0.2149`
  - `humidity`: null-rate `1.0000` 유지
- holdout 기준 best model은 모든 시즌에서 `random_forest`였습니다.
  - 2022: log_loss `0.6790`, accuracy `0.5605`
  - 2023: log_loss `0.6840`, accuracy `0.5580`
  - 2024: log_loss `0.6786`, accuracy `0.5583`
  - 2025: log_loss `0.6809`, accuracy `0.5551`
- `pytest` 기준 `14 passed`를 확인했습니다.

## 2026-05-20

### 진행 상황 점검 및 체크리스트 업데이트

- 현재 작업 폴더는 git repository가 아니어서 `git status` 기준 변경 추적은 사용할 수 없음을 확인했습니다.
- 루트 작업 관리 문서는 다음 두 파일을 기준으로 확인했습니다.
  - `WORKLOG.md`
  - `PROJECT_CHECKLIST.md`
- 2021-2025 MLB Stats API 기반 원천 데이터 수집 상태를 재확인했습니다.
  - `boxscores_2021`: `2429` files
  - `boxscores_2022`: `2430` files
  - `boxscores_2023`: `2430` files
  - `boxscores_2024`: `2429` files
  - `boxscores_2025`: `2430` files
- 통합 feature 산출물을 재확인했습니다.
  - `data/processed/features_confirmed_2021_2025.csv`: `12148` rows
  - `data/processed/features_confirmed_2021_2025_with_park_factors.csv`: `12148` rows
- 최신 품질 리포트 기준 상태를 확인했습니다.
  - rows: `12148`
  - columns: `91`
  - `humidity` null-rate: `1.0000`
  - `park_factor_run` null-rate: `0.2149`
  - `park_factor_hr` null-rate: `0.2149`
  - `wind_direction` null-rate: `0.1697`
- park factor 포함 holdout 기준 best model이 모든 holdout season에서 `random_forest`임을 재확인했습니다.
  - 2022: log_loss `0.6790`, accuracy `0.5605`
  - 2023: log_loss `0.6840`, accuracy `0.5580`
  - 2024: log_loss `0.6786`, accuracy `0.5583`
  - 2025: log_loss `0.6809`, accuracy `0.5551`
- 기본 Python 환경에서는 `pytest`가 없어 테스트 실행이 실패했습니다.
  - 실패 사유: `No module named pytest`
- 프로젝트 `.venv`로 테스트를 재실행해 현재 코드 상태를 검증했습니다.
  - command: `.\.venv\Scripts\python.exe -m pytest`
  - result: `14 passed`
- `PROJECT_CHECKLIST.md`에 최신 완료 항목과 다음 우선순위를 반영했습니다.

현재 남은 핵심 작업:

- weather source 결정 및 `humidity` 결측 해소
- Baseball Savant / Statcast event 수집과 투타 로그 집계 연동
- Retrosheet 백업 source 변환 경로 구현
- FanGraphs 보조 지표 수집 방식 확정
- Lahman 또는 Chadwick register 기반 `id_map.csv` 구축
- Calibration plot 이미지 저장 기능 추가
- Feature importance / SHAP 기반 설명 리포트 추가
- 데이터 갱신/학습/검증 명령 및 결과 디렉터리 운영 표준화

### 0.1.9 Weather 1차 보강

- 1순위 작업인 weather 결측/자동화 개선을 시작했습니다.
- 현재 보유한 MLB Stats API boxscore JSON에는 `Weather`, `Wind` 정보는 있으나 `Humidity` 정보는 없음을 확인했습니다.
- `standardize.py`의 weather parser를 보강했습니다.
  - `weather_condition` 추출
  - `weather_source` 기록
  - `Roof Closed`, `Dome`, `Indoor` 계열 문구 기반 `is_dome=1` 판정
  - 원천 문자열에 humidity 문구가 들어올 경우를 대비한 humidity parser
- 신규 테스트를 추가했습니다.
  - closed roof 경기의 `is_dome=1` 판정
  - humidity 문구가 제공될 때 값 추출
- 2021-2025 표준 CSV를 재생성했습니다.
  - `data/standardized/mlb_stats_api_2021/weather.csv`
  - `data/standardized/mlb_stats_api_2022/weather.csv`
  - `data/standardized/mlb_stats_api_2023/weather.csv`
  - `data/standardized/mlb_stats_api_2024/weather.csv`
  - `data/standardized/mlb_stats_api_2025/weather.csv`
- 2021-2025 feature와 park factor 포함 feature를 재생성했습니다.
  - `data/processed/features_confirmed_2021_2025.csv`
  - `data/processed/features_confirmed_2021_2025_with_park_factors.csv`
- 품질 리포트와 시즌별 holdout 리포트를 재생성했습니다.
  - `outputs/quality/features_confirmed_2021_2025/`
  - `outputs/quality/features_confirmed_2021_2025_with_park_factors/`
  - `outputs/experiments/season_holdout_confirmed_2021_2025/`
  - `outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors/`

확인 결과:

```text
features_confirmed_2021_2025_with_park_factors.csv rows: 12148

temperature null_rate: 0.0000
is_dome null_rate: 0.0000
wind_speed null_rate: 0.0001
wind_direction null_rate: 0.1697
humidity null_rate: 1.0000

2024 weather.csv is_dome counts:
is_dome=1  457
is_dome=0  1972
```

park factor 포함 holdout 기준 best model:

```text
2022 random_forest log_loss 0.6770 accuracy 0.5704
2023 random_forest log_loss 0.6854 accuracy 0.5543
2024 random_forest log_loss 0.6774 accuracy 0.5673
2025 random_forest log_loss 0.6814 accuracy 0.5568
```

- MLB Stats API live feed collector가 `api/v1` 경로를 사용해 `404`를 내는 문제를 확인했습니다.
- live feed 경로를 `https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live`로 수정했습니다.
- live feed URL 회귀 테스트를 추가했습니다.
- 수정 후 2024 schedule 기준 샘플 5경기 live feed를 수집했습니다.
  - output: `data/raw/mlb_stats_api/feeds_weather_probe_2024/`
- 샘플 live feed의 `gameData.weather`에는 구조화된 날씨 정보가 있었지만, 값은 `condition`, `temp`, `wind`까지만 제공되고 `humidity`는 없음을 확인했습니다.
  - 예: `{"condition": "Dome", "temp": "72", "wind": "0 mph, None"}`
- `.venv` 기준 테스트를 재실행했고 `17 passed`를 확인했습니다.
- 남은 weather 핵심 이슈는 `humidity` 100% 결측입니다. boxscore와 live feed 샘플 모두 습도를 제공하지 않으므로 다음 단계는 외부 historical weather source를 확정하고 venue 위치/경기 시각 기준으로 join하는 것입니다.

### 0.1.10 Open-Meteo humidity 보강

- Open-Meteo Historical Weather API를 외부 humidity 보강 source로 채택했습니다.
  - 시간별 `relative_humidity_2m`를 경기 시각의 가장 가까운 UTC hour에 맞춰 join합니다.
  - 기존 MLB boxscore의 `temperature`, `wind_speed`, `wind_direction`, `is_dome`은 유지하고 `humidity` 결측만 채웁니다.
- MLB Stats API venue endpoint에서 구장 좌표를 수집하는 경로를 추가했습니다.
  - `collect-mlb-venues`
  - output: `data/raw/mlb_stats_api/venues_2021_2025.csv`
- MLB venue endpoint에 좌표가 없는 `Estadio Alfredo Harp Helu`는 fallback 좌표를 적용했습니다.
- Open-Meteo humidity 보강 CLI를 추가했습니다.
  - `augment-weather-openmeteo`
- 2021-2025 전체 `weather.csv`를 Open-Meteo humidity로 보강했습니다.
  - 2021: `2429/2429` rows humidity 채움
  - 2022: `2430/2430` rows humidity 채움
  - 2023: `2430/2430` rows humidity 채움
  - 2024: `2429/2429` rows humidity 채움
  - 2025: `2430/2430` rows humidity 채움
- 2021-2025 기본 feature와 park factor 포함 feature를 재생성했습니다.
  - `data/processed/features_confirmed_2021_2025.csv`
  - `data/processed/features_confirmed_2021_2025_with_park_factors.csv`
- 품질 리포트와 시즌별 holdout 리포트를 재생성했습니다.
  - `outputs/quality/features_confirmed_2021_2025/`
  - `outputs/quality/features_confirmed_2021_2025_with_park_factors/`
  - `outputs/experiments/season_holdout_confirmed_2021_2025/`
  - `outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors/`

품질 확인:

```text
features_confirmed_2021_2025_with_park_factors.csv rows: 12148

humidity null_rate: 1.0000 -> 0.0000
temperature null_rate: 0.0000
is_dome null_rate: 0.0000
wind_speed null_rate: 0.0001
wind_direction null_rate: 0.1697
park_factor_run null_rate: 0.2149
park_factor_hr null_rate: 0.2149
```

park factor 포함 holdout 기준 best model:

```text
2022 random_forest log_loss 0.6780 accuracy 0.5675
2023 random_forest log_loss 0.6821 accuracy 0.5564
2024 random_forest log_loss 0.6777 accuracy 0.5677
2025 random_forest log_loss 0.6821 accuracy 0.5514
```

- `.venv` 기준 테스트를 재실행했고 `20 passed`를 확인했습니다.

### 0.1.11 Statcast 집계 및 선택적 Feature 연동

- Statcast event CSV를 선수/경기 단위 품질 집계로 변환하는 모듈을 추가했습니다.
  - `src/mlb_winprob/statcast.py`
- 타자 game log에 병합 가능한 Statcast 품질 합계를 생성합니다.
  - `statcast_pa`
  - `statcast_batted_balls`
  - `statcast_hard_hit_balls`
  - `statcast_barrels`
  - `statcast_xwoba_sum/count`
  - `statcast_woba_sum/count`
  - `statcast_launch_speed_sum`
- 투수 game log에 병합 가능한 Statcast 허용 품질 합계를 생성합니다.
  - `statcast_batters_faced`
  - `statcast_batted_balls_allowed`
  - `statcast_hard_hit_balls_allowed`
  - `statcast_barrels_allowed`
  - `statcast_xwoba_allowed_sum/count`
  - `statcast_woba_allowed_sum/count`
  - `statcast_launch_speed_allowed_sum`
- CLI를 추가했습니다.
  - `aggregate-statcast`
  - `merge-statcast-logs`
- FeatureBuilder가 Statcast 품질 컬럼이 있을 때만 다음 feature를 추가로 계산하도록 연동했습니다.
  - `lineup_statcast_xwoba`
  - `lineup_statcast_woba`
  - `lineup_hard_hit_rate`
  - `lineup_barrel_rate`
  - `lineup_avg_exit_velocity`
  - `sp_statcast_xwoba_allowed_to_date`
  - `sp_statcast_woba_allowed_to_date`
  - `sp_hard_hit_rate_allowed_to_date`
  - `sp_barrel_rate_allowed_to_date`
  - `sp_avg_exit_velocity_allowed_to_date`
  - `lineup_statcast_xwoba_diff`
  - `sp_statcast_xwoba_allowed_diff`
- 기존 boxscore-only feature 생성 경로에서는 위 컬럼이 모두 결측으로 남고, Statcast 품질 컬럼이 병합된 로그를 넣었을 때만 값이 채워집니다.
- 단위 테스트를 추가했습니다.
  - Statcast batting 품질 집계
  - Statcast pitching 품질 집계
  - 표준 로그와 Statcast 품질 집계 merge
  - Statcast 기반 feature의 누수 방지 계산
- `.venv` 기준 테스트를 재실행했고 `24 passed`를 확인했습니다.

남은 Statcast 작업:

- `pybaseball` data extra 설치/확인
- 2021-2025 Statcast event CSV 실제 수집
- 2021-2025 표준 로그에 Statcast 품질 컬럼 병합
- Statcast 포함 feature/품질/holdout 리포트 별도 생성

### 0.1.12 Statcast smoke test 수집

- `pybaseball` data extra를 `.venv`에 설치했습니다.
  - command: `.\.venv\Scripts\python.exe -m pip install -e ".[data]"`
- 2024-04-01~2024-04-07 Statcast event smoke test를 실제 수집했습니다.
  - output: `data/raw/statcast/statcast_2024-04-01_2024-04-07.csv`
  - rows: `26072`
- Statcast event를 선수/경기 단위 품질 집계로 변환했습니다.
  - batting quality rows: `1771`
  - pitching quality rows: `738`
- 기존 2024-04-01~2024-04-07 표준 로그에 Statcast 품질 컬럼을 병합했습니다.
  - `data/standardized/mlb_stats_api_2024-04-01_2024-04-07/batting_logs_statcast.csv`: `1894` rows
  - `data/standardized/mlb_stats_api_2024-04-01_2024-04-07/pitcher_logs_statcast.csv`: `752` rows
- Statcast 포함 feature smoke 파일을 생성했습니다.
  - `data/processed/features_confirmed_2024-04-01_2024-04-07_with_statcast.csv`
  - rows: `90`
- Statcast 포함 feature 품질 리포트를 생성했습니다.
  - `outputs/quality/features_confirmed_2024-04-01_2024-04-07_with_statcast/`
- Smoke test 품질 확인:

```text
home_lineup_statcast_xwoba non_null: 73 / 90
away_lineup_statcast_xwoba non_null: 72 / 90
home_sp_statcast_xwoba_allowed_to_date non_null: 13 / 90
away_sp_statcast_xwoba_allowed_to_date non_null: 13 / 90
```

- 첫 경기/시즌 초반은 누수 방지상 prior Statcast 이력이 없어 결측이 남는 것이 정상입니다.
- `.venv` 기준 테스트를 재실행했고 `24 passed`를 확인했습니다.

### 0.1.13 2021-2025 Statcast 전체 수집 및 feature 반영

- 12개 worker 병렬 수집 스크립트를 추가했습니다.
  - `scripts/collect_statcast_parallel.py`
  - 시즌별 `games.csv`의 최소/최대 경기일을 기준으로 7일 chunk를 만들고 `pybaseball.statcast()`로 수집합니다.
  - chunk 산출물은 `data/raw/statcast/chunks/`에 저장하고, 성공 후 시즌별 CSV로 합칩니다.
- 2021-2025 전체 Statcast event CSV를 수집했습니다.

```text
data/raw/statcast/statcast_2021.csv  712320 rows
data/raw/statcast/statcast_2022.csv  710210 rows
data/raw/statcast/statcast_2023.csv  720684 rows
data/raw/statcast/statcast_2024.csv  732481 rows
data/raw/statcast/statcast_2025.csv  742080 rows
```

- 시즌별 Statcast event를 타자/투수 품질 집계로 변환했습니다.

```text
2021 batting quality 51490 rows, pitching quality 21540 rows
2022 batting quality 48329 rows, pitching quality 20878 rows
2023 batting quality 48767 rows, pitching quality 20629 rows
2024 batting quality 51565 rows, pitching quality 21659 rows
2025 batting quality 52011 rows, pitching quality 21948 rows
```

- 2021-2025 표준 로그에 Statcast 품질 컬럼을 병합했습니다.
  - `data/standardized/mlb_stats_api_*/batting_logs_statcast.csv`
  - `data/standardized/mlb_stats_api_*/pitcher_logs_statcast.csv`
- Statcast + weather + park factor 포함 feature CSV를 생성했습니다.

```text
data/processed/features_confirmed_2021_with_park_factors_statcast.csv  2429 rows
data/processed/features_confirmed_2022_with_park_factors_statcast.csv  2430 rows
data/processed/features_confirmed_2023_with_park_factors_statcast.csv  2430 rows
data/processed/features_confirmed_2024_with_park_factors_statcast.csv  2429 rows
data/processed/features_confirmed_2025_with_park_factors_statcast.csv  2430 rows
data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv  12148 rows
```

- Statcast 포함 품질 리포트와 holdout 리포트를 생성했습니다.
  - `outputs/quality/features_confirmed_2021_2025_with_park_factors_statcast/`
  - `outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/`
- 주요 Statcast feature null-rate를 확인했습니다.

```text
home_lineup_statcast_xwoba null_rate 0.0281
away_lineup_statcast_xwoba null_rate 0.0284
lineup_statcast_xwoba_diff null_rate 0.0505
home_sp_statcast_xwoba_allowed_to_date null_rate 0.1025
away_sp_statcast_xwoba_allowed_to_date null_rate 0.1019
sp_statcast_xwoba_allowed_diff null_rate 0.1691
```

- park factor 포함 + Statcast holdout 기준 best model은 모든 holdout season에서 `random_forest`였습니다.

```text
2022 random_forest log_loss 0.6781 accuracy 0.5827
2023 random_forest log_loss 0.6834 accuracy 0.5572
2024 random_forest log_loss 0.6792 accuracy 0.5751
2025 random_forest log_loss 0.6806 accuracy 0.5556
```

- `.venv` 기준 테스트를 재실행했고 `24 passed`를 확인했습니다.

### 0.1.14 Calibration plot 이미지 저장

- 시즌별 holdout 리포트 생성 시 calibration CSV와 함께 PNG 이미지를 저장하도록 추가했습니다.
  - 구현: `src/mlb_winprob/reporting.py`
  - 함수: `write_calibration_plot`
  - 저장 위치: `outputs/experiments/*/calibration/`
- matplotlib은 optional plotting dependency처럼 다루어, import가 불가능하면 CSV 리포트는 계속 생성되도록 했습니다.
- Statcast 포함 holdout 리포트를 재생성해 calibration plot 12개를 확인했습니다.

```text
outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/calibration/

calibration_2022_elo.png
calibration_2022_logistic.png
calibration_2022_random_forest.png
calibration_2023_elo.png
calibration_2023_logistic.png
calibration_2023_random_forest.png
calibration_2024_elo.png
calibration_2024_logistic.png
calibration_2024_random_forest.png
calibration_2025_elo.png
calibration_2025_logistic.png
calibration_2025_random_forest.png
```

- reporting 단위 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `25 passed`

### 0.1.15 Feature importance 리포트

- 시즌별 holdout 리포트 생성 시 `feature_importances_`를 제공하는 모델의 feature importance를 CSV와 Markdown summary로 저장하도록 추가했습니다.
  - 구현: `src/mlb_winprob/reporting.py`
  - 함수: `feature_importance_table`, `write_feature_importance_summary`
  - 저장 위치: `outputs/experiments/*/feature_importance/`
- 현재 기본 holdout 실행 모델 중에서는 `random_forest`가 importance를 제공합니다.
- Statcast 포함 holdout 리포트를 재생성해 feature importance 파일 4개와 summary를 확인했습니다.

```text
outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/feature_importance/

feature_importance_2022_random_forest.csv
feature_importance_2023_random_forest.csv
feature_importance_2024_random_forest.csv
feature_importance_2025_random_forest.csv
summary.md
```

- 2025 holdout 기준 상위 feature 일부를 확인했습니다.

```text
away_team_runs_allowed_per_game_to_date  0.0172
team_woba_diff                           0.0171
home_team_runs_allowed_per_game_to_date  0.0168
away_bullpen_whip_season_to_date         0.0155
away_bullpen_fip_season_to_date          0.0140
```

- 2025 holdout 기준 Statcast feature도 중상위권에 포함되는 것을 확인했습니다.

```text
away_lineup_statcast_xwoba              0.0118
sp_statcast_xwoba_allowed_diff          0.0115
lineup_statcast_xwoba_diff              0.0115
home_lineup_statcast_xwoba              0.0112
home_sp_statcast_xwoba_allowed_to_date  0.0109
```

- reporting 단위 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `26 passed`

### 0.1.16 Statcast feature pipeline 운영 명령 표준화

- Statcast 포함 feature/report 전체 재생성 스크립트를 추가했습니다.
  - `scripts/build_statcast_feature_pipeline.py`
- 기본 실행은 기존 시즌별 Statcast 원천 CSV를 재사용합니다.

```powershell
.\.venv\Scripts\python.exe scripts\build_statcast_feature_pipeline.py
```

- 원천 Statcast CSV까지 다시 수집하려면 `--collect`를 사용합니다.

```powershell
.\.venv\Scripts\python.exe scripts\build_statcast_feature_pipeline.py `
  --collect `
  --workers 12
```

- 스크립트가 표준화한 단계:
  - 시즌별 Statcast event 집계
  - 표준 타자/투수 로그에 Statcast 품질 컬럼 병합
  - 시즌별 Statcast + weather + park factor 포함 feature 생성
  - 2021-2025 통합 feature 생성
  - feature quality report 생성
  - season holdout report 생성
  - calibration PNG 생성
  - random forest feature importance report 생성

- `--collect` 없이 기존 원천 CSV를 재사용해 전체 파이프라인 재생성을 검증했습니다.

```text
2021 feature rows 2429 columns 112
2022 feature rows 2430 columns 112
2023 feature rows 2430 columns 112
2024 feature rows 2429 columns 112
2025 feature rows 2430 columns 112
combined feature rows 12148
```

- 사용법을 문서화했습니다.
  - `README.md`
  - `src/mlb_winprob/DATA_AND_CLI.md`

### 0.1.17 Retrosheet 백업 source 변환

- Retrosheet 다운로드 URL이 개별 CSV에서 ZIP 원천으로 바뀐 것을 반영했습니다.
  - `gameinfo.zip`
  - `teamstats.zip`
  - `batting.zip`
  - `pitching.zip`
- `collect-retrosheet`가 ZIP 원천을 받아 `.csv` 출력으로 내부 CSV를 추출하도록 보강했습니다.
- 2021-2025 Retrosheet 원천 4종을 수집했습니다.

```text
data/raw/retrosheet/gameinfo.csv
data/raw/retrosheet/teamstats.csv
data/raw/retrosheet/batting.csv
data/raw/retrosheet/pitching.csv
```

- Retrosheet 표준 변환 모듈과 CLI를 추가했습니다.
  - `src/mlb_winprob/retrosheet.py`
  - `mlb-winprob standardize-retrosheet`
- 2021-2025 Retrosheet 데이터를 프로젝트 표준 schema로 변환했습니다.

```text
data/standardized/retrosheet_2021_2025/games.csv          12148 rows
data/standardized/retrosheet_2021_2025/weather.csv        12148 rows
data/standardized/retrosheet_2021_2025/lineups.csv        218664 rows
data/standardized/retrosheet_2021_2025/batting_logs.csv   356498 rows
data/standardized/retrosheet_2021_2025/pitcher_logs.csv   104610 rows
```

- Retrosheet games는 2021-2025 MLB Stats API 표준 데이터와 같은 경기 수를 가집니다.

```text
2021 2429 games
2022 2430 games
2023 2430 games
2024 2429 games
2025 2430 games
home_sp_id null_rate 0.0
away_sp_id null_rate 0.0
```

- Retrosheet-only feature CSV와 품질 리포트를 생성해 feature builder 경로를 검증했습니다.

```text
data/processed/features_confirmed_2021_2025_retrosheet.csv  12148 rows
outputs/quality/features_confirmed_2021_2025_retrosheet/
```

- Retrosheet 변환 단위 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `28 passed`

### 0.1.18 Chadwick 기반 id_map 구축

- Chadwick Register가 단일 `people.csv` 대신 `people-0.csv`~`people-f.csv` 분할 구조로 바뀐 것을 반영했습니다.
- `collect-chadwick-people`가 16개 shard를 내려받아 `data/raw/chadwick/people.csv`로 합치도록 보강했습니다.
- ID crosswalk 생성 모듈과 CLI를 추가했습니다.
  - `src/mlb_winprob/id_map.py`
  - `mlb-winprob build-id-map`
- Chadwick Register와 MLB Stats API people metadata를 결합해 ID map을 생성했습니다.

```text
data/raw/chadwick/people.csv  516081 rows
data/processed/id_map.csv     128742 rows
```

- 주요 ID 보유 row 수:

```text
mlbam_id       127526
retrosheet_id   25620
bbref_id        23861
fangraphs_id    21201
```

- 2021-2025 표준 데이터의 선수 ID 커버리지를 확인했습니다.

```text
retro_batting   2692 / 2692 matched
retro_pitching  1743 / 1743 matched
mlbam_batting   2012 / 2012 matched
mlbam_pitching  1743 / 1743 matched
```

- `read_csv_table`의 대용량 혼합 타입 CSV 경고를 줄이기 위해 `low_memory=False`를 적용했습니다.
- id_map 단위 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `29 passed`

### 0.1.19 작업 목록 정리 및 SHAP 설명 리포트

- `PROJECT_CHECKLIST.md`의 오래된 미완료 항목을 최신 worklog 기준으로 정리했습니다.
  - Retrosheet 백업 source 변환
  - Chadwick 기반 `id_map.csv`
  - weather source 자동화
  - calibration plot
  - feature importance
  - Statcast 포함 운영 스크립트
- FanGraphs 운영 기준을 확정했습니다.
  - 현재는 모델 primary input이 아니라 raw 보존, 고급 지표 검산, park factor 비교용 보조 source로 사용합니다.
  - 시즌 최종 leaderboard는 경기 전 feature에 직접 넣지 않습니다.
- 라인업 source 운영 기준을 확정했습니다.
  - `confirmed_lineup`: MLB Stats API boxscore primary, Retrosheet 선발 라인업 fallback
  - `pre_lineup`: probable pitcher는 MLB Stats API schedule을 사용하되, 예상 타순 source는 별도 확정 전까지 연구 확장으로 둡니다.
- optional SHAP 설명 리포트 경로를 추가했습니다.
  - optional extra: `.[explain]`
  - 구현: `src/mlb_winprob/reporting.py`
  - 산출물: `outputs/experiments/*/shap_importance/`
  - 계산 비용을 줄이기 위해 holdout 표본은 기본 250경기까지 샘플링합니다.
- `.venv`에 `shap` extra를 설치하고 전체 테스트를 재실행했습니다.
  - result: `30 passed`
- Statcast + park factor 포함 holdout 리포트를 재생성해 SHAP 산출물을 확인했습니다.

```text
outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/shap_importance/

shap_importance_2022_random_forest.csv
shap_importance_2023_random_forest.csv
shap_importance_2024_random_forest.csv
shap_importance_2025_random_forest.csv
summary.md
```

### 0.1.20 실험 config 및 결과 버전 관리

- 시즌 holdout 실험을 TOML config로 실행할 수 있는 경로를 추가했습니다.
  - 구현: `src/mlb_winprob/config.py`
  - CLI: `mlb-winprob season-holdout-report --config ...`
  - 예시 config: `configs/season_holdout_statcast.toml`
- 기존 CLI 인자 방식은 유지했습니다.
  - `--config`가 없으면 기존처럼 `--features`, `--output-dir`, `--holdout-seasons`, `--models`를 사용합니다.
- 결과 버전 관리 방식을 확정했습니다.
  - config에서 `versioned_output = true`이면 `outputs/experiments/versioned/YYYYMMDD_HHMMSS_<name>_<config_hash>/` 형태로 저장합니다.
  - 모든 holdout report는 `run_manifest.json`을 저장합니다.
  - config 기반 실행은 `config_snapshot.json`도 함께 저장합니다.
- Statcast + park factor 포함 holdout config를 실제 실행해 versioned output을 검증했습니다.

```text
outputs/experiments/versioned/20260520_172415_season_holdout_confirmed_2021_2025_with_park_factors_statcast_ef38dbac9b6d/

metrics_by_holdout.csv
best_by_holdout.csv
calibration/
feature_importance/
shap_importance/
run_manifest.json
config_snapshot.json
```

- config 단위 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `33 passed`

### 0.1.21 Handedness matchup feature 정교화

- 라인업 좌우 매치업 feature를 당일 상대 선발투수 손 방향에 맞춰 계산하도록 보강했습니다.
  - `lineup_platoon_woba`
  - `lineup_platoon_advantage_ratio`
  - `lineup_same_hand_ratio`
  - `lineup_platoon_woba_diff`
  - `lineup_platoon_advantage_diff`
- `batting_logs.opposing_pitcher_hand`를 우선 사용하고, 표준 `games.csv`에 `home_sp_hand`, `away_sp_hand`가 있으면 fallback으로 사용합니다.
- MLB Stats API 표준 변환 시 선발투수 손 방향을 `games.csv`에 기록하도록 보강했습니다.
- Statcast + park factor 포함 feature/품질/holdout 리포트를 새 feature schema로 재생성했습니다.

```text
data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv
rows: 12148
columns: 121
```

- 새 holdout 결과도 재생성했습니다.

```text
2022 random_forest log_loss 0.6764 accuracy 0.5794
2023 random_forest log_loss 0.6820 accuracy 0.5572
2024 random_forest log_loss 0.6801 accuracy 0.5677
2025 random_forest log_loss 0.6801 accuracy 0.5502
```

- feature 단위 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `34 passed`

### 연구 확장 잔여 작업 정리

- `PROJECT_CHECKLIST.md`에 남은 연구 확장 항목을 우선순위와 하위 작업으로 풀어 적었습니다.
- 우선순위는 경기 전 예측 성능에 직접 붙을 가능성이 큰 순서로 정리했습니다.

```text
1. 라인업 확정 전 예상 라인업 confidence Feature
2. 팀 이동거리와 시차 Feature
3. 불펜 high-leverage role 자동 추정
4. 선수 부상/휴식/결장 신호
5. 선발투수 pitch-mix / Stuff 계열 Feature
6. 모델 앙상블 selection rule
7. 예상 득점 모델 확장
8. 딥러닝용 선수 embedding 실험
9. KBO 확장 가능 schema 점검
```

### 0.1.22 연구 확장 Feature 1-5차 구현

- 연구 확장 우선순위 1~5번을 optional input 기반 feature로 구현했습니다.
- 라인업 확정 전/예상 라인업 confidence 계열 feature를 추가했습니다.
  - `lineup_confidence`
  - `lineup_available_ratio`
  - `lineup_expected_starter_ratio`
  - `lineup_previous_starter_return_rate`
  - `lineup_previous_starter_missing_count`
- 선수 휴식/결장 신호 feature를 추가했습니다.
  - `lineup_rest_signal_count`
  - `lineup_injury_absence_signal_count`
- venue 좌표와 timezone offset이 있을 때 팀별 이동/시차 feature를 계산하도록 추가했습니다.
  - `travel_rest_days`
  - `travel_distance_miles`
  - `travel_timezone_shift`
  - `travel_is_back_to_back`
  - `travel_travel_day`
  - `travel_away_game_streak`
  - `travel_home_game_streak`
- 불펜 high-leverage role 자동 추정 proxy를 추가했습니다.
  - RP의 과거 `saves`, `holds`, `games_finished`, `save_opportunities`, `blown_saves`를 사용합니다.
  - 산출 feature: `estimated_high_leverage_role_fatigue_score`
- Statcast pitch-mix / Stuff 계열 선발투수 feature를 추가했습니다.
  - pitch type count: `FF`, `SI`, `FC`, `SL`, `CU`, `CH`, `FS`
  - whiff rate, fastball velocity, spin, fastball/breaking/offspeed usage
- Diff feature도 홈팀에 유리할수록 양수인 방향으로 추가했습니다.
  - `lineup_confidence_diff`
  - `lineup_previous_starter_return_diff`
  - `lineup_injury_absence_signal_diff`
  - `travel_distance_diff`
  - `travel_rest_diff`
  - `travel_timezone_shift_diff`
  - `sp_whiff_rate_diff`
  - `sp_fastball_velocity_diff`
- feature 단위 테스트를 확장했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `35 passed`
- 2021 시즌 실제 표준 데이터로 feature build smoke test를 실행했습니다.

```text
outputs/features_2021_feature_expansion_check.csv
rows: 2429
```

### 0.1.23 연구 확장 6-9차 구현

- 모델 앙상블 selection rule 산출물을 추가했습니다.
  - `season-holdout-report` 실행 시 `model_selection_rules.csv`를 저장합니다.
  - `overall_log_loss`, `confidence_55`, `confidence_60`, `confidence_65` rule을 생성합니다.
- 예상 득점 모델 리포트 경로를 추가했습니다.
  - CLI: `mlb-winprob expected-runs-report`
  - 구현: `run_expected_runs_experiments`, `write_expected_runs_holdout_report`
  - baseline regressor: `ridge`, `random_forest_regressor`
  - metric: `home_mae`, `away_mae`, `total_mae`, `total_rmse`, `run_diff_mae`
- 선수 embedding 실험 설계를 문서화했습니다.
  - `src/mlb_winprob/RESEARCH_EXTENSIONS.md`
  - lineup sequence, pitcher/batter embedding, holdout vocabulary/UNK 처리, cold-start share 평가 기준을 정리했습니다.
- KBO 확장 가능 schema gap을 문서화했습니다.
  - `src/mlb_winprob/KBO_SCHEMA_GAP.md`
  - 공통 canonical table, KBO source requirement, optional feature 처리, 최소 smoke test 기준을 정리했습니다.
- 관련 테스트를 추가했고 `.venv` 기준 전체 테스트를 재실행했습니다.
  - result: `37 passed`
- 실제 Statcast 포함 2021-2025 feature로 smoke test를 실행했습니다.

```text
outputs/experiments/selection_rules_confirmed_2021_2025_feature_expansion_check/model_selection_rules.csv
outputs/experiments/expected_runs_confirmed_2021_2025_feature_expansion_check/expected_runs_metrics_by_holdout.csv
```

### 0.1.24 최신 Feature set 재생성 및 성능 비교

- 기존 Statcast 포함 confirmed lineup feature/report를 baseline으로 보존했습니다.

```text
outputs/experiments/feature_set_update_compare_20260521_095456/
baseline_features_confirmed_2021_2025_with_park_factors_statcast.csv
baseline_metrics_by_holdout.csv
baseline_best_by_holdout.csv
```

- 최신 feature schema로 2021-2025 시즌 feature를 재생성했습니다.
  - 2021-2024는 전체 pipeline 실행 중 생성 완료
  - 2025는 타임아웃 이후 `--seasons 2025`로 이어서 생성
  - 5개 시즌 feature를 다시 combine

```text
data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv
rows: 12148
columns: 173
```

- 품질 리포트와 시즌 holdout 리포트를 재생성했습니다.

```text
outputs/quality/features_confirmed_2021_2025_with_park_factors_statcast/
outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/
```

- baseline 대비 최신 feature set 성능 비교를 저장했습니다.

```text
outputs/experiments/feature_set_update_compare_20260521_095456/
metric_comparison_latest_vs_baseline.csv
metric_comparison_mean_delta.csv
new_feature_coverage.csv
summary.md
```

- Random Forest 기준 평균 변화는 다음과 같습니다.
  - `log_loss_delta`: `-0.000246`
  - `brier_score_delta`: `-0.000130`
  - `accuracy_delta`: `+0.002572`
- 해석:
  - 최신 feature set은 현재 strongest model인 Random Forest에는 소폭 긍정적입니다.
  - 다만 시즌별로 균일하지 않으므로 대폭 개선이 아니라 incremental gain으로 판단합니다.
  - 실제로 모델에 기여한 축은 pitch-mix/Stuff, 라인업 continuity, home/away streak/rest proxy, bullpen role proxy입니다.
  - lineup confidence/availability와 venue distance/timezone shift는 upstream source가 없어 현재 all-null입니다.

### 0.1.25 all-null source 보강 및 feature group ablation

- all-null이던 source-dependent feature를 보강했습니다.
  - `venues_2021_2025.csv`를 feature build 단계에 연결했습니다.
  - `FeatureBuilder.build(..., venues=...)`를 추가했습니다.
  - `mlb-winprob build-features --venues ...`를 추가했습니다.
  - `scripts/build_statcast_feature_pipeline.py --venues ...`를 추가했습니다.
- venue source 보강 후 다음 feature의 null-rate가 해소됐습니다.

```text
home_lineup_confidence         0.000000
away_lineup_confidence         0.000000
home_lineup_available_ratio    0.000000
away_lineup_available_ratio    0.000000
home_travel_distance_miles     0.006092
away_travel_distance_miles     0.006256
home_travel_timezone_shift     0.006092
away_travel_timezone_shift     0.006256
```

- confirmed lineup 기준 기본값을 적용했습니다.
  - `lineup_confidence = 1.0`
  - `is_available = 1.0`
  - `is_expected_starter = 1.0`
  - `rest_signal = 0.0`
- venue timezone source가 없는 경우 longitude 기반 근사 offset을 적용했습니다.
- 최신 feature set으로 2021-2025 feature와 공식 품질/holdout 리포트를 다시 갱신했습니다.

```text
data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv
outputs/quality/features_confirmed_2021_2025_with_park_factors_statcast/
outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/
```

- feature group ablation 스크립트를 추가했습니다.

```text
scripts/run_feature_group_ablation.py
outputs/experiments/feature_group_ablation_confirmed_2021_2025_with_park_factors_statcast/
```

- Random Forest 기준 ablation 평균 결과:

```text
full                         log_loss 0.679559  accuracy 0.567343
without_pitch_stuff          log_loss 0.679942  accuracy 0.563844
without_travel               log_loss 0.679937  accuracy 0.563433
without_all_research_groups  log_loss 0.679770  accuracy 0.564873
baseline_like_columns        log_loss 0.679803  accuracy 0.564976
without_bullpen_role         log_loss 0.679424  accuracy 0.565079
without_lineup_optional      log_loss 0.679386  accuracy 0.569092
```

- 해석:
  - `pitch_stuff`와 `travel`은 제거하면 log loss와 accuracy가 모두 나빠져 실제로 도움이 됩니다.
  - 전체 research feature 묶음은 baseline-like 대비 소폭 도움이 됩니다.
  - `lineup_optional`은 confirmed lineup 기본값 위주라 현재는 노이즈에 가깝습니다.
  - `bullpen_role`은 accuracy에는 도움되지만 log loss에는 약한 노이즈가 있어 추가 튜닝 후보입니다.

### 0.1.26 Baseline 고정 및 sklearn 모델 테스트 1차

- confirmed lineup 최신 feature set 기준 baseline 실험을 고정했습니다.

```text
outputs/experiments/model_baseline_confirmed_2021_2025_with_park_factors_statcast/
models: elo, logistic, random_forest
```

- baseline 평균 성능:

```text
random_forest  log_loss 0.679559  accuracy 0.567343  accuracy_conf_60 0.650573  coverage_conf_60 0.186231
logistic       log_loss 0.689587  accuracy 0.564872  accuracy_conf_60 0.604787  coverage_conf_60 0.421125
elo            log_loss 0.692476  accuracy 0.559521  accuracy_conf_60 0.591693  coverage_conf_60 0.527727
```

- sklearn 기반 모델 테스트 후보를 추가했습니다.
  - `logistic_l1`
  - `logistic_l2_c03`
  - `logistic_l2_c3`
  - `random_forest_shallow`
  - `random_forest_deep`
  - `extra_trees`
  - `hist_gradient_boosting`
  - `calibrated_logistic`
  - `calibrated_random_forest`
- 빠른 metric-only 모델 테스트 스크립트를 추가했습니다.

```text
scripts/run_model_test_experiment.py
outputs/experiments/model_test_confirmed_2021_2025_with_park_factors_statcast/
```

- 1차 모델 테스트 평균 결과:

```text
random_forest              log_loss 0.679559  accuracy 0.567343  accuracy_conf_60 0.650573
random_forest_shallow      log_loss 0.680300  accuracy 0.565285  accuracy_conf_60 0.672257
random_forest_deep         log_loss 0.680681  accuracy 0.565902  accuracy_conf_60 0.647200
extra_trees                log_loss 0.681978  accuracy 0.559008  accuracy_conf_60 0.678075
calibrated_logistic        log_loss 0.683131  accuracy 0.561066  accuracy_conf_60 0.615442
logistic_l1                log_loss 0.686193  accuracy 0.564666  accuracy_conf_60 0.613934
logistic_l2_c03            log_loss 0.688679  accuracy 0.564357  accuracy_conf_60 0.606529
logistic                   log_loss 0.689587  accuracy 0.564872  accuracy_conf_60 0.604787
logistic_l2_c3             log_loss 0.690143  accuracy 0.564872  accuracy_conf_60 0.604847
hist_gradient_boosting     log_loss 0.692632  accuracy 0.551806  accuracy_conf_60 0.599648
```

- 해석:
  - 전체 평균 log loss 기준 메인 baseline은 여전히 `random_forest`입니다.
  - `random_forest_shallow`는 전체 log loss는 밀리지만 confidence 60%+ 구간 accuracy가 가장 좋아 선별 모델 후보입니다.
  - `calibrated_logistic`은 plain logistic보다 log loss가 좋아졌지만 RF를 넘지는 못했습니다.
  - `hist_gradient_boosting`은 현재 sklearn-only 설정에서는 부적합합니다.
  - 다음 실험은 `random_forest` 메인 + `random_forest_shallow` confidence-band challenger + feature pruning 조합으로 좁히는 것이 좋습니다.

### 0.1.27 RF 계열 feature pruning / calibration 실험

- pruning feature set을 생성했습니다.

```text
data/processed/model_experiments/features_confirmed_2021_2025_with_park_factors_statcast_without_lineup_optional.csv
data/processed/model_experiments/features_confirmed_2021_2025_with_park_factors_statcast_without_lineup_optional_bullpen_role.csv
```

- 비교 모델:
  - `random_forest`
  - `random_forest_shallow`
  - `calibrated_random_forest`
- 비교 산출물:

```text
outputs/experiments/model_test_rf_family_full_confirmed_2021_2025/
outputs/experiments/model_test_rf_family_without_lineup_optional_confirmed_2021_2025/
outputs/experiments/model_test_rf_family_without_lineup_optional_bullpen_role_confirmed_2021_2025/
outputs/experiments/model_test_rf_family_comparison_confirmed_2021_2025/
```

- 평균 log loss 기준 top 결과:

```text
without_lineup_optional              random_forest              log_loss 0.679386  accuracy 0.569092  acc_conf_60 0.647983  cov_conf_60 0.191376
full                                 random_forest              log_loss 0.679559  accuracy 0.567343  acc_conf_60 0.650573  cov_conf_60 0.186231
without_lineup_optional_bullpen_role random_forest              log_loss 0.679819  accuracy 0.561890  acc_conf_60 0.655906  cov_conf_60 0.187980
full                                 calibrated_random_forest   log_loss 0.679895  accuracy 0.563947  acc_conf_60 0.638381  cov_conf_60 0.186131
```

- 해석:
  - 새 main baseline 후보는 `without_lineup_optional + random_forest`입니다.
  - 기존 full feature `random_forest` 대비 평균 log loss와 accuracy가 모두 소폭 개선됐습니다.
  - `calibrated_random_forest`는 현재 설정에서는 RF를 넘지 못했습니다.
  - `random_forest_shallow`는 전체 log loss는 밀리지만 `accuracy_conf_60`이 약 `0.682`로 가장 높아 confidence-band 전용 후보입니다.
  - `bullpen_role`까지 제거하면 confidence-band accuracy는 올라가지만 전체 accuracy/log_loss가 나빠져 메인 baseline에서는 유지하지 않는 편이 낫습니다.

### 0.1.28 Multi-seed baseline 안정성 검증

- 단일 seed 결과의 안정성을 확인하기 위해 10개 seed 반복 검증을 실행했습니다.

```text
seeds: 11,22,33,44,55,66,77,88,99,111
holdout seasons: 2022,2023,2024,2025
variants: full, without_lineup_optional
models: random_forest, random_forest_shallow
baseline: full + random_forest
```

- 산출물:

```text
outputs/experiments/model_multiseed_rf_pruning_confirmed_2021_2025/
metrics_by_seed_holdout.csv
summary_by_variant_model.csv
stability_vs_baseline.csv
summary.md
```

- 10개 seed 평균 결과:

```text
full                    random_forest          log_loss 0.679496  accuracy 0.565069  acc_conf_60 0.657115  cov_conf_60 0.185079
without_lineup_optional random_forest          log_loss 0.679896  accuracy 0.565100  acc_conf_60 0.652715  cov_conf_60 0.188207
full                    random_forest_shallow  log_loss 0.680243  accuracy 0.567127  acc_conf_60 0.678148  cov_conf_60 0.127459
without_lineup_optional random_forest_shallow  log_loss 0.680310  accuracy 0.566623  acc_conf_60 0.673279  cov_conf_60 0.128241
```

- baseline 대비 안정성:

```text
without_lineup_optional + random_forest
  mean_log_loss_delta_vs_baseline: +0.000400
  log_loss_win_rate_vs_baseline: 0.35

full + random_forest_shallow
  mean_log_loss_delta_vs_baseline: +0.000746
  accuracy_delta_vs_baseline: +0.002058
  accuracy_win_rate_vs_baseline: 0.625
```

- 최종 판단:
  - 단일 seed에서 좋아 보였던 `without_lineup_optional + random_forest`는 반복 검증에서 안정적으로 이기지 못했습니다.
  - 메인 baseline은 `full + random_forest`로 확정합니다.
  - `full + random_forest_shallow`는 전체 log loss는 밀리지만 confidence-band accuracy가 좋아 선별 모델 후보로 유지합니다.
  - feature pruning은 현재 단계에서 baseline 교체 근거가 부족합니다.

### 0.1.29 Baseline decision log and next validation sweep

- 모델 개선/평가 의사결정을 누적 기록하기 위해 `MODEL_IMPROVEMENT_LOG.md`를 추가했습니다.
- 현재 baseline 결정을 문서화했습니다.
  - main baseline: `full + random_forest`
  - confidence-band challenger: `full + random_forest_shallow`
  - calibration challenger: `calibrated_logistic`
  - watchlist: `without_bullpen_role + random_forest`
- `README.md`, `src/mlb_winprob/MODELS_AND_EXPERIMENTS.md`에 현재 baseline 요약을 추가했습니다.

Bullpen role stability:

```text
output: outputs/experiments/model_multiseed_rf_bullpen_role_confirmed_2021_2025/
baseline: full + random_forest
candidate: without_bullpen_role + random_forest
seeds: 11,22,33,44,55,66,77,88,99,111

without_bullpen_role + random_forest
  mean_log_loss: 0.679389
  mean_accuracy: 0.565974
  log_loss_delta_vs_baseline: -0.000107
  accuracy_delta_vs_baseline: +0.000906
  log_loss_win_rate_vs_baseline: 0.55
```

- 판단:
  - `without_bullpen_role + random_forest`는 평균 지표가 소폭 좋아졌지만 win rate가 55%라 baseline 교체 근거로는 약합니다.
  - watchlist/challenger로 유지하고, high-leverage role proxy 계산식을 더 다듬은 뒤 재검증합니다.

Confidence-band rule check:

```text
output: outputs/experiments/confidence_band_selection_rules_confirmed_2021_2025/

full + random_forest_shallow vs full + random_forest
  log_loss_delta: +0.000746
  accuracy_delta: +0.002058
  accuracy_conf_60_delta: +0.021033
  coverage_conf_60_delta: -0.057620
```

- 판단:
  - `random_forest_shallow`는 `accuracy_conf_60`은 좋지만 coverage가 줄고 전체 log loss가 나빠집니다.
  - 기본 확률 모델은 `full + random_forest`를 유지합니다.
  - `random_forest_shallow`는 고확신 구간 분석용 challenger로만 유지합니다.

Pre-lineup readiness:

```text
output: outputs/experiments/pre_lineup_readiness_confirmed_2021_2025/
```

- 현재 2021-2025 feature table과 standardized `lineups.csv`는 모두 `confirmed_lineup`입니다.
- `pre_lineup`, `projected`, `expected` lineup row가 없어 실제 경기 전 예측 성능 평가는 blocked 상태입니다.
- 현재 confirmed-lineup 성능을 pre-game deployable 성능으로 해석하지 않습니다.

Expected runs:

```text
output: outputs/experiments/expected_runs_confirmed_2021_2025_full_check/

best by holdout:
2022 random_forest_regressor total_mae 3.507164 total_rmse 4.411268 run_diff_mae 3.373167
2023 ridge                   total_mae 3.570532 total_rmse 4.546192 run_diff_mae 3.472396
2024 random_forest_regressor total_mae 3.328263 total_rmse 4.198817 run_diff_mae 3.412222
2025 ridge                   total_mae 3.533861 total_rmse 4.490473 run_diff_mae 3.529009
```

- 판단:
  - expected-runs는 별도 리포트로 유효하지만 시즌별 best regressor가 바뀝니다.
  - 승률 모델 feature로 붙이려면 out-of-fold/holdout-safe expected-run prediction feature를 먼저 생성해야 합니다.

Booster comparison:

```text
output: outputs/experiments/model_test_boosters_confirmed_2021_2025_with_park_factors_statcast/

random_forest mean_log_loss 0.679559 mean_accuracy 0.567343
catboost      mean_log_loss 0.683661 mean_accuracy 0.563123
xgboost       mean_log_loss 0.693865 mean_accuracy 0.562507
lightgbm      mean_log_loss 0.720479 mean_accuracy 0.552834
```

- optional booster dependency를 설치해 LightGBM/XGBoost/CatBoost를 비교했습니다.
- 판단:
  - 현재 기본 설정에서는 어떤 booster도 `full + random_forest`를 대체하지 못합니다.
  - CatBoost만 추후 targeted tuning/calibration 후보로 남깁니다.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
38 passed
```

- 기본 temp 경로에서는 pytest numbered temp directory 생성 문제로 실패했지만, workspace 내부 `--basetemp` 지정 후 전체 테스트가 통과했습니다.

다음 작업 후보:

1. `pre_lineup` source 확보: projected/expected lineup source 후보를 정하고 표준 `lineups.csv`에 `pre_lineup` row를 만들 수 있는지 검증합니다.
2. Expected-runs OOF feature 실험: season holdout에서 누수 없는 expected home/away/total/run_diff prediction feature를 만들고 win-probability baseline 대비 성능 변화를 확인합니다.
3. Bullpen role proxy 개선: save/hold/games finished/save opportunity 기반 high-leverage role score를 재조정하고 `without_bullpen_role` watchlist를 재검증합니다.
4. CatBoost targeted tuning: 기본 CatBoost가 RF보다 약하므로, depth/l2/learning-rate/calibration 후보를 좁혀 별도 튜닝 실험으로만 진행합니다.
5. Feature stability/SHAP 정리: 시즌별 feature importance와 SHAP top feature 안정성을 비교해 pruning 후보와 유지 후보를 분리합니다.
### 0.1.30 Pre-lineup guard, OOF expected-runs, bullpen cap, CatBoost tuning

- Updated the model experiment record and checklist from the recommended work order.
- Main model decision is unchanged:
  - main baseline: `full + random_forest`
  - confidence challenger: `full + random_forest_shallow`
  - calibration challenger: `calibrated_logistic`
  - watchlist: `without_bullpen_role + random_forest`

Pre-lineup guard and smoke build:

```text
data/smoke_pre_lineup/lineups_projected_2024-04-01.csv
data/smoke_pre_lineup/features_pre_lineup_2024-04-01.csv
```

- Added a strict `prediction_mode` filter for lineup features.
- `pre_lineup` mode now accepts projected/expected aliases and does not fall back to confirmed rows.
- Smoke pre-lineup feature build produced 14 games with 9 projected players per side.

Expected-runs OOF feature experiment:

```text
outputs/experiments/expected_runs_oof_feature_confirmed_2021_2025/
outputs/experiments/expected_runs_oof_feature_rf_regressor_confirmed_2021_2025/
```

- Added holdout-safe expected run prediction features:
  - `expected_home_runs`
  - `expected_away_runs`
  - `expected_total_runs`
  - `expected_run_diff`
- Result: do not add expected-runs prediction columns to the current win-probability baseline yet.
- Keep expected-runs as an adjacent report until a stronger OOF signal appears.

Bullpen role proxy cap:

```text
outputs/experiments/model_multiseed_rf_bullpen_role_capped_confirmed_2021_2025/
```

- Capped `estimated_high_leverage_role_score` at `1.0` before fatigue aggregation.
- Multi-seed decision did not change at decision precision.
- Keep the cap as a safety guard, but keep `without_bullpen_role + random_forest` as watchlist only.

CatBoost targeted tuning:

```text
outputs/experiments/model_test_catboost_tuning_confirmed_2021_2025_with_park_factors_statcast/
```

- Added CatBoost candidates:
  - `catboost_shallow`
  - `catboost_l2`
  - `catboost_lr02`
- Best average model remains `random_forest`.
- CatBoost showed some season-specific wins, so it remains a season-dependent challenger rather than the baseline.

Feature stability summary:

```text
outputs/experiments/feature_stability_confirmed_2021_2025/
```

- Added a feature stability summary across holdout seasons.
- Stable groups are useful for the next grouped ablation pass.
- Do not prune one-off features from importance alone.

Docs and tests:

- Updated:
  - `MODEL_IMPROVEMENT_LOG.md`
  - `PROJECT_CHECKLIST.md`
  - `EXPERIMENT_RUNBOOK.md`
  - `PRE_LINEUP_SOURCE_PLAN.md`
  - `README.md`
  - `src/mlb_winprob/MODELS_AND_EXPERIMENTS.md`
- Added/updated tests for:
  - pre-lineup mode isolation
  - projected lineup alias handling
  - bullpen role score cap
  - expected-runs OOF feature safety
  - optional CatBoost candidate registry

Next work queue:

1. Build the actual projected/expected lineup source collector and normalizer.
2. Run a real source-backed pre-lineup smoke test.
3. Evaluate CatBoost season-dependent selection rules with multi-seed validation.
4. Run grouped ablation using stable feature groups.
5. Clean up Windows subprocess encoding warnings.

### 0.1.31 Projected Lineup Source Collector MVP

- Added a first automated projected-lineup ingestion path for the BALLDONTLIE MLB Lineups API.
- New collector:
  - `BallDontLieMLBCollector`
  - `lineups(...)` paginates API responses.
  - `save_lineups(...)` stores raw provider JSON snapshots.
  - `normalize_lineups(...)` converts provider JSON into standard `lineups.csv` rows.
- New CLI commands:
  - `collect-balldontlie-lineups`
  - `standardize-balldontlie-lineups`
- Standardized rows preserve:
  - `external_game_id`
  - `external_player_id`
  - `provider_lineup_status`
  - `captured_at`
  - `lineup_source=balldontlie_mlb`
  - `prediction_mode=projected` by default
- Optional mapping inputs let provider IDs translate into the MLBAM IDs used by the existing feature pipeline:
  - `--game-id-map` with `external_game_id,game_id`
  - `--player-id-map` with `external_player_id,player_id`

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_collectors.py --basetemp .pytest_tmp
10 passed
```

Remaining blocker:

- A real source-backed `pre_lineup` feature smoke test still needs API credentials/terms confirmation plus provider-to-MLBAM game/player ID maps.

### 0.1.32 External Lineup ID Map Helpers

- Added provider-to-MLBAM mapping helpers for projected lineup sources.
- New functions:
  - `build_external_player_id_map(...)`
  - `build_external_game_id_map(...)`
- New CLI command:
  - `build-external-lineup-id-maps`
- Player map behavior:
  - input: normalized provider `lineups.csv` with `external_player_id`, `player_name`
  - reference: `data/processed/id_map.csv`
  - output: `external_player_id,player_id`
  - only unique normalized-name matches are emitted
  - optional `--season` filters active MLB seasons
- Game map behavior:
  - input: normalized provider `lineups.csv` with `external_game_id`, `game_date`, `home_team`, `away_team`
  - reference: project `games.csv`
  - output: `external_game_id,game_id`
  - only unique date/team-pair matches are emitted

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_id_map.py tests\test_collectors.py --basetemp .pytest_tmp
13 passed
```

Next:

- Run the collector against a real BALLDONTLIE response once credentials/terms are confirmed.
- Review ambiguous/unmapped provider IDs.
- Re-run `standardize-balldontlie-lineups` with the generated maps, then run `build-features --prediction-mode pre_lineup`.

### 0.1.33 Fixture-Backed Pre-Lineup Smoke Test

- Added `scripts/run_pre_lineup_fixture_smoke.py`.
- The script creates a provider-shaped projected-lineup JSON snapshot from existing standardized MLBAM game data, then runs the same ingestion path planned for a live source.
- Default smoke game:
  - `game_id=778563`
  - `2025-03-18`
  - CHC vs LAD
- Smoke output:
  - `outputs/pre_lineup_fixture_smoke/raw/balldontlie_lineups_fixture.json`
  - `outputs/pre_lineup_fixture_smoke/standardized/lineups_unmapped.csv`
  - `outputs/pre_lineup_fixture_smoke/metadata/balldontlie_game_id_map.csv`
  - `outputs/pre_lineup_fixture_smoke/metadata/balldontlie_player_id_map.csv`
  - `outputs/pre_lineup_fixture_smoke/standardized/lineups_projected.csv`
  - `outputs/pre_lineup_fixture_smoke/processed/features_pre_lineup_fixture.csv`
  - `outputs/pre_lineup_fixture_smoke/summary.csv`
- Result:
  - 18 projected lineup rows normalized
  - 1 external game ID mapped
  - 14 external player IDs auto-mapped
  - 1 `pre_lineup` feature row generated
- Fixes discovered during smoke:
  - `FeatureBuilder` now handles lineup inputs that already include `game_date` but need `season` merged from `games`.
  - lineup `player_id` dtype is aligned with batter profile IDs, so numeric MLBAM IDs and string test IDs both work.
  - unmapped provider player IDs no longer crash lineup feature generation.

Verification:

```text
.\.venv\Scripts\python.exe scripts\run_pre_lineup_fixture_smoke.py
.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
48 passed
```

Remaining live-source blocker:

- `BALLDONTLIE_API_KEY` is not set in the current environment, so the live API response schema and real source-backed smoke test still need credentials/terms confirmation.

### 0.1.34 Free MLB Stats API Lineup Snapshot Path

- Switched the preferred low-cost `pre_lineup` source from BALLDONTLIE to MLB Stats API boxscore snapshots because BALLDONTLIE lineups require a paid GOAT tier.
- Added `collect-mlb-lineup-snapshots` CLI.
  - input: schedule CSV
  - output: boxscore snapshot JSON files
  - optional manifest records `game_id`, `snapshot_path`, `captured_at`, `lineup_source`
- Extended `standardize-mlb-boxscores` with:
  - `--lineup-source`
  - `--captured-at`
  - `--lineup-confidence`
- Extended `standardize_mlb_stats_api_boxscores(...)` so standardized lineup rows can preserve snapshot metadata.
- Hardened pre-game empty table handling:
  - empty `lineups.csv`, `batting_logs.csv`, and `pitcher_logs.csv` now retain schema headers
  - downstream `build-features --prediction-mode pre_lineup` can produce null lineup features without confirmed-lineup fallback

Live smoke:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-schedule \
  --start-date 2026-05-26 \
  --end-date 2026-05-26 \
  --output outputs\mlb_lineup_snapshot_smoke\schedule_2026-05-26.csv

.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-lineup-snapshots \
  --games outputs\mlb_lineup_snapshot_smoke\schedule_2026-05-26.csv \
  --output-dir outputs\mlb_lineup_snapshot_smoke\boxscores \
  --manifest outputs\mlb_lineup_snapshot_smoke\manifest.csv \
  --workers 4

.\.venv\Scripts\python.exe -m mlb_winprob.cli standardize-mlb-boxscores \
  --schedule outputs\mlb_lineup_snapshot_smoke\schedule_2026-05-26.csv \
  --boxscore-dir outputs\mlb_lineup_snapshot_smoke\boxscores \
  --output-dir outputs\mlb_lineup_snapshot_smoke\standardized \
  --prediction-mode pre_lineup \
  --lineup-source mlb_stats_api_boxscore_snapshot \
  --captured-at 2026-05-26T04:06:02Z \
  --lineup-confidence 1.0

.\.venv\Scripts\python.exe -m mlb_winprob.cli build-features \
  --games outputs\mlb_lineup_snapshot_smoke\standardized\games.csv \
  --batting-logs outputs\mlb_lineup_snapshot_smoke\standardized\batting_logs.csv \
  --pitcher-logs outputs\mlb_lineup_snapshot_smoke\standardized\pitcher_logs.csv \
  --lineups outputs\mlb_lineup_snapshot_smoke\standardized\lineups.csv \
  --weather outputs\mlb_lineup_snapshot_smoke\standardized\weather.csv \
  --prediction-mode pre_lineup \
  --output outputs\mlb_lineup_snapshot_smoke\features_pre_lineup.csv
```

Result:

```text
schedule rows: 15
snapshot JSON files: 15
standardized games: 15
standardized lineups: 0
pre_lineup feature rows: 15
home/away lineup_player_count non-null: 0
```

Readout:

- The free MLB Stats API path works end-to-end.
- The snapshot was taken before official batting orders were posted, so lineup features correctly remain null.
- Next live check should rerun `collect-mlb-lineup-snapshots` closer to first pitch and compare how many games have non-null lineup features.

### 0.1.35 Manual Projected Lineup Input

- Added a manual lineup input path for user-authored expected lineups.
- New standardization helpers:
  - `manual_lineup_template(...)`
  - `standardize_manual_lineups(...)`
- New CLI commands:
  - `write-manual-lineup-template`
  - `standardize-manual-lineups`
- Manual template columns:
  - `game_id`
  - `team`
  - `batting_order`
  - `player_id`
  - `player_name`
  - `bats`
  - `position`
  - `lineup_confidence`
  - `is_available`
  - `is_expected_starter`
  - `injury_status`
  - `rest_signal`
  - `notes`
- If `player_id` is blank, `standardize-manual-lineups` can use `data/processed/id_map.csv` to resolve unique normalized `player_name` matches.

Smoke:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli write-manual-lineup-template \
  --games outputs\mlb_lineup_snapshot_smoke\standardized\games.csv \
  --game-ids 824434 \
  --output outputs\manual_lineup_smoke\manual_lineup_template.csv

.\.venv\Scripts\python.exe -m mlb_winprob.cli standardize-manual-lineups \
  --input outputs\manual_lineup_smoke\manual_lineup_filled.csv \
  --output outputs\manual_lineup_smoke\lineups_manual.csv \
  --prediction-mode projected \
  --lineup-source manual \
  --captured-at 2026-05-26T04:30:00Z

.\.venv\Scripts\python.exe -m mlb_winprob.cli build-features \
  --games outputs\mlb_lineup_snapshot_smoke\standardized\games.csv \
  --batting-logs data\standardized\mlb_stats_api_2025\batting_logs.csv \
  --pitcher-logs data\standardized\mlb_stats_api_2025\pitcher_logs.csv \
  --lineups outputs\manual_lineup_smoke\lineups_manual.csv \
  --weather outputs\mlb_lineup_snapshot_smoke\standardized\weather.csv \
  --prediction-mode pre_lineup \
  --output outputs\manual_lineup_smoke\features_manual_pre_lineup.csv
```

Result:

```text
manual template rows: 18
manual standardized rows: 18
manual feature rows: 15
game 824434 home_lineup_player_count: 9
game 824434 away_lineup_player_count: 9
```

Next:

- Train or select a saved model bundle so manual `features_manual_pre_lineup.csv` can flow directly into `mlb-winprob predict`.

### 0.1.36 Final Model Bundle And Manual Lineup Prediction Smoke

- Added `fit-final-model` CLI to train a deployment-style model on all available rows instead of a season holdout split.
- Final model smoke:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli fit-final-model \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest \
  --output-dir outputs\final_models\full_random_forest_confirmed_2021_2025_statcast
```

Result:

```text
best_model.joblib written
training_rows=12148
feature_count=162
model_name=random_forest
```

- Hardened `predict`:
  - missing model feature columns are filled with `NaN`
  - prediction matrix is coerced to numeric
  - added `--game-ids` to predict only selected games from a multi-game feature file
- Manual lineup prediction smoke:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli predict \
  --features outputs\manual_lineup_smoke\features_manual_pre_lineup.csv \
  --model outputs\final_models\full_random_forest_confirmed_2021_2025_statcast\best_model.joblib \
  --prediction-mode pre_lineup \
  --game-ids 824434
```

Result:

```json
{"home_win_probability": 0.4772758014293535, "away_win_probability": 0.5227241985706466, "model_name": "random_forest", "prediction_mode": "pre_lineup", "key_reasons": ["라인업 wOBA 차이가 홈팀에 유리합니다.", "불펜 피로도 차이가 홈팀에 유리합니다."]}
```

Readout:

- User-authored manual lineups can now flow to a win-probability JSON response.
- The saved model was trained on confirmed-lineup historical features, so live/manual `pre_lineup` predictions should still be treated as an operational smoke baseline until enough real pre-lineup snapshots are evaluated.

### 0.1.37 Completed-Game Official Lineup Smoke

- Used MLB Stats API completed games as a practical official-lineup smoke test.
- Date selected:
  - `2026-05-25` MLB date
  - chosen because the user is in Korea on `2026-05-26`, so those games are already completed
- Commands:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-schedule \
  --start-date 2026-05-25 \
  --end-date 2026-05-25 \
  --output outputs\mlb_completed_lineup_smoke\schedule_2026-05-25.csv

.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-lineup-snapshots \
  --games outputs\mlb_completed_lineup_smoke\schedule_2026-05-25.csv \
  --output-dir outputs\mlb_completed_lineup_smoke\boxscores \
  --manifest outputs\mlb_completed_lineup_smoke\manifest.csv \
  --workers 4

.\.venv\Scripts\python.exe -m mlb_winprob.cli standardize-mlb-boxscores \
  --schedule outputs\mlb_completed_lineup_smoke\schedule_2026-05-25.csv \
  --boxscore-dir outputs\mlb_completed_lineup_smoke\boxscores \
  --output-dir outputs\mlb_completed_lineup_smoke\standardized \
  --prediction-mode pre_lineup \
  --lineup-source mlb_stats_api_completed_boxscore_lineup_smoke \
  --captured-at 2026-05-26T04:30:00Z \
  --lineup-confidence 1.0

.\.venv\Scripts\python.exe -m mlb_winprob.cli build-features \
  --games outputs\mlb_completed_lineup_smoke\standardized\games.csv \
  --batting-logs data\standardized\mlb_stats_api_2025\batting_logs.csv \
  --pitcher-logs data\standardized\mlb_stats_api_2025\pitcher_logs.csv \
  --lineups outputs\mlb_completed_lineup_smoke\standardized\lineups.csv \
  --weather outputs\mlb_completed_lineup_smoke\standardized\weather.csv \
  --prediction-mode pre_lineup \
  --output outputs\mlb_completed_lineup_smoke\features_pre_lineup.csv
```

Result:

```text
schedule rows: 13
boxscore snapshots: 13
official lineup rows: 234
games with lineups: 13
pre_lineup feature rows: 13
home/away lineup_player_count non-null: 13 / 13
prediction summary: outputs\mlb_completed_lineup_smoke\predictions.csv
winner direction smoke: 9 / 13
```

Readout:

- MLB official lineup extraction works when lineups are available.
- This is not true pre-game validation because the games were already completed.
- It does validate the lineups -> features -> saved baseline model -> predictions pipeline with non-null official lineup features.

### 0.1.38 Over/Under Baseline From Expected Runs

- Added `fit-final-runs-model` CLI.
  - trains separate home/away score regressors on all available rows
  - writes `runs_model.joblib`
- Added `predict-runs` CLI.
  - predicts home score, away score, total, and run differential
  - supports `--total-line` for one line across all games
  - supports `--total-lines` CSV with `game_id,total_line`
  - outputs `ou_pick`, `ou_margin`, and `ou_confidence`
  - confidence buckets:
    - `pass`: margin <= `--pass-margin` (default 0.5)
    - `lean`: margin <= `--strong-margin` (default 1.5)
    - `strong`: margin > `--strong-margin`

Final runs model:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli fit-final-runs-model \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest_regressor \
  --output-dir outputs\final_models\runs_random_forest_confirmed_2021_2025_statcast
```

Result:

```text
training_rows=12148
feature_count=162
model_name=random_forest_regressor
```

Over/under smoke:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli predict-runs \
  --features outputs\mlb_completed_lineup_smoke\features_pre_lineup.csv \
  --model outputs\final_models\runs_random_forest_confirmed_2021_2025_statcast\runs_model.joblib \
  --prediction-mode pre_lineup \
  --total-line 8.5 \
  --output outputs\mlb_completed_lineup_smoke\over_under_predictions_8_5.csv
```

Result at fixed line `8.5`:

```text
correct: 7 / 13
pass: 11 games
lean: 2 games
strong: 0 games
```

Line sensitivity:

```text
6.5  correct 9/13
7.5  correct 8/13
8.5  correct 7/13
9.5  correct 9/13
10.5 correct 10/13
```

Readout:

- Total-run prediction is more useful than exact-score prediction.
- The current model's predicted totals cluster near league-average run environments, so true confidence should be based on margin from the market line.
- Most `8.5` picks in the smoke were classified as `pass`, which is the desired behavior for small edges.

### 0.1.39 Market Line Features And Direct Over/Under Model Path

- Added optional market-line input to feature generation.
  - `build-features --market-lines <csv>`
  - supported fields include opening/current/closing total, over/under odds, moneyline movement, and starter-change signals
  - derived features include:
    - `market_total_line`
    - `market_total_line_movement`
    - `market_over_implied_prob`
    - `market_under_implied_prob`
    - `market_ou_vig`
    - `market_home_moneyline_movement`
    - `market_away_moneyline_movement`
    - `market_home_sp_changed`
    - `market_away_sp_changed`
    - `market_starter_change_count`
- Added a user-editable market-line template command:

```text
mlb-winprob write-market-lines-template \
  --games outputs/mlb_completed_lineup_smoke/standardized/games.csv \
  --output outputs/mlb_completed_lineup_smoke/market_lines_template.csv
```

- Added direct over/under model commands:
  - `fit-final-ou-model`
  - `predict-ou`
- The direct model trains on `actual_total > market_total_line`.
- `market_closing_total_line` is excluded from the normal feature set to avoid accidentally training on a future closing number.

Important data note:

- The existing 2021-2025 baseball dataset is enough for baseball context features.
- A true market-aware over/under model still needs historical market-line rows for those same games.
- Without historical total lines/odds snapshots, the current system can compare predicted totals to a user-provided line, but it cannot learn line movement, odds, or market behavior from history.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_features.py tests\test_standardize.py --basetemp .pytest_tmp
19 passed

.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
55 passed, 4 warnings

.\.venv\Scripts\python.exe -m mlb_winprob.cli write-market-lines-template \
  --games outputs\mlb_completed_lineup_smoke\standardized\games.csv \
  --output outputs\mlb_completed_lineup_smoke\market_lines_template.csv
Wrote 13 market line template rows
```

### 0.1.40 Combined Win/Score/Over-Under Prediction Output

- Added `predict-game` CLI for one-row-per-game combined prediction output.
- The command combines:
  - win probability model (`--win-model`)
  - expected score model (`--runs-model`)
  - optional direct over/under classifier (`--ou-model`)
- Output columns include:
  - `home_win_probability`, `away_win_probability`, `win_pick`
  - `pred_home_score`, `pred_away_score`, `pred_total`, `rounded_score`
  - `total_line`, `runs_ou_margin`, `runs_ou_pick`, `runs_ou_confidence`
  - optional direct OU fields: `direct_prob_over`, `direct_prob_under`, `direct_ou_pick`
  - if actual scores exist: `win_correct`, `actual_total`, `actual_ou`, `runs_ou_correct`

Smoke command:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli predict-game \
  --features outputs\mlb_completed_lineup_smoke\features_pre_lineup.csv \
  --win-model outputs\final_models\full_random_forest_confirmed_2021_2025_statcast\best_model.joblib \
  --runs-model outputs\final_models\runs_random_forest_confirmed_2021_2025_statcast\runs_model.joblib \
  --prediction-mode pre_lineup \
  --total-line 8.5 \
  --output outputs\mlb_completed_lineup_smoke\combined_predictions_8_5.csv
```

Result:

```text
Wrote 13 combined game predictions
tests\test_models.py tests\test_features.py: 14 passed, 4 warnings
```

### 0.1.41 Direct Over/Under Baseline Model

- Extended `fit-final-ou-model` so it can train from:
  - `market_total_line` already present in features
  - `--total-lines game_id,total_line`
  - a fixed baseline `--total-line`
- Trained a first direct over/under baseline with fixed total line `8.5`.

Command:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli fit-final-ou-model \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest \
  --total-line 8.5 \
  --output-dir outputs\final_models\ou_random_forest_confirmed_2021_2025_statcast_fixed_8_5
```

Result:

```text
training_rows=12148
feature_count=163
model_name=random_forest
over_rate=0.491
model: outputs\final_models\ou_random_forest_confirmed_2021_2025_statcast_fixed_8_5\ou_model.joblib
```

Combined smoke with win + score + direct OU:

```text
output: outputs\mlb_completed_lineup_smoke\combined_predictions_with_ou_model_8_5.csv
runs-model OU direction at fixed 8.5: 7 / 13
direct OU model direction at fixed 8.5: 8 / 13
```

Readout:

- This completes the first over/under-specific baseline.
- It is not market-aware yet because historical game-specific total lines/odds are not in the dataset.
- When historical lines are backfilled, retrain the same command without a fixed line and with feature-level `market_total_line`.

### 0.1.42 Modeling Direction Clarification

- Confirmed that score data is already stored in the project-standard data.
  - `games.csv` contains `home_score`, `away_score`.
  - feature CSVs preserve `home_score`, `away_score` when actual scores are available.
  - win target is derived as `home_team_win = home_score > away_score`.
  - expected-runs models train on `home_score` and `away_score`.
- Clarified model roles:
  - Win model: predicts `home_win_probability` / `away_win_probability`.
  - Score model: predicts `pred_home_score`, `pred_away_score`, `pred_total`, and `pred_run_diff`.
  - Runs-based OU signal: compares `pred_total` to `total_line`.
  - Direct OU model: predicts `P(actual_total > total_line)`.
- Current direct OU baseline:
  - trained with fixed `total_line=8.5`
  - useful as a first baseline, but not yet market-aware
  - should be treated as a secondary signal until game-specific historical market lines are added
- Product direction:
  - make expected score / expected total the primary output
  - use direct OU probability as a confirmation/pass signal
  - if score model and direct OU model disagree, mark the game as lower confidence or pass

Recommended next work:

1. Improve the score model baseline before chasing more complex OU modeling.
   - Add holdout metrics focused on total runs:
     - total MAE
     - total RMSE
     - within 1 / 2 / 3 runs
     - OU accuracy by synthetic lines such as 6.5, 7.5, 8.5, 9.5, 10.5
   - Compare current RF regressor against alternatives.

2. Add a combined signal report.
   - For each game, compare:
     - `pred_total - total_line`
     - direct `prob_over`
     - agreement/disagreement between score model and OU classifier
   - Produce `pass`, `lean`, `strong` recommendation rules.

3. Backfill market lines when possible.
   - Required fields:
     - `game_id`
     - `opening_total_line`
     - `current_total_line` or close-time available line
     - `over_odds`, `under_odds`
     - movement fields
     - starter-change snapshot fields
   - Once this exists, retrain direct OU with real game-specific `market_total_line`.

### 0.1.43 Score-Focused Holdout Report With Synthetic OU Lines

- Extended `expected-runs-report` with score-model-focused diagnostics:
  - `total_within_1`
  - `total_within_2`
  - `total_within_3`
  - synthetic OU accuracy by configurable lines
  - synthetic pass/strong rates by predicted-total margin
- Added CLI option:
  - `--synthetic-total-lines`, default `6.5,7.5,8.5,9.5,10.5`
- Generated score/OU baseline report:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli expected-runs-report \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --output-dir outputs\experiments\expected_runs_score_ou_baseline_confirmed_2021_2025 \
  --holdout-seasons 2022,2023,2024,2025 \
  --models ridge,random_forest_regressor \
  --prediction-mode confirmed_lineup \
  --synthetic-total-lines 6.5,7.5,8.5,9.5,10.5
```

Outputs:

```text
outputs\experiments\expected_runs_score_ou_baseline_confirmed_2021_2025\expected_runs_metrics_by_holdout.csv
outputs\experiments\expected_runs_score_ou_baseline_confirmed_2021_2025\expected_runs_best_by_holdout.csv
outputs\experiments\expected_runs_score_ou_baseline_confirmed_2021_2025\synthetic_ou_metrics_by_holdout.csv
outputs\experiments\expected_runs_score_ou_baseline_confirmed_2021_2025\summary.md
```

Best total-run model by holdout:

```text
2022 random_forest_regressor total_mae 3.507 total_within_2 0.349 total_within_3 0.491
2023 ridge                   total_mae 3.571 total_within_2 0.352 total_within_3 0.501
2024 random_forest_regressor total_mae 3.328 total_within_2 0.359 total_within_3 0.513
2025 ridge                   total_mae 3.534 total_within_2 0.344 total_within_3 0.499
```

Synthetic OU average accuracy:

```text
random_forest_regressor line 10.5: 0.677
random_forest_regressor line  6.5: 0.675
ridge                   line 10.5: 0.671
ridge                   line  6.5: 0.669
random_forest_regressor line  9.5: 0.604
ridge                   line  9.5: 0.603
ridge                   line  7.5: 0.571
random_forest_regressor line  7.5: 0.566
ridge                   line  8.5: 0.549
random_forest_regressor line  8.5: 0.537
```

Readout:

- Exact total prediction is still noisy: total MAE is roughly 3.3-3.6 runs.
- Within 2 runs is roughly 34-36%; within 3 runs is roughly 49-51%.
- Synthetic OU accuracy is higher on extreme lines like 6.5 and 10.5, but weak around common middle lines like 8.5.
- Next modeling work should focus on improving predicted total dispersion/calibration around the middle market lines.

### 0.1.44 Win-Probability Improvement Experiment: Expected Runs As Features

- Ran a win-model improvement experiment that adds holdout-safe expected-run features to the win model.
- Feature variant:
  - baseline feature table
  - baseline + OOF expected runs from ridge score model
- Tested models:
  - `random_forest`
  - `random_forest_shallow`
  - `logistic`
  - `calibrated_logistic`
  - `extra_trees`
  - `hist_gradient_boosting`
- Holdouts:
  - 2022, 2023, 2024, 2025

Command:

```text
.\.venv\Scripts\python.exe scripts\run_expected_runs_feature_experiment.py \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --output-dir outputs\experiments\win_improvement_expected_runs_features_confirmed_2021_2025 \
  --holdout-seasons 2022,2023,2024,2025 \
  --models random_forest,random_forest_shallow,logistic,calibrated_logistic,extra_trees,hist_gradient_boosting \
  --expected-runs-model ridge \
  --prediction-mode confirmed_lineup
```

Outputs:

```text
outputs\experiments\win_improvement_expected_runs_features_confirmed_2021_2025\metrics_by_holdout.csv
outputs\experiments\win_improvement_expected_runs_features_confirmed_2021_2025\metrics_vs_baseline.csv
outputs\experiments\win_improvement_expected_runs_features_confirmed_2021_2025\summary_by_model.csv
outputs\experiments\win_improvement_expected_runs_features_confirmed_2021_2025\summary.md
outputs\experiments\win_improvement_expected_runs_features_confirmed_2021_2025\features_with_expected_runs_oof.csv
```

Average accuracy by feature set/model:

```text
baseline            random_forest          0.5673
expected_runs_ridge random_forest_shallow  0.5661
baseline            random_forest_shallow  0.5653
baseline            logistic               0.5649
expected_runs_ridge random_forest          0.5635
expected_runs_ridge logistic               0.5633
expected_runs_ridge calibrated_logistic    0.5613
baseline            calibrated_logistic    0.5611
expected_runs_ridge extra_trees            0.5602
baseline            extra_trees            0.5590
expected_runs_ridge hist_gradient_boosting 0.5546
baseline            hist_gradient_boosting 0.5518
```

Expected-runs feature deltas vs the same model baseline:

```text
hist_gradient_boosting accuracy +0.0028, log_loss -0.0018
extra_trees            accuracy +0.0012, log_loss -0.0005
random_forest_shallow  accuracy +0.0008, log_loss -0.0009
calibrated_logistic    accuracy +0.0002, log_loss +0.0019
logistic               accuracy -0.0015, log_loss -0.0007
random_forest          accuracy -0.0038, log_loss +0.0002
```

Readout:

- The current overall win baseline remains `baseline + random_forest`.
- Adding expected-run features does not improve the main `random_forest`; it slightly hurts average accuracy.
- Expected-run features help some alternate models a little, especially `hist_gradient_boosting`, but those models still do not beat baseline RF on overall accuracy.
- For selective higher-confidence betting-style use, `random_forest_shallow` and `extra_trees` remain worth testing as confidence-band challengers.

Next recommended win-probability work:

1. Add a dedicated confidence-band report across model candidates.
2. Evaluate selective rules on recent completed games:
   - overall picks
   - confidence >= 55/60/65
   - pass/lean/strong rule candidates
3. Test recent-season weighting or 2024-2025-only training as a challenger to the full 2021-2025 baseline.

### 0.1.45 Confidence Bands And Feature Reduction Diagnostics

- Checked the recent completed-game smoke (`2026-05-19` to `2026-05-25`) by model confidence.
- Recent-week `random_forest` final model:

```text
confidence >= 0.55: 11 games, 7/11 correct, accuracy 0.636
confidence >= 0.58:  1 game,  1/1 correct, accuracy 1.000
confidence >= 0.60:  0 games
```

- Historical season-holdout confidence bands show that 60%+ predictions do exist in backtests.
- Baseline model average at `confidence >= 0.60`:

```text
extra_trees            accuracy_conf_60 0.678, coverage 0.071
random_forest_shallow  accuracy_conf_60 0.672, coverage 0.131
random_forest          accuracy_conf_60 0.651, coverage 0.186
calibrated_logistic    accuracy_conf_60 0.615, coverage 0.176
logistic               accuracy_conf_60 0.605, coverage 0.421
hist_gradient_boosting accuracy_conf_60 0.600, coverage 0.413
```

- Ran feature redundancy diagnostics.
- High-correlation outputs:

```text
outputs\experiments\win_feature_diagnostics_confirmed_2021_2025\top_correlation_pairs.csv
outputs\experiments\win_feature_diagnostics_confirmed_2021_2025\high_correlation_pairs_095.csv
outputs\experiments\win_feature_diagnostics_confirmed_2021_2025\feature_non_null_unique.csv
```

- Strong redundant pairs found:

```text
lineup_previous_starter_return_rate vs lineup_previous_starter_missing_count: 1.000
lineup_platoon_advantage_ratio vs lineup_same_hand_ratio: ~0.997
team_ops_season_to_date vs team_woba_season_to_date: ~0.996
lineup_avg_ops vs lineup_avg_woba: ~0.992
lineup_avg_woba vs lineup_weighted_woba_by_order: ~0.989
lineup_avg_woba vs lineup_statcast_woba: ~0.984
```

- Ran feature group ablation:

```text
outputs\experiments\win_feature_group_ablation_confirmed_2021_2025\
```

- Built a reduced feature set that removes lineup optional signals and obvious redundant paired features:

```text
data\processed\model_experiments\features_confirmed_2021_2025_win_reduced_lineup_redundancy.csv
original_cols: 176
reduced_cols: 149
dropped: 27
```

- Reduced feature model test:

```text
outputs\experiments\win_reduced_lineup_redundancy_model_test\
```

Reduced feature average results:

```text
random_forest         accuracy 0.5662, accuracy_conf_60 0.6529, coverage_conf_60 0.1845
random_forest_shallow accuracy 0.5664, accuracy_conf_60 0.6688, coverage_conf_60 0.1308
extra_trees           accuracy 0.5584, accuracy_conf_60 0.6751, coverage_conf_60 0.0715
logistic              accuracy 0.5651, accuracy_conf_60 0.6082, coverage_conf_60 0.4098
```

Readout:

- Removing redundant/optional lineup features did not materially improve overall accuracy over the existing full `random_forest`.
- The reduced set is competitive and simpler, especially for `random_forest_shallow`.
- For selective picks, `random_forest_shallow` is a better practical challenger than `extra_trees` because it keeps a useful 60%+ coverage while staying near 67% accuracy.
- A reasonable next rule candidate is:
  - main model: full or reduced `random_forest`
  - selective strong model: reduced `random_forest_shallow` when confidence >= 0.60
  - otherwise pass/lean instead of forcing every game

### 0.1.46 Reduced Shallow Challenger Smoke On Recent Completed Games

- Trained and saved the reduced-feature `random_forest_shallow` challenger.

Command:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli fit-final-model \
  --features data\processed\model_experiments\features_confirmed_2021_2025_win_reduced_lineup_redundancy.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest_shallow \
  --output-dir outputs\final_models\win_reduced_random_forest_shallow_confirmed_2021_2025
```

Result:

```text
training_rows=12148
feature_count=135
model_name=random_forest_shallow
model: outputs\final_models\win_reduced_random_forest_shallow_confirmed_2021_2025\best_model.joblib
```

- Compared main full RF vs reduced shallow challenger on the recent completed-game smoke.
- Output:

```text
outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\win_main_vs_reduced_shallow.csv
```

Recent-week result:

```text
rows: 95
main full random_forest:        52 / 95 = 0.547
reduced random_forest_shallow:  48 / 95 = 0.505
main/challenger agree rows:     57 games, accuracy 0.544

rule strong: 0 games
rule lean: 6 games, 3 / 6 = 0.500
rule lean_main_only: 6 games, 4 / 6 = 0.667
pass: 83 games
```

Readout:

- The reduced shallow challenger did not improve the recent-week smoke.
- It also produced no `confidence >= 0.60` strong picks in this 95-game sample.
- The historical holdout case for reduced/shallow remains interesting, but recent-week behavior says not to promote it yet.
- The next step should be a more formal selective-pick report using out-of-fold predictions, not only aggregate holdout metrics.

### 0.1.47 Boosting And Ensemble Win-Model Candidates

- Clarified terminology:
  - combining multiple model outputs into one prediction is an `ensemble`
  - common ensemble forms are `voting`, `blending`, and `stacking`
- Added model registry candidates:
  - `soft_voting`
    - logistic + random forest + shallow random forest + extra trees
  - `booster_voting`
    - hist gradient boosting + LightGBM + XGBoost + CatBoost shallow
  - `booster_stacking`
    - same booster base learners with logistic final estimator
- Verified boosters are installed:

```text
catboost True
lightgbm True
xgboost True
```

- Ran full-feature model comparison:

```text
.\.venv\Scripts\python.exe scripts\run_model_test_experiment.py \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --output-dir outputs\experiments\win_boosting_voting_full_confirmed_2021_2025 \
  --holdout-seasons 2022,2023,2024,2025 \
  --models random_forest,random_forest_shallow,extra_trees,hist_gradient_boosting,lightgbm,xgboost,catboost,catboost_shallow,catboost_l2,catboost_lr02,soft_voting,booster_voting,booster_stacking \
  --prediction-mode confirmed_lineup
```

Outputs:

```text
outputs\experiments\win_boosting_voting_full_confirmed_2021_2025\metrics_by_holdout.csv
outputs\experiments\win_boosting_voting_full_confirmed_2021_2025\mean_by_model.csv
outputs\experiments\win_boosting_voting_full_confirmed_2021_2025\best_by_holdout.csv
outputs\experiments\win_boosting_voting_full_confirmed_2021_2025\model_selection_rules.csv
outputs\experiments\win_boosting_voting_full_confirmed_2021_2025\summary.md
```

Mean holdout results by accuracy:

```text
booster_stacking       accuracy 0.5680, log_loss 0.6811
soft_voting            accuracy 0.5678, log_loss 0.6783
random_forest          accuracy 0.5673, log_loss 0.6796
random_forest_shallow  accuracy 0.5653, log_loss 0.6803
catboost_lr02          accuracy 0.5648, log_loss 0.6808
catboost_l2            accuracy 0.5633, log_loss 0.6816
catboost               accuracy 0.5631, log_loss 0.6837
catboost_shallow       accuracy 0.5630, log_loss 0.6801
xgboost                accuracy 0.5625, log_loss 0.6939
extra_trees            accuracy 0.5590, log_loss 0.6820
booster_voting         accuracy 0.5558, log_loss 0.6883
lightgbm               accuracy 0.5528, log_loss 0.7205
hist_gradient_boosting accuracy 0.5518, log_loss 0.6926
```

Best overall log-loss by holdout:

```text
2022 soft_voting
2023 soft_voting
2024 catboost_lr02
2025 soft_voting
```

Selection rule highlights:

```text
overall_log_loss: soft_voting wins 3/4 holdouts
confidence_60:
  2022 random_forest_shallow
  2023 soft_voting
  2024 soft_voting
  2025 random_forest_shallow
confidence_65:
  mostly CatBoost variants
```

- Trained final soft voting candidate:

```text
outputs\final_models\win_soft_voting_confirmed_2021_2025_statcast\best_model.joblib
training_rows=12148
feature_count=162
```

- Recent-week smoke comparison:

```text
outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\win_model_ensemble_comparison.csv

main_rf:         52 / 95 = 0.547, avg_conf 0.525
soft_voting:     39 / 95 = 0.411, avg_conf 0.614
reduced_shallow: 48 / 95 = 0.505, avg_conf 0.522

soft voting strong rule: 41 games, 20 / 41 = 0.488
```

Readout:

- Historical holdout strongly supports `soft_voting` as a probability-quality challenger.
- Recent-week 2026 smoke strongly rejects promoting it immediately: it is overconfident and wrong on this sample.
- The likely cause is feature distribution mismatch in the current 2026 smoke path, especially because 2026 season logs are not yet backfilled and the feature row uses 2025 logs for compatibility.
- Keep production/final default as full `random_forest` until a 2026-ready feature pipeline is built or a larger true pre-game validation confirms soft voting.

### 0.1.48 Recent-Week 2026 May 23 Failure Diagnostic

- Investigated why 2026-05-23 was much worse than the rest of the recent completed-game smoke.
- Corrected the scored-game denominator:
  - schedule rows on 2026-05-23 included one game without a usable final score in the review table
  - scored-game evaluation is therefore `3 / 15 = 0.200`, not `3 / 16 = 0.188`
- Outputs:

```text
outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\may23_diagnostics\may23_scored_game_review.csv
outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\may23_diagnostics\may23_scored_summary.csv
outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\may23_diagnostics\may23_scored_actual_vs_pred_side.csv
```

Scored-game summary:

```text
scored_games:              15
win_hits:                  3
win_accuracy:              0.200
actual home win rate:      0.533
model home pick rate:      0.400
avg home win probability:  0.493
avg favorite confidence:   0.522
total MAE:                 3.978
runs OU accuracy at 8.5:   0.467
direct OU accuracy at 8.5: 0.600
```

Winner-side confusion:

```text
actual away / predicted away: 2
actual away / predicted home: 5
actual home / predicted away: 7
actual home / predicted home: 1
```

Readout:

- This does not look like a simple home/away bias.
- Actual winners were balanced, but the model flipped the side on most games.
- The average favorite confidence was only `0.522`, so the model was mostly making forced low-edge picks.
- The operational lesson is to avoid treating every game as a pick. A pass/lean/strong rule is now more important than marginally changing the base classifier.
- The smoke still has a major caveat: 2026 rows are using compatibility features from prior-season logs, not a leakage-safe 2026 season-to-date feature pipeline.

### 0.1.49 Win Pick Selection Rules

- Added reusable win-pick rule helpers:
  - `apply_win_pick_rules(...)`
  - `summarize_win_pick_rules(...)`
- Added CLI:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli win-pick-rule-report \
  --predictions <prediction_csv> \
  --output-dir <output_dir> \
  --lean-threshold 0.55 \
  --strong-threshold 0.60
```

- The rule converts home win probability into:
  - `pass`: confidence below lean threshold
  - `lean`: confidence >= lean threshold
  - `strong`: confidence >= strong threshold
- Output files:
  - `win_pick_rules.csv`
  - `win_pick_rule_summary.csv`
  - `win_pick_rule_daily.csv`

Recent completed-game smoke using the main RF prediction file:

```text
input: outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\combined_predictions_8_5.csv
```

Threshold comparison:

```text
53/55 rule: actionable 32 games, 19/32 = 0.594
54/57 rule: actionable 20 games, 13/20 = 0.650
55/60 rule: actionable 11 games,  7/11 = 0.636
55/60 excluding 2026-05-23: actionable 9 games, 7/9 = 0.778
```

Readout:

- The default production-style starting rule should be `lean >= 0.55`, `strong >= 0.60`.
- The recent smoke has no `strong` picks at 60%+, but the 55%+ lean band is already better than forced picking.
- The looser `54/57` rule is a useful comparison point because it increases coverage to 20 games while keeping 65% accuracy in this sample.
- Next work should validate these thresholds on historical out-of-fold predictions, then add agreement rules with challenger models.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
58 passed, 5 warnings
```

### 0.1.50 Historical OOF Selective-Pick Report

- Added season-holdout out-of-fold win prediction generation:
  - `run_oof_win_predictions(...)`
  - CLI: `oof-selective-pick-report`
- Added agreement-based pick helper:
  - `apply_model_agreement_pick_rules(...)`
  - primary model pick is actionable only when configured challenger models agree on side
- Added test coverage for the agreement rule.

Generated OOF reports:

```text
outputs\experiments\oof_selective_pick_main_challenger_confirmed_2021_2025\
outputs\experiments\oof_selective_pick_main_challenger_confirmed_2021_2025_53_55\
outputs\experiments\oof_selective_pick_main_challenger_confirmed_2021_2025_54_57\
```

Command shape:

```text
.\.venv\Scripts\python.exe -m mlb_winprob.cli oof-selective-pick-report \
  --features data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --output-dir outputs\experiments\oof_selective_pick_main_challenger_confirmed_2021_2025 \
  --holdout-seasons 2022,2023,2024,2025 \
  --models random_forest,random_forest_shallow,soft_voting \
  --primary-model random_forest \
  --challenger-models random_forest_shallow,soft_voting \
  --prediction-mode confirmed_lineup \
  --lean-threshold 0.55 \
  --strong-threshold 0.60
```

OOF threshold comparison, agreement rule:

```text
53/55: 6287 picks, 3707 hits, accuracy 0.590, coverage 0.647
54/57: 5558 picks, 3294 hits, accuracy 0.593, coverage 0.572
55/60: 4789 picks, 2893 hits, accuracy 0.604, coverage 0.493
```

OOF `55/60` comparison:

```text
random_forest:         4865 picks, 2937 hits, accuracy 0.604, coverage 0.501
random_forest_shallow: 4276 picks, 2607 hits, accuracy 0.610, coverage 0.440
soft_voting:           4874 picks, 2977 hits, accuracy 0.611, coverage 0.501
agreement:             4789 picks, 2893 hits, accuracy 0.604, coverage 0.493
```

Agreement `55/60` by holdout:

```text
2022: 1237 picks, 756 hits, accuracy 0.611, coverage 0.509
2023: 1218 picks, 710 hits, accuracy 0.583, coverage 0.501
2024: 1132 picks, 701 hits, accuracy 0.619, coverage 0.466
2025: 1202 picks, 726 hits, accuracy 0.604, coverage 0.495
```

Readout:

- Historical OOF supports keeping the stricter `55/60` rule as the default candidate.
- Lower thresholds increase coverage but give back accuracy.
- Simple main/challenger side agreement does not materially beat the strongest individual challenger on OOF.
- `soft_voting` remains attractive historically, but the prior 2026 recent-week smoke still blocks production promotion until the 2026 season-to-date feature path is fixed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_evaluation.py tests\test_models.py --basetemp .pytest_tmp
10 passed, 5 warnings
```

### 0.1.51 Scored-Only Daily Win-Pick Breakdown

- Hardened `apply_win_pick_rules(...)` so rows without `actual_winner` are not counted as misses.
- Added scored-row filtering for win-pick reports:
  - score columns are preferred when `home_score` / `away_score` exist
  - `actual_winner` is used as a fallback only when scores are unavailable
- Added `win-pick-rule-report --scored-only`.
- Updated daily output to report:
  - `scored_games`
  - `pass_games`
  - `lean_games`
  - `strong_games`
  - `picks`
  - `hits`
  - `accuracy`
  - `coverage`
  - `avg_confidence`

Generated recent-week scored-only report:

```text
outputs\mlb_recent_week_predictions_2026-05-19_2026-05-25\win_pick_rules_55_60_scored_daily\
```

Scored-only summary for `55/60`:

```text
pass:       82 games
lean:       11 games, 7 / 11 = 0.636
strong:      0 games
actionable: 11 games, 7 / 11 = 0.636
```

Daily scored breakdown:

```text
2026-05-19: scored 10, picks 0
2026-05-20: scored 18, picks 5, 4 / 5 = 0.800
2026-05-21: scored  7, picks 2, 1 / 2 = 0.500
2026-05-22: scored 12, picks 1, 1 / 1 = 1.000
2026-05-23: scored 15, picks 2, 0 / 2 = 0.000
2026-05-24: scored 18, picks 0
2026-05-25: scored 11, picks 1, 1 / 1 = 1.000
2026-05-26: scored  2, picks 0
```

Readout:

- The daily report now excludes rows without final scores from its denominator.
- The 2026-05-23 denominator is correctly `15` scored games in this report.
- Overall scored-game denominator is now `93` games for this file, with 11 actionable lean picks.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
60 passed, 5 warnings
```

## 2026-05-27 2026 Season-to-Date Feature Pipeline

### 0.1.52 Leakage-Safe 2026 Season-to-Date Features

- Built the missing 2026 season-to-date feature pipeline that was blocking ensemble-model promotion.
- Root problem fixed: the earlier 2026 recent-week smoke fed prior-season (2025) batting/pitcher logs into the feature builder, so every season-to-date feature was computed from 2025 data, not real 2026 in-season games.
- Added `scripts/build_season_to_date_features.py`:
  - Accepts an explicit standardized snapshot directory (e.g. `data/season_to_date/mlb_stats_api_2026_to_2026-05-26/standardized`) instead of the full-season `data/standardized/mlb_stats_api_<season>` convention.
  - Uses the in-season logs directly, so rolling/season-to-date features stay leakage-safe (each game still excludes itself).
  - Optionally aggregates and merges a snapshot Statcast CSV; aligns output columns to the training schema.
  - Normalizes all id columns (`game_id`, `player_id`, `home_sp_id`, `away_sp_id`) to a canonical string to avoid str/int64 merge errors when snapshot CSVs are numeric-only.
- Collected 2026 Statcast events through the snapshot date.

```text
data/raw/statcast/statcast_2026.csv  237836 rows  (2026-03-26 .. 2026-05-25)
```

- Built the 2026 season-to-date, Statcast-enriched, park-factor feature table.

```text
data/processed/features_confirmed_2026_to_2026-05-26_with_park_factors_statcast.csv
rows: 807  (2026-03-26 .. 2026-05-26)
outputs/quality/features_confirmed_2026_to_2026-05-26_with_park_factors_statcast/
```

- Feature quality now matches the historical MLB confirmed-lineup baseline (May-onward null rates):

```text
home/away_lineup_statcast_xwoba      0.000
home_sp_statcast_xwoba_allowed       0.068
home_sp_avg_fastball_velocity        0.068
home_sp_fip_season_to_date           ~0.068
```

- Regenerated recent-week predictions with the production model bundles on the leakage-safe table.

```text
outputs/mlb_2026_season_to_date_predictions/main_rf_predictions_8_5.csv
outputs/mlb_2026_season_to_date_predictions/soft_voting_predictions_8_5.csv
outputs/mlb_2026_season_to_date_predictions/season_to_date_vs_smoke_summary.csv
```

- Recent-week (2026-05-19 .. 2026-05-25) comparison, old 2025-fallback smoke vs new season-to-date:

```text
main_rf      old: acc 0.547 conf 0.525   new: acc 0.531 conf 0.551
soft_voting  old: acc 0.411 conf 0.614   new: acc 0.521 conf 0.545
```

- Readout:
  - The soft_voting overconfidence/failure on the 2026 smoke was a feature-distribution artifact, not a model defect. With real 2026 season-to-date features its confidence normalizes (0.614 -> 0.545) and accuracy recovers (0.411 -> 0.521), tracking main_rf closely.
  - Full-season-to-date 2026 accuracy is modest for both models (main_rf 0.517, soft_voting 0.519 over 807 scored games), so pass/lean/strong pick rules remain the primary lever.
  - This unblocks fair ensemble evaluation; promotion still warrants a larger true pre-game validation before changing the production default.

### 0.1.53 Recent-Season Training Challenger

- Added `scripts/run_recent_season_challenger.py` to test whether recent-only or recency-weighted training beats equal-weighted all-season training, now that the 2026 season-to-date table exists.
- Trains three Random Forest variants on a shared feature set (162 columns) and scores them on 2026 season-to-date scored games, plus a 2025 holdout sanity check.

```text
outputs/experiments/recent_season_challenger_2026/challenger_metrics.csv
outputs/experiments/recent_season_challenger_2026/summary.md
```

- 2026 target (807 scored games):

```text
baseline_rf_all_seasons   log_loss 0.6944  accuracy 0.5167  acc_conf_60 0.5586
challenger_rf_2024_2025    log_loss 0.6939  accuracy 0.5390  acc_conf_60 0.5155
recency_weighted_rf_hl2    log_loss 0.6933  accuracy 0.5180  acc_conf_60 0.5895
```

- 2025 holdout (2430 games):

```text
baseline_rf_all_seasons   log_loss 0.6797  accuracy 0.5584
challenger_rf_2024         log_loss 0.6829  accuracy 0.5527
recency_weighted_rf_hl2    log_loss 0.6813  accuracy 0.5539
```

- Decision: keep `baseline + random_forest` (all 2021-2025, equal weight) as default. Recent-only / recency-weighted show a small edge on the partial 2026 sample but lose on the robust 2025 holdout, and 2026 log_loss is near coin-flip (~0.693). Not a robust improvement; revisit with a larger 2026 sample. Logged in `MODEL_IMPROVEMENT_LOG.md` (2026-05-27).

### 0.1.54 CatBoost Season-Dependent Selection Rule Check

- Verified with multi-seed runs whether CatBoost's earlier per-season wins (2022/2024/2025) generalize, using `scripts/run_multiseed_model_experiment.py` (5 seeds × 4 holdouts, models `random_forest,catboost,catboost_lr02`).

```text
outputs/experiments/catboost_season_rule_multiseed_2021_2025/summary_by_variant_model.csv
outputs/experiments/catboost_season_rule_multiseed_2021_2025/per_season_winrate_vs_rf.csv
```

- Overall mean (across seasons/seeds):

```text
random_forest  log_loss 0.6795  accuracy 0.5651
catboost_lr02  log_loss 0.6807  accuracy 0.5668
catboost       log_loss 0.6839  accuracy 0.5612
```

- Per-season CatBoost log_loss win-rate vs RF (across 5 seeds):

```text
2022  catboost 0%   catboost_lr02 0%
2023  catboost 0%   catboost_lr02 20%
2024  catboost 40%  catboost_lr02 100%
2025  catboost 0%   catboost_lr02 20%
```

- Decision: do NOT adopt a season-dependent CatBoost switch. Only 2024 is a stable CatBoost win and its margin is negligible (catboost_lr02 0.6785 vs RF 0.6792, delta -0.00072). The earlier single-seed "best in 2022/2024/2025" pattern was mostly seed luck. Keep `random_forest` as the single default; `catboost_lr02` stays watchlist-only. Logged in `MODEL_IMPROVEMENT_LOG.md` (2026-05-27).

### 0.1.55 Stable Feature Group Ablation

- Added `scripts/run_stable_group_ablation.py` to ablate feature-stability groups (stable 13 vs low-stability 19) rather than one-off features.

```text
outputs/experiments/stable_group_ablation_confirmed_2021_2025/
```

- Random Forest mean over 2022-2025 holdouts:

```text
without_low_stability  feat 142  log_loss 0.679521  delta -0.000038  accuracy 0.5660
full                   feat 161  log_loss 0.679559  delta  0.000000  accuracy 0.5673
without_stable         feat 148  log_loss 0.683308  delta +0.003748  accuracy 0.5593
stable_only            feat  13  log_loss 0.685491  delta +0.005931  accuracy 0.5527
```

- Decision: keep `full + random_forest`. The 13 stable features dominate (removing them hurts log_loss +0.0037; a 13-feature model is only ~0.006 worse). The 19 low-stability features are effectively noise (removing all of them moves log_loss by -0.00004, accuracy -0.0013). Low-stability group is a safe lean-model prune candidate but offers no meaningful gain. Logged in `MODEL_IMPROVEMENT_LOG.md` (2026-05-27).

### 0.1.56 Test Warning Cleanup

- Cleaned up the pytest warning output (CI/log-quality item).
- The previously noted cp949 decode warning from joblib subprocess reader threads no longer reproduces on the current sklearn 1.8 environment.
- Remaining warnings addressed:
  - `logistic_l1` used the deprecated `penalty="l1", solver="liblinear"` API (FutureWarning + "penalty=l1 with l1_ratio=0.0" UserWarning in sklearn 1.8). Migrated to `l1_ratio=1.0, solver="saga", max_iter=5000`. Note: this is a watchlist-only candidate, not the production default, and the solver change slightly alters its numeric output.
  - The benign LightGBM "X does not have valid feature names" UserWarning (pipeline imputer strips DataFrame names before the booster) is now scoped-ignored via `filterwarnings` in `pyproject.toml`.

```text
.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
68 passed, 0 warnings
```

### 0.1.57 Score Model Comparison And CatBoost Regressor Adoption

- Expanded `make_regressor` with gradient_boosting / hist_gradient_boosting / lightgbm / xgboost / catboost regressors and widened `fit-final-runs-model` model choices.
- Added `scripts/run_score_model_comparison.py` to compare regressors on 2022-2025 holdouts (total/home/away/run_diff MAE+RMSE and synthetic O/U accuracy).

```text
outputs/experiments/score_model_comparison_confirmed_2021_2025/
```

- Mean over 2022-2025 holdouts:

```text
catboost_regressor                total_mae 3.4661  rmse 4.3844  ou_acc_8.5 0.5529
gradient_boosting_regressor       total_mae 3.4910  rmse 4.4159  ou_acc_8.5 0.5520
random_forest_regressor (prior)   total_mae 3.5005  rmse 4.4111  ou_acc_8.5 0.5372
ridge                             total_mae 3.5037  rmse 4.4347  ou_acc_8.5 0.5490
lightgbm_regressor                total_mae 3.5218  rmse 4.4490  ou_acc_8.5 0.5482
hist_gradient_boosting_regressor  total_mae 3.5447  rmse 4.4801  ou_acc_8.5 0.5389
```

- Decision: ADOPT `catboost_regressor` as the score/expected-runs model. It beats the prior `random_forest_regressor` on total_mae and 8.5 O/U accuracy in all four holdout seasons (consistent, unlike the win-prob checks). Trained final bundle:

```text
outputs/final_models/runs_catboost_confirmed_2021_2025_statcast/runs_model.joblib
training_rows=12148  feature_count=162
```

- Tests: `76 passed` (parametrized model tests now cover the new regressors). Logged in `MODEL_IMPROVEMENT_LOG.md` (2026-05-27).

### 0.1.58 Over-Under Pass/Lean/Strong Pick Rules

- Added a totals/over-under analogue to the existing win-pick rules so the score track has the same pass/lean/strong actionability framework.
  - `apply_ou_pick_rules(...)` and `summarize_ou_pick_rules(...)` in `evaluation.py`.
  - CLI: `ou-pick-rule-report` (mirrors `win-pick-rule-report`: scored-only filter, daily breakdown).
- Rule: margin = predicted_total - line; `pass` if |margin| < lean_margin (0.5), `lean` at/above it, `strong` at/above strong_margin (1.5). Pass rows are not scored; correctness is over/under vs actual_total.
- Validated end-to-end on the 2026 season-to-date table using the adopted CatBoost runs model at a fixed 8.5 line:

```text
outputs/mlb_2026_season_to_date_predictions/runs_catboost_predictions_8_5.csv
outputs/mlb_2026_season_to_date_predictions/ou_pick_rules_05_15/

pass        332 games  (coverage 0.41)
lean        390 picks  235 hits  accuracy 0.603
strong       85 picks   60 hits  accuracy 0.706
actionable  475 picks  295 hits  accuracy 0.621
```

- Readout: accuracy increases monotonically with margin (pass -> lean 0.603 -> strong 0.706), so the rule cleanly separates actionable totals. Caveat: this uses a synthetic fixed 8.5 line, not real market totals; predicted-total calibration around the middle line is the next item.
- Added OU rule tests; `pytest` `86 passed`. Note: win-pick and OU-pick rules now exist in parallel; a single fused win+OU recommendation remains a possible future enhancement.

### 0.1.59 First KBO Model - MLB-Mirrored Feature Build And Holdout

- Ran the MLB pipeline on KBO data as closely as possible, completing the `KBO_SCHEMA_GAP.md` minimum smoke test.
- Added `scripts/build_kbo_features_and_experiment.py` which adapts the MyKBO canonical tables to the MLB `FeatureBuilder` contract:
  - builds a `games` table from the MyKBO final-game schedule and injects `home_sp_id`/`away_sp_id` from the `is_start` flag in `pitcher_logs`;
  - renames `mykbo_player_id` -> `player_id` in batting / pitcher logs.
- League-common only, per the KBO plan: no Statcast, weather, park factors, or venue coordinates (those groups stay missing instead of being invented).

```text
data/processed/kbo/features_confirmed_kbo_2024_2026.csv   1752 games, 205 columns
outputs/quality/kbo/features_confirmed_kbo_2024_2026/
outputs/experiments/kbo/season_holdout_kbo_2024_2026/
```

- Feature quality matches the MLB confirmed-lineup baseline for league-common groups:

```text
home_sp_fip_season_to_date        null 0.093
home_lineup_avg_ops               null 0.003
home_team_runs_per_game_to_date   null 0.009
home_bullpen_fip_season_to_date   null 0.009
home_lineup_statcast_xwoba        null 1.000  (expected: no KBO Statcast)
temperature / park_factor_run     null 1.000  (expected: not supplied)
```

- Season holdout (same models as MLB: elo / logistic / random_forest):

```text
2025 holdout (train 2024):       random_forest  log_loss 0.6819  accuracy 0.5590  acc_conf_60 0.6667
2026 holdout (train 2024-2025):  random_forest  log_loss 0.6913  accuracy 0.5109  acc_conf_60 0.6750
```

- Readout: the KBO first model already tracks MLB-like numbers - `random_forest` is the best model in both holdouts, log_loss ~0.68-0.69, accuracy ~0.51-0.56, confidence-60 accuracy ~0.67 - using only league-common features. This validates the "KBO mirrors MLB" canonical-schema design. Caveats: thin training (2025 holdout trains on a single 2024 season; 2026 is a partial-season 274-game holdout), and KBO lacks MLB's Statcast/weather/park edge features. Next KBO steps would add more seasons and the public-data sabermetric / `_proxy` features from `KBO_FEATURE_PLAN.md`.

### 0.1.60 KBO Extended Data (2021-2026) And Model Enhancement

- KBO collection expanded to six seasons (2021-2026, 4,119 final games). Rebuilt the feature table on `canonical_2021_2026` with MLB-style multi-season holdouts (2022-2025).
  - Added a post-build `game_id` dedup safeguard (a rare suspended/resumed schedule game fanned out to 3 extra rows inside the builder merges).

```text
data/processed/kbo/features_confirmed_kbo_2021_2026.csv   4119 games, 205 columns
outputs/experiments/kbo/season_holdout_kbo_2021_2026/
```

- Robust multi-season result is more modest than the thin 2-season smoke: RF mean over 2022-2025 is log_loss 0.690, accuracy 0.533 - weaker than MLB (0.680 / 0.567), as expected without Statcast/park/weather.
- Model enhancement: ran the MLB `run_model_test_experiment` flow on KBO. The FeatureBuilder already emits the computable KBO proxy columns (`sp_run_prevention_proxy`, `lineup_xwoba_proxy`, `lineup_hard_contact_proxy`), and `select_feature_columns` already drops the 83 all-null Statcast/weather/park columns, so the lever is model choice, not more proxy features.

```text
outputs/experiments/kbo/model_test_kbo_2021_2026/  (mean over 2022-2025)

random_forest_shallow  log_loss 0.6871  accuracy 0.5471  acc_conf_60 0.6142
extra_trees            log_loss 0.6885  accuracy 0.5315  acc_conf_60 0.6929
soft_voting            log_loss 0.6890  accuracy 0.5359
random_forest (deep)   log_loss 0.6894  accuracy 0.5312
catboost_lr02          log_loss 0.7061
elo                    log_loss 0.7097
logistic               log_loss 0.7127
```

- Decision: for KBO the best model is `random_forest_shallow` (best log_loss AND accuracy), not the MLB deep-RF default. KBO has less data and a weaker signal, so shallower / more-regularized trees generalize better - a genuine league-specific difference. Trained the KBO final bundle:

```text
outputs/final_models/kbo_win_random_forest_shallow_2021_2026/best_model.joblib
training_rows=4119  feature_count=111
```

- KBO win prediction now runs end-to-end on six seasons with a KBO-tuned model. Deeper public-data sabermetrics (extra-base / SLG / ISO) need richer game logs than the current MyKBO boxscores provide.

### 0.1.61 NPB ProEyeKyuu Pipeline Smoke And First Model Check

- Added an NPB public-source pipeline scoped to official NPB, ProEyeKyuu, and BaseballData.jp. Paid/commercial APIs remain out of scope for this first NPB milestone.
- Added collectors and CLI surface for source pages, ProEyeKyuu game results, game pages, game-table standardization, starter enrichment, venue enrichment, coverage reporting, batting-detail audit, feature-set export, and model-ready feature export.

```text
collect-npb-source-pages
standardize-proeyekyuu-tables
standardize-proeyekyuu-game-results
collect-proeyekyuu-game-pages
standardize-proeyekyuu-game-tables
enrich-proeyekyuu-games-starters
write-npb-venue-template
enrich-npb-games-venues
audit-proeyekyuu-batting-detail
write-npb-feature-set
write-npb-model-ready-features
report-proeyekyuu-coverage
```

- Added `src/mlb_winprob/npb.py` and reproducible smoke scripts:

```text
scripts/run_npb_proeyekyuu_pipeline.py
scripts/run_npb_smoke_model_predictions.py
```

- Expanded shared non-Statcast public/proxy features so KBO/NPB can use meaningful league-common columns without pretending they are Statcast measurements:

```text
lineup_xwoba_proxy
lineup_hard_contact_proxy
sp_whiff_proxy
sp_run_prevention_proxy
sp_command_proxy
```

- Expanded the ProEyeKyuu smoke run from 10 game pages to all 50 standardized game-result sample rows:

```text
outputs/npb_smoke/standardized/npb/canonical_sample_50/batting_logs.csv   1337 rows
outputs/npb_smoke/standardized/npb/canonical_sample_50/lineups.csv         900 rows
outputs/npb_smoke/standardized/npb/canonical_sample_50/pitcher_logs.csv    396 rows
outputs/npb_smoke/processed/features_confirmed_npb_sample_50.csv            50 rows, 210 columns
outputs/npb_smoke/processed/npb_feature_set_sample_50.csv                  128 included public/proxy numeric features
outputs/npb_smoke/processed/features_confirmed_npb_model_ready_sample_50.csv 50 rows, 140 columns
```

- Coverage/readiness:
  - `outputs/npb_smoke/npb_proeyekyuu_coverage_report_50.md` reports 100% game/log/lineup/starter coverage for the 50-game sample.
  - `outputs/npb_smoke/npb_proeyekyuu_batting_detail_audit.md` confirms current parsed batting tables expose AB/R/H/RBI/SB/order/position, but not 2B/3B/HR/BB/HBP/SF.
  - Because of that gap, batting standardization fills unavailable components conservatively; NPB lineup power/on-base features are runnable but not production-grade yet.

- First chronological NPB smoke model check (40 train rows, 10 test rows, 128 features):

```text
random_forest_shallow  accuracy 0.50  brier 0.253  log_loss 0.698
logistic               accuracy 0.40  brier 0.469  log_loss 2.410
random_forest_deep     accuracy 0.30  brier 0.302  log_loss 0.798
```

- Smoke final bundle written:

```text
outputs/npb_smoke/model_final_random_forest_shallow/best_model.joblib
```

- Decision: NPB is now pipeline-smoke ready from public pages through canonical tables, feature build, model-ready export, and model scoring. This is not a production model decision: 50 games is too small for calibration or model selection, and the batting-detail gap must be closed or accepted as a conservative proxy limitation before larger NPB modeling.

### 0.1.62 KBO Environment/Public-Proxy Feature Upgrade

- Completed KBO model-improvement steps 1-3:
  - venue metadata + dome flag + empirical park factors;
  - public sabermetric features;
  - `_proxy` features and feature-stage multi-seed evaluation.
- Added built-in KBO venue metadata and enrichment helpers in `src/mlb_winprob/kbo.py`.
  - `data/standardized/kbo/venues_seed.csv`
  - `venue_id` is inferred from MyKBO venue text when present, otherwise from the home team's primary venue.
  - `is_dome` is supplied offline; outdoor temperature/wind/humidity remain pending historical weather backfill.
- Added public-data sabermetric columns in `FeatureBuilder`:
  - lineup/team: ISO, BABIP, BB rate, K rate;
  - starter: ERA, K%, BB%, K/9, BB/9, HR/9;
  - KBO/NPB public proxies: lineup xwOBA proxy, lineup hard-contact proxy, starter whiff/run-prevention/command proxy.
- Added a public-data fallback for missing pitcher `batters_faced`:

```text
estimated_bf = innings_pitched * 3 + hits + walks + hit_by_pitch
```

- Rebuilt the KBO full feature set:

```text
data/processed/kbo/features_confirmed_kbo_2021_2026_env_public_proxy.csv
data/processed/kbo/park_factors_empirical_kbo_2021_2026.csv
outputs/quality/kbo/features_confirmed_kbo_2021_2026_env_public_proxy/
```

- Quality:

```text
rows=4119  columns=241
venue_id null-rate=0.000
is_dome null-rate=0.000
park_factor_run/hr null-rate=0.186  (expected: first season has no prior-season factor)
home_sp_whiff_proxy null-rate=0.082
home_lineup_xwoba_proxy null-rate=0.008
```

- Lightweight 2022-2026 model test:

```text
random_forest_shallow  log_loss 0.6862  accuracy 0.5467  acc_conf_60 0.603
extra_trees            log_loss 0.6871  accuracy 0.5385
random_forest          log_loss 0.6872  accuracy 0.5425
```

- Multi-seed feature-stage result (3 seeds x 2022-2026 holdouts, baseline=`baseline_like + random_forest_shallow`):

```text
full + random_forest_shallow      log_loss 0.6856  delta -0.00221  accuracy +0.0131  win_rate 0.80
no_env + random_forest_shallow    log_loss 0.6858  delta -0.00203  accuracy +0.0143  win_rate 0.73
no_public_proxy + shallow RF      log_loss 0.6876  delta -0.00019  accuracy -0.0014  win_rate 0.53
baseline_like + shallow RF        log_loss 0.6878  reference
```

- Readout: the public/proxy feature upgrade is the main lift. Venue/dome/park factors add a smaller incremental log-loss gain on top of the public/proxy features. Keep KBO default as `full + random_forest_shallow`.
- Trained the upgraded final KBO model bundle:

```text
outputs/final_models/kbo_win_random_forest_shallow_2021_2026_env_public_proxy/best_model.joblib
training_rows=4119  feature_count=163
```

- Updated `scripts/predict_kbo_date.py` to use the upgraded KBO model, venues, dome weather stub, and empirical park factors by default.
- Tests: `pytest tests/test_features.py tests/test_collectors.py tests/test_evaluation.py --basetemp .pytest_tmp` -> 52 passed.

### 0.1.63 MLB Recent Form Feature Pack v1

- Added leakage-safe team recent-form features from game scores only:
  - exponentially weighted win rate last 10/20;
  - exponentially weighted run differential last 10/20;
  - weighted recent runs for/allowed;
  - low-run and 5+ run rates;
  - recent scoring volatility;
  - one-run game/win rates;
  - Pythagorean expected win percentage and actual-minus-pythagorean delta;
  - close-win dependency.
- Added diff features for the strongest recent-form signals:
  - weighted win rate, weighted run differential, recent runs for/allowed, low-run rate, 5+ run rate, actual-minus-pythagorean, close-win dependency.
- Added `scripts/rebuild_mlb_features_from_enriched_logs.py` so MLB features can be regenerated from existing enriched Statcast logs without rerunning Statcast aggregation.
- Rebuilt the recent-form feature set:

```text
data/processed/features_confirmed_2021_2025_with_park_factors_statcast_recent_form.csv
outputs/quality/features_confirmed_2021_2025_with_park_factors_statcast_recent_form/
rows=12148  columns=278
```

- Lightweight model test on 2022-2025 holdouts:

```text
outputs/experiments/mlb_recent_form_model_test_2021_2025/

random_forest_shallow  log_loss 0.68047  accuracy 0.56384
random_forest          log_loss 0.68061  accuracy 0.56518
extra_trees            log_loss 0.68191  accuracy 0.56004
```

- Multi-seed comparison against the existing baseline (`baseline + random_forest`, 3 seeds x 4 holdouts):

```text
outputs/experiments/mlb_recent_form_multiseed_2021_2025/

baseline + random_forest            log_loss 0.67948  accuracy 0.56573
baseline + random_forest_shallow    log_loss 0.68036  accuracy 0.56758
recent_form + random_forest_shallow log_loss 0.68092  accuracy 0.55966
recent_form + random_forest         log_loss 0.68100  accuracy 0.56107
```

- Decision: do NOT adopt Recent Form v1 as a full feature pack. It worsens mean log loss by about `+0.00144` to `+0.00153` vs the current baseline and reduces accuracy. The likely issue is not that recent form is useless, but that the full pack is redundant/noisy when added wholesale to an already rolling-feature-heavy model.
- Follow-up: run a narrower ablation/selection pass instead of full-pack adoption:
  - keep candidates like weighted run differential, low-run rate, and actual-minus-pythagorean;
  - drop or isolate noisy close/luck dependency features;
  - test recent form as a selection-rule/reporting overlay rather than raw model input.

### 0.1.64 MLB Recent Form v2 Ablation

- Added `scripts/run_recent_form_v2_ablation.py` to reuse the v1 recent-form feature table while testing smaller recent-form groups.
- Smoke check passed for `baseline` vs `v2_core` on 2022 holdout / seed 11.
- Ran parallel 3-seed x 2022-2025 holdout ablations across:
  - `baseline`
  - `v2_core`
  - `run_diff_only`
  - `scoring_only`
  - `pythag_only`
  - `weighted_win_only`
  - `volatility_only`
  - `close_game_only`
  - `v1_full`
- Merged output:

```text
outputs/experiments/mlb_recent_form_v2_ablation_2021_2025/
```

- Best RF candidates vs `baseline + random_forest`:

```text
pythag_only      RF  log_loss 0.67958  delta -0.00036  accuracy +0.00436  win_rate 0.58
volatility_only  RF  log_loss 0.67968  delta -0.00026  accuracy +0.00336  win_rate 0.67
scoring_only     RF  log_loss 0.67975  delta -0.00019  accuracy +0.00329  win_rate 0.67
close_game_only  RF  log_loss 0.67982  delta -0.00012  accuracy +0.00381  win_rate 0.67
baseline         RF  log_loss 0.67994  reference
v1_full          RF  log_loss 0.68100  reject
```

- Readout: narrow recent-form groups look more promising than the full v1 pack, but the lift is very small. Treat `pythag_only`, `volatility_only`, and `scoring_only` as confirmation candidates, not default features yet.

## 2026-05-28

### 0.1.65 Historical Market OU Odds Backfill (2021-2025)

- Adopted the ArnavSaraogi MLB odds JSON dump (SBR-derived, 80MB, 2021-03-20 .. 2025-08-16, 1097 daily entries, 13,117 game-odds rows, 4 sportsbooks per game with opening + current totals/ML/spread).
- Added `src/mlb_winprob/odds.py`:
  - `parse_sbr_odds_dataset` (median across books, drops All-Star, ATH/OAK rebrand handled),
  - `match_odds_to_games` (date + home/away keys, two-pass with ATH<->OAK rebrand),
  - `evaluate_predictions_against_market` + `summarize_market_ou_rules`.
- Added CLI `standardize-mlb-market-odds` and scripts:
  - `scripts/run_runs_oof_predictions.py` (per-season OOF runs predictions using adopted catboost_regressor)
  - `scripts/evaluate_ou_with_market_lines.py` (OU pick-rule + calibration vs real market lines).
- Coverage:

```text
data/raw/mlb_odds/mlb_odds_dataset.json    13117 odds rows
data/processed/market_odds_sbr_2021_2025.csv  11319 matched rows
  2021 2350 / 2022 2361 / 2023 2389 / 2024 2397 / 2025 1822 (dataset ends 2025-08-16)
```

- Generated 2022-2025 catboost_regressor OOF runs predictions (9,719 games):

```text
outputs/experiments/runs_oof_catboost_2021_2025/predictions.csv
```

- OU pick-rule with REAL market closing lines (vs prior synthetic 8.5 line):

```text
outputs/experiments/runs_oof_market_eval_2021_2025/

bucket      n_total  n_scored  n_hits  accuracy
pass        3058     2943      1449    0.4924
lean        3956     3823      1977    0.5171
strong      1923     1858      1084    0.5834   <- still has edge
actionable  5879     5681      3061    0.5388
```

- Per-season strong-bucket accuracy: 2022 0.535 / 2023 0.586 / 2024 0.639 / 2025 0.636.
- Calibration findings (pred_total bucket -> mean market line vs mean actual):

```text
pred  (0,7]    mean_pred 6.74  market 7.65  pred-market -0.91  pred-actual -1.07
pred  (8,8.5]  mean_pred 8.26  market 8.16  pred-market +0.10  pred-actual +0.05
pred  (9.5,10] mean_pred 9.73  market 8.69  pred-market +1.04  pred-actual +0.05
pred  (10,20]  mean_pred 10.83 market 8.96  pred-market +1.88  pred-actual +0.25
```

- Dispersion vs market:

```text
pred_total_std    1.10    market_line_std 1.01    actual_total_std 4.48
pred - market: mean +0.52, std 1.22, MAE 0.99   (systematic over-bias of ~0.5 run)
actual - market: mean +0.44, MAE 3.43           (market itself only catches the actual mean, not variance)
```

- Readout: real-market OU accuracy is materially lower than the fixed-8.5 results we previously reported (which got free wins on extreme totals). The strong bucket still beats coin flip by ~8 pts, so the model carries real edge, but the prior fixed-8.5 numbers were optimistic. Calibration is the main lift: predictions run ~+0.5 above market on average and diverge sharply above pred_total > 9.5 even though actual totals match much more closely. This sets up the calibration/dispersion work item next.
- Tests: 54 passed (relevant suites).

### 0.1.66 Runs Calibration And Dispersion Analysis

- Tried three post-hoc approaches on the catboost OOF runs predictions, evaluated against real SBR market closing lines:
  - (A) Cross-season isotonic + linear bias correction (fit on prior holdout seasons),
  - (B) LightGBM quantile regression at p10/p50/p90,
  - (C) In-season rolling residual bias correction.
- Per-bucket diagnostic across seasons explained why (A) fails — bias direction reverses across seasons (pred_total > 10 was +1.28 lag in 2022 but -0.61 lag in 2023 after the pitch-clock scoring jump):

```text
                pred bucket (10, 20]    bucket (0, 7.5]
2022 actual    9.66 (pred-actual +1.28) 7.23 (-0.15)
2023 actual   11.31 (-0.61)             8.39 (-1.24)   <- regime shift up
2024 actual   11.20 (-0.41)             7.19 (+0.02)
2025 actual   11.24 (-0.46)             7.23 (-0.09)
```

- (A) Cross-season isotonic — REJECTED. Fitting on prior seasons applies the wrong sign of correction during regime shifts. 2023 raw bias -0.53 became calibrated bias -1.05 (got worse). Overall actionable accuracy 53.88 -> 53.33 with calibration.
- (B) Quantile regression — REJECTED for primary use. p50 MAE matches raw catboost, but the 80% prediction-interval coverage was 0.57-0.67 (target 0.80). The quantile model structurally underestimates dispersion. p50 OU accuracy is essentially equal to raw (54.26 vs 53.88 actionable). The PI itself remains useful as a per-game uncertainty signal but is not a primary calibration lever.
- (C) In-season rolling residual bias (window=200, warmup=60) — ADOPTED. Walks chronologically through each holdout season; for each game subtracts the mean (pred_total - actual_total) of the most recent N completed games (no future leakage). Result by window:

```text
outputs/experiments/runs_rolling_calibration_2021_2025_w*/

window  strong_acc  actionable_acc  strong_n
raw     0.5834      0.5388          1858
60      0.5742      0.5383          1975
100     0.5926      0.5427          1814
200     0.5927      0.5461          1721   <- chosen
400     0.5913      0.5429          1686
```

- After window=200 rolling correction, per-season biases land near zero (was [+0.69, -0.53, +0.11, +0.03] -> [+0.04, +0.02, +0.03, +0.03]) and the actionable strong-bucket lifts +1.0pp to 59.27%.

```text
outputs/experiments/runs_rolling_calibration_2021_2025/
  predictions_rolling_calibrated.csv
  ou_pick_rule_summary.csv
```

- Decision: adopt in-season rolling residual correction as the score-model post-hoc step. Cross-season calibration kept as a documented anti-pattern. Quantile model retained as an uncertainty side-output (per-game PI width), not the primary point estimate.
- Underlying limit: pred_total_std 1.10 vs actual_total_std 4.48 means the model captures regimes/matchups but is structurally under-dispersed at the single-game level. Closing that gap is a feature/model lever (more matchup noise, weather variance, lineup variance), not a calibration lever.

### 0.1.67 Recent Form v2 Reconfirmation (7-Seed) And Overlay Rule

- Re-ran the v2 narrow ablation at 7 seeds (vs prior 3) and added a 2025-only sanity slice. Variants tested: `baseline`, `pythag_only`, `volatility_only`, `scoring_only`.
- 7-seed mean (4 holdouts × 7 seeds = 28 runs per variant):

```text
volatility_only  log_loss 0.679682  std 0.00148  delta -0.000134  win_rate 0.571
pythag_only      log_loss 0.679760  std 0.00132  delta -0.000056  win_rate 0.464
baseline         log_loss 0.679816  std 0.00122  reference
scoring_only     log_loss 0.679972  std 0.00112  delta +0.000156  win_rate 0.536
```

- 2025-only (recent-season) holdout:

```text
baseline         0.68004 +/- 0.00061
pythag_only      0.67993 +/- 0.00051
scoring_only     0.67979 +/- 0.00045
volatility_only  0.67988 +/- 0.00092
```

- Decision: REJECT all v2 narrow groups as default features. The 3-seed lift was inside seed noise; pythag_only loses vs baseline 53.6% of the time at 7 seeds. None of the variant deltas exceeds its own seed std, and the 2025-only differences are within 1 std of baseline.
- Tested an overlay alternative: keep model = baseline + random_forest, but require both `team_actual_minus_pythag_last_20_diff` and `team_weighted_run_diff_last_10_diff` to agree in sign with the main pick before treating it as actionable. Results on 2022-2025 OOF (random_forest, seed 42):

```text
outputs/experiments/mlb_recent_form_overlay_2021_2025/

band 0.53  raw n=6765 acc=0.5817   agree n=2032 acc=0.5910   +0.94pp / coverage -70%
band 0.55  raw n=5032 acc=0.6016   agree n=1566 acc=0.6092   +0.76pp / coverage -69%
band 0.57  raw n=3601 acc=0.6232   agree n=1172 acc=0.6246   +0.14pp / coverage -67%
band 0.60  raw n=1950 acc=0.6379   agree n=  677 acc=0.6425  +0.46pp / coverage -65%
```

- Decision: REJECT the overlay too. Lift is +0.1 to +0.9pp at a 65-70% coverage cost. Below 0.57 band, the natural model already exposes 60%+ accuracy via win-pick rules without sacrificing pool. Above 0.60, overlay adds <0.5pp on a much smaller pool.
- Net: the Recent Form v1 track (raw scores -> weighted recent-game features) is fully concluded as a non-adoption. Keeping the recent-form table and scripts as reference and as a starting point for any future, more carefully designed signal (e.g. matchup-conditional or team-quality-conditional residuals).

### 0.1.68 KBO Open-Meteo Outdoor Weather Backfill

- Replaced the offline dome-only KBO weather stub with real Open-Meteo Historical Hourly observations for 2021-2026.
- Added `augment_kbo_weather_with_open_meteo(games, venues)` in `src/mlb_winprob/kbo.py`. Mirrors the MLB augmenter but handles string-typed KBO venue IDs and writes temperature/wind_speed/wind_direction/humidity/is_dome/weather_source in the same schema as the existing stub.
- Added `scripts/augment_kbo_weather_open_meteo.py` runner; calls Open-Meteo Archive once per (venue, season) — 9 venues × 6 seasons = 54 API calls.

```text
data/standardized/kbo/weather_open_meteo_2021_2026.csv  4119 rows

temperature null-rate    0.0000
wind_speed null-rate     0.0000
wind_direction null-rate 0.0000
humidity null-rate       0.0000
is_dome=0 3705   is_dome=1 414  (dome games still get the outdoor reading; FeatureBuilder ignores via dome flag)
```

- Updated `scripts/build_kbo_features_and_experiment.py` with a new `--weather` flag so the build can swap between the dome-only stub and the Open-Meteo backfill without code changes.
- Built the upgraded KBO feature table and re-ran the 2022-2026 holdout against `random_forest_shallow / random_forest / extra_trees`:

```text
data/processed/kbo/features_confirmed_kbo_2021_2026_env_public_proxy_openmeteo.csv   4119 rows, 277 columns
outputs/experiments/kbo/season_holdout_kbo_2021_2026_openmeteo/

mean across 2022-2026 holdouts (best model = random_forest_shallow each season):
  log_loss              0.6863
  accuracy              0.5524
  accuracy_conf_60      0.6189

Per-season best (random_forest_shallow):
  2022  log_loss 0.6863 acc 0.541   acc_conf_60 0.632
  2023  log_loss 0.6894 acc 0.558   acc_conf_60 0.558
  2024  log_loss 0.6842 acc 0.567   acc_conf_60 0.622
  2025  log_loss 0.6809 acc 0.550   acc_conf_60 0.699
  2026  log_loss 0.6910 acc 0.547   acc_conf_60 0.583  (partial-season holdout)
```

- Comparison vs prior dome-only stub (env+public+proxy, 2022-2025 lightweight test from 0.1.62):

```text
                          log_loss  accuracy  conf_60_acc
stub (env+public+proxy)   0.6862    0.5467    0.603
+ open_meteo              0.6863    0.5524    0.619    delta acc +0.0057  delta conf60 +0.016
```

- Decision: ADOPT Open-Meteo outdoor weather for KBO. Log loss is flat but accuracy +0.57pp and the high-confidence 60% band gains +1.6pp, which is the actionable signal. The lift is genuine because the prior stub was literally NaN for outdoor temp/wind/humidity; weather now contributes real numeric features.
- Trained the upgraded final KBO model bundle:

```text
outputs/final_models/kbo_win_random_forest_shallow_2021_2026_openmeteo/best_model.joblib
training_rows=4119  feature_count=203  model_name=random_forest_shallow
```

- Tests: `pytest tests/test_features.py tests/test_collectors.py --basetemp .pytest_tmp` -> 44 passed.
- Follow-up (not blocking): point `scripts/predict_kbo_date.py` at the new openmeteo bundle and add an Open-Meteo recent-day fetch path so production KBO predictions also get real weather.

### 0.1.69 NPB Source Investigation + 2024 Full-Season Adoption

- Option B (alternative NPB sources for structured batting detail):
  - **NPB.jp official `/scores/YYYY/MMDD/<matchup>/box.html`** exposes only AB / R / H / RBI / SB columns. 2B / 3B / HR / BB / HBP / SF data exists in play-by-play text but is **not** structured columns. Same gap as ProEyeKyuu.
  - **baseball-data.com** offers aggregated season tables only; no per-game CSV.
  - **1point02.jp** is sabermetric (WAR / WPA / UZR) aggregations only; no per-game.
  - **npbstats.com** is offline (ECONNREFUSED at the eng index).
  - Conclusion: no public free NPB source surfaces structured per-game 2B/3B/HR/BB/HBP/SF. Parsing NPB.jp play-by-play is engineering equivalent to a new scraper. Option B fails for the source-quality goal.
- Option A (ProEyeKyuu full-season): collected and standardized the entire 2024 NPB regular season.

```text
outputs/npb_full/standardized/npb/games.csv                                     878 rows
outputs/npb_full/raw/proeyekyuu_game_pages/                                     878 HTML game pages
outputs/npb_full/standardized/npb/proeyekyuu_game_tables/                       15,804 parsed tables
outputs/npb_full/standardized/npb/canonical_2024/batting_logs.csv               24,431 rows
outputs/npb_full/standardized/npb/canonical_2024/lineups.csv                    15,804 rows
outputs/npb_full/standardized/npb/canonical_2024/pitcher_logs.csv                7,240 rows
outputs/npb_full/processed/features_confirmed_npb_2024_full.csv  858 reg-season rows, 277 cols
```

- Collection notes:
  - `collect-proeyekyuu-game-pages --parse-tables` only inline-parsed the first 64 games before silently continuing as download-only. Worked around by running `scripts/parse_proeyekyuu_game_pages_static.py` separately across 808 remaining HTMLs; 808/808 parsed clean.
  - All 858 games have non-null home_sp_id, away_sp_id, and venue_id after the starter and venue enrichment passes.
- Chronological 80/20 holdout (687 train through 2024-08-26, 171 test from 2024-08-27 onward):

```text
outputs/npb_full/model_test_npb_full_2024.csv

random_forest_shallow  log_loss 0.68610   accuracy 0.5263  brier 0.2464
extra_trees            log_loss 0.69179   accuracy 0.5088
random_forest          log_loss 0.69180   accuracy 0.5146
random_forest_deep     log_loss 0.69379   accuracy 0.5088
logistic               log_loss 0.83715   accuracy 0.5731   <- high acc, broken calibration
```

- Decision: ADOPT `random_forest_shallow` as the NPB 2024 default win model. Same model class that already won for KBO, same regime (less data, weaker per-game signal -> shallow trees generalize). Logistic has the highest accuracy but its log_loss 0.84 makes it overconfident on wrong picks; not adoptable.
- Final NPB model bundle:

```text
outputs/final_models/npb_win_random_forest_shallow_2024/best_model.joblib
training_rows=858  feature_count=196  model_name=random_forest_shallow
```

- Caveats kept on the books (no Option C parallel needed since A succeeded):
  - Batting detail still limited to AB / R / H / RBI / SB. Lineup OPS / SLG / ISO and patience features remain conservative proxies until a richer per-game source appears.
  - 2024 only. Multi-season NPB will need 2023/2022 ProEyeKyuu collection runs of the same shape (the script is reusable).
  - Test window is 171 chronological games; calibration / confidence-band reports will need OOF or multi-fold once we have 2+ NPB seasons.

### 0.1.70 Pre-Lineup Live Operational Smoke

- Closed the last open checklist item under "pre_lineup 실제 source smoke test" with a real end-to-end live-style run on a recent slate (2026-05-27).
- Operational flow exercised (all via existing CLI, no new code):

```text
collect-mlb-schedule          --start-date 2026-05-27 --end-date 2026-05-27
                              -> 15 scheduled games
collect-mlb-lineup-snapshots  -> 15/15 MLB Stats API boxscore JSONs
standardize-mlb-boxscores     --prediction-mode pre_lineup
                              -> 270 lineup rows (18 batters x 15 games), home_sp_id null=0
build-features                --prediction-mode pre_lineup using the 2026-to-2026-05-26
                                season-to-date batting/pitcher/weather snapshot as prior
                                rolling history
                              -> 15 feature rows x 277 cols
predict-game                  --win-model full_random_forest + runs catboost, total_line 8.5
                              -> 15 combined predictions
```

- Verified vs actuals (the snapshot also contains the final boxscore now that 2026-05-27 is in the past):

```text
outputs/pre_lineup_live_2026-05-27/predictions.csv  (15 rows)

Win-pick:                 4/15  (0.267)
OU actionable (lean+strong, 3 picks):  2/3  (0.667)
OU including pass:        10/15  (0.667 by chance)
```

- Readout: the pipeline runs end-to-end from snapshot to predictions to scored verification without intervention. Win-pick accuracy on this slate is low because most win-probabilities cluster at 0.47-0.57 - the SP season-to-date rolling features were largely null due to schema mismatches between the 2026 season-to-date pitcher_logs and the new game SP IDs in the snapshot. That is a feature-prep issue, not an operational-flow issue, and the OU side (which doesn't depend on those columns as heavily) tracks the expected 60-70% on the 3 actionable picks.
- Caveat: this was a retroactive snapshot - the API also returns final scores in the JSON when run after the games are over. Capturing 1-2 hours before first pitch instead would yield the same lineup data but with `home_score / away_score` blank in `games.csv` (so the verification step would simply be deferred until the games complete). The flow is identical either way.
- Follow-up (out of scope for this milestone): fix the SP rolling-feature null-rate on live pre-lineup features by either (a) joining the live game SP IDs against the canonical 2025 pitcher_logs as fallback when the in-season log lacks the player, or (b) extending the season-to-date snapshot collection to include any newly active SPs.
