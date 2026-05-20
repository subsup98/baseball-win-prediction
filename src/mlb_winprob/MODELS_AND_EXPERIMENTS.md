# Models And Experiments

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

현재 `simple_key_reasons`는 diff Feature 방향을 기준으로 간단한 설명을 생성합니다. 이후 SHAP 기반 설명으로 확장할 예정입니다.
