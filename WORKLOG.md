# Worklog

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
