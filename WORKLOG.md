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
