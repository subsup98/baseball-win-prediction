# Source Layout

`src` 디렉터리는 설치 가능한 Python 패키지 코드를 담습니다.

## 구조

```text
src/
  mlb_winprob/
    __init__.py
    cli.py
    constants.py
    data_sources.py
    evaluation.py
    experiments.py
    features.py
    models.py
    prediction.py
    schemas.py
```

## 역할

- `mlb_winprob.features`: raw table을 경기 단위 Feature Vector로 변환합니다.
- `mlb_winprob.models`: 모델 registry와 Elo baseline을 제공합니다.
- `mlb_winprob.experiments`: 동일 split에서 여러 모델을 학습/평가합니다.
- `mlb_winprob.evaluation`: Log Loss, Brier Score, Accuracy, Calibration 평가를 제공합니다.
- `mlb_winprob.prediction`: 모델 출력을 public prediction response로 변환합니다.
- `mlb_winprob.data_sources`: CSV 입출력과 optional pybaseball adapter를 제공합니다.
- `mlb_winprob.cli`: CLI 명령을 제공합니다.
- `mlb_winprob.schemas`: config와 public response dataclass를 정의합니다.
- `mlb_winprob.constants`: 공통 상수와 feature 제외 컬럼을 정의합니다.

## 세부 문서

- [패키지 개요](mlb_winprob/README.md)
- [Feature Builder](mlb_winprob/FEATURES.md)
- [모델과 실험](mlb_winprob/MODELS_AND_EXPERIMENTS.md)
- [데이터와 CLI](mlb_winprob/DATA_AND_CLI.md)
- [스키마와 평가](mlb_winprob/SCHEMAS_AND_EVALUATION.md)
