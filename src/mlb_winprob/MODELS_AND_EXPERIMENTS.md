# Models And Experiments

## Current Baseline Decision

- Main baseline: `full + random_forest`
- Confidence-band challenger: `full + random_forest_shallow`
- Calibration challenger: `calibrated_logistic`
- Held pruning candidate: `without_lineup_optional + random_forest`

The main baseline is fixed to `full + random_forest` because the 10-seed stability check had the best mean log loss among the current RF candidates. `full + random_forest_shallow` remains a selective confidence-band challenger because it improves `accuracy_conf_60` while giving up overall log loss and coverage. Feature-pruned candidates should not replace the baseline unless they beat it in multi-seed season-holdout validation.

구현 파일: `models.py`, `experiments.py`, `prediction.py`

## 모델 실험 구조

`run_model_experiments`는 동일한 Feature table, 동일한 split, 동일한 metric으로 여러 모델을 비교합니다.

현재 지원 모델:

- `elo`
- `logistic`
- `random_forest`
- `mlp`
- `lightgbm`
- `xgboost`
- `catboost`
- `hybrid_stacking`

`lightgbm`, `xgboost`, `catboost`는 optional dependency입니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[boosters]"
```

SHAP 기반 설명 리포트는 optional dependency입니다. 설치되어 있으면 시즌 holdout 리포트 생성 시 tree 계열 모델에 대해 `shap_importance/` 산출물이 함께 생성됩니다. 계산 비용을 줄이기 위해 holdout 표본은 기본 250경기까지 샘플링합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[explain]"
```

## Elo baseline

`EloRatingModel`은 날짜순으로 rating을 업데이트하는 기준 모델입니다.

- 초기 rating: `1500`
- 기본 K-factor: `20`
- 홈 어드밴티지 rating: `55`

Elo는 복잡한 세이버 Feature 없이도 비교 기준선을 제공합니다.

## Feature 선택

`select_feature_columns`는 숫자형/boolean 컬럼 중 학습 대상이 아닌 메타 컬럼을 제외합니다.

제외되는 대표 컬럼:

- `game_id`
- `game_date`
- `season`
- `home_team`
- `away_team`
- `home_score`
- `away_score`
- `prediction_mode`
- `home_team_win`

## 학습/검증 split

기본은 시즌 holdout입니다.

- `holdout_season`이 있으면 해당 시즌을 test로 사용합니다.
- 값이 없으면 가장 최근 시즌을 holdout으로 사용합니다.
- 시즌 split이 불가능하면 날짜순 temporal split으로 fallback합니다.

## 실험 config와 결과 버전

`season-holdout-report`는 CLI 인자 또는 TOML config로 실행할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli season-holdout-report `
  --config configs/season_holdout_statcast.toml
```

Config 예:

```toml
[season_holdout]
name = "season_holdout_confirmed_2021_2025_with_park_factors_statcast"
features = ["data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv"]
output_dir = "outputs/experiments/versioned"
holdout_seasons = [2022, 2023, 2024, 2025]
models = ["elo", "logistic", "random_forest"]
prediction_mode = "confirmed_lineup"
versioned_output = true
```

`versioned_output = true`이면 결과는 `YYYYMMDD_HHMMSS_<name>_<config_hash>` 디렉터리에 저장됩니다. 모든 holdout report 실행은 `run_manifest.json`을 남기고, config 기반 실행은 `config_snapshot.json`도 함께 저장합니다.

## 앙상블 selection rule

`season-holdout-report`는 모델별 원시 metric 외에 `model_selection_rules.csv`를 저장합니다.

- `overall_log_loss`: holdout log loss가 가장 낮은 모델
- `confidence_55`, `confidence_60`, `confidence_65`: 해당 confidence band에서 coverage가 10% 이상인 모델 중 accuracy가 가장 높은 모델

이 rule은 production 후보를 고정하기 위한 1차 기준입니다. 시즌별 best model이 흔들리는지, confidence band별 선택이 calibration을 해치지 않는지 별도로 확인해야 합니다.

## 예상 득점 모델

`expected-runs-report`는 같은 feature table로 홈/원정 득점을 따로 예측합니다.

지원 regressor:

- `ridge`
- `random_forest_regressor`

```powershell
mlb-winprob expected-runs-report `
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv `
  --output-dir outputs/experiments/expected_runs_confirmed_2021_2025 `
  --holdout-seasons 2022,2023,2024,2025 `
  --models ridge,random_forest_regressor `
  --prediction-mode confirmed_lineup
```

출력 metric:

- `home_mae`
- `away_mae`
- `total_mae`
- `total_rmse`
- `run_diff_mae`

예상 득점은 승률 모델의 대체물이 아니라 adjacent task입니다. total runs와 run differential이 안정적으로 맞는지 확인한 뒤 승률 모델의 보조 출력으로 연결합니다.

## 연구 확장 설계 문서

- 선수 embedding 실험 설계: `RESEARCH_EXTENSIONS.md`
- KBO schema gap 점검: `KBO_SCHEMA_GAP.md`

## 예측 응답

`prediction.py`는 모델 확률을 public response 형태로 바꿉니다.

```json
{
  "home_win_probability": 0.58,
  "away_win_probability": 0.42,
  "model_name": "lightgbm_confirmed_lineup",
  "prediction_mode": "confirmed_lineup",
  "key_reasons": []
}
```

현재 `simple_key_reasons`는 diff Feature 방향을 기준으로 간단한 설명을 생성합니다. 시즌 holdout 리포트에서는 optional SHAP 설치 시 tree 계열 모델의 mean absolute SHAP 중요도를 별도 CSV와 Markdown summary로 저장합니다.
