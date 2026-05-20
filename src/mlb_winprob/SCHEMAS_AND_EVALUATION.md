# Schemas And Evaluation

구현 파일: `schemas.py`, `constants.py`, `evaluation.py`

## Dataclass

### FeatureBuildConfig

Feature 생성 설정입니다.

- `prediction_mode`: `pre_lineup` 또는 `confirmed_lineup`
- `fip_constant`: 기본 `3.1`
- `home_field_advantage`: 기본 `1.0`
- `lineup_order_weights`: 타순별 wOBA 가중 평균 계산용 weight

### PredictionResult

public prediction response입니다.

- `home_win_probability`
- `away_win_probability`
- `model_name`
- `prediction_mode`
- `key_reasons`

## 공통 상수

`constants.py`는 모델 학습에서 제외할 컬럼과 target 이름을 관리합니다.

- target: `home_team_win`
- prediction mode:
  - `pre_lineup`
  - `confirmed_lineup`
- confidence thresholds:
  - `0.55`
  - `0.60`
  - `0.65`

## 평가 지표

`evaluate_probabilities`는 다음 metric을 반환합니다.

- `log_loss`
- `brier_score`
- `accuracy`
- `n_games`
- `accuracy_conf_55`
- `accuracy_conf_60`
- `accuracy_conf_65`
- `coverage_conf_55`
- `coverage_conf_60`
- `coverage_conf_65`

## Calibration

`calibration_table`은 확률 구간별 예측 승률과 실제 승률을 비교합니다.

결과 컬럼:

- `bin`
- `n_games`
- `predicted_home_win_rate`
- `actual_home_win_rate`
- `calibration_error`

## Split

`season_holdout_split`:

- 가장 최근 시즌 또는 지정 시즌을 test로 사용합니다.
- train/test가 비어 있으면 temporal split으로 fallback합니다.

`temporal_train_test_split`:

- `game_date`, `game_id` 기준 정렬 후 뒤쪽 일부를 test로 사용합니다.
