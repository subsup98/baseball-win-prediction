# MLB 경기 승률 예측 시스템

현재 버전: `0.1.5`

MLB 경기 전 정보를 하나의 경기 단위 Feature Vector로 합쳐 홈팀 승률을 예측하는 연구용 파이프라인입니다.

핵심 원칙은 다음과 같습니다.

- 모든 Feature는 경기 시작 전 시점에 알 수 있었던 데이터만 사용합니다.
- 라인업 확정 전(`pre_lineup`)과 확정 후(`confirmed_lineup`) 예측을 분리합니다.
- 배당/수익률 데이터는 모델 입력에서 제외합니다.
- 동일한 Feature 테이블과 동일한 시간순 검증 조건에서 여러 모델을 비교합니다.

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

선택 모델과 공개 데이터 수집 기능까지 설치하려면:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,boosters,data]"
```

## 입력 테이블

CSV 또는 `pandas.DataFrame`으로 아래 테이블을 넣을 수 있습니다.

### games

필수 컬럼:

- `game_id`
- `game_date`
- `season`
- `home_team`
- `away_team`
- `home_sp_id`
- `away_sp_id`

학습용이면 다음 컬럼도 사용합니다.

- `home_score`
- `away_score`

선택 컬럼:

- `venue_id`

### batting_logs

타자 경기 기록입니다. 선수별 경기 로그 형태를 기대합니다.

- `game_id`, `game_date`, `season`, `player_id`, `team`
- `at_bats`, `hits`, `doubles`, `triples`, `home_runs`
- `walks`, `hit_by_pitch`, `sacrifice_flies`, `total_bases`
- 선택: `plate_appearances`, `opposing_pitcher_hand`

### pitcher_logs

투수 경기 기록입니다.

- `game_id`, `game_date`, `season`, `player_id`, `team`
- `innings_pitched`, `hits`, `home_runs`, `walks`, `hit_by_pitch`, `strikeouts`
- 선택: `batters_faced`, `pitches`, `is_start`, `role`, `is_closer`, `is_high_leverage`

### lineups

예상/확정 라인업입니다.

- `game_id`, `team`, `player_id`, `batting_order`
- 선택: `bats`, `prediction_mode`

`prediction_mode` 값은 `confirmed_lineup`, `confirmed`, `pre_lineup`, `projected`, `expected`를 지원합니다.

### weather

- `game_id`
- `temperature`, `wind_speed`, `wind_direction`, `humidity`, `is_dome`

### park_factors

- `venue_id`
- 선택: `season`
- `park_factor_run`, `park_factor_hr`

## CLI 사용

Feature 생성:

```powershell
mlb-winprob build-features `
  --games data/raw/games.csv `
  --batting-logs data/raw/batting_logs.csv `
  --pitcher-logs data/raw/pitcher_logs.csv `
  --lineups data/raw/lineups.csv `
  --weather data/raw/weather.csv `
  --park-factors data/raw/park_factors.csv `
  --prediction-mode confirmed_lineup `
  --output data/processed/features_confirmed.csv
```

모델 비교:

```powershell
mlb-winprob train `
  --features data/processed/features_confirmed.csv `
  --prediction-mode confirmed_lineup `
  --output-dir outputs/confirmed
```

Config 기반 시즌 holdout 리포트:

```powershell
mlb-winprob season-holdout-report `
  --config configs/season_holdout_statcast.toml
```

예상 득점 리포트:

```powershell
mlb-winprob expected-runs-report `
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv `
  --output-dir outputs/experiments/expected_runs_confirmed_2021_2025 `
  --holdout-seasons 2022,2023,2024,2025 `
  --models ridge,random_forest_regressor `
  --prediction-mode confirmed_lineup
```

`versioned_output = true`인 config는 `outputs/experiments/versioned/YYYYMMDD_HHMMSS_<name>_<config_hash>/` 아래에 결과를 저장하고, `run_manifest.json`과 `config_snapshot.json`을 함께 남깁니다.

예측:

```powershell
mlb-winprob predict `
  --features data/processed/today_features.csv `
  --model outputs/confirmed/best_model.joblib `
  --model-name lightgbm `
  --prediction-mode confirmed_lineup
```

공개 Statcast 원천 데이터 수집:

```powershell
mlb-winprob collect-statcast `
  --start-date 2024-04-01 `
  --end-date 2024-04-07 `
  --output data/raw/statcast_2024_04_01_07.csv
```

Statcast 포함 전체 feature/report 재생성:

```powershell
.\.venv\Scripts\python.exe scripts\build_statcast_feature_pipeline.py
```

원천 Statcast CSV까지 다시 수집하려면:

```powershell
.\.venv\Scripts\python.exe scripts\build_statcast_feature_pipeline.py `
  --collect `
  --workers 12
```

MLB Stats API schedule 수집:

```powershell
mlb-winprob collect-mlb-schedule `
  --start-date 2024-04-01 `
  --end-date 2024-04-01 `
  --output data/raw/mlb_stats_api/schedule_2024-04-01.csv
```

MLB 시즌 단위 원천 수집/표준화/Feature 생성:

```powershell
mlb-winprob collect-mlb-season-dataset `
  --start-season 2021 `
  --end-season 2025 `
  --output-root data
```

## 개발 테스트

```powershell
python -m pytest
```

## 프로젝트 문서

- [프로젝트 체크리스트](PROJECT_CHECKLIST.md)
- [워크로그](WORKLOG.md)
- [전체 진행 방향](PROJECT_DIRECTION.md)
- [데이터 요구사항](DATA_REQUIREMENTS.md)
- [원천 데이터 수집 가이드](RAW_DATA_COLLECTION.md)
- [변경 이력](CHANGELOG.md)
- [소스 구조 설명](src/README.md)
## Current Model Baseline

- Main baseline: `full + random_forest`
- Confidence-band challenger: `full + random_forest_shallow`
- Decision log: `MODEL_IMPROVEMENT_LOG.md`

Use the main baseline for overall probability quality. Use the confidence-band challenger only for selective high-confidence analysis until selection rules are validated.
