# mlb_winprob Package

`mlb_winprob`는 MLB 경기 승률 예측을 위한 연구용 패키지입니다. 현재 구현은 실제 데이터 source에 강하게 묶이지 않고, 표준화된 CSV 또는 `pandas.DataFrame`을 받아 Feature 생성과 모델 실험을 수행하는 구조입니다.

## 데이터 흐름

```text
raw tables
  games
  batting_logs
  pitcher_logs
  lineups
  weather
  park_factors
        ↓
FeatureBuilder
        ↓
game-level feature table
        ↓
run_model_experiments
        ↓
metrics / calibration / best_model.joblib
        ↓
predict
```

## 핵심 규칙

- `season_to_date` Feature는 경기 전 누적값입니다.
- rolling Feature는 현재 경기 기록을 포함하지 않습니다.
- diff Feature는 `positive = home advantage` 방향을 따릅니다.
- 배당 데이터는 모델 입력에서 제외합니다.
- `pre_lineup`과 `confirmed_lineup`은 같은 구조를 쓰되 서로 다른 prediction mode로 분리합니다.

## public entrypoint

```python
from mlb_winprob import FeatureBuilder, FeatureBuildConfig, PredictionResult
```

현재 패키지 버전은 `0.1.1`입니다.
