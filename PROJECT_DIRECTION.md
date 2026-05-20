# 전체 진행 방향

## 목표

MLB 경기 전 정보를 사용해 홈팀/원정팀 승률을 예측하는 연구 시스템을 만든다. 핵심은 팀 시즌 기록만 보는 모델이 아니라, 오늘 경기의 실제 구성원 정보를 경기 단위 Feature Vector로 만드는 것이다.

## 원칙

- 모델 입력에는 배당/수익률 데이터를 넣지 않는다.
- 모든 Feature는 경기 시작 전 알 수 있었던 정보만 사용한다.
- 라인업 확정 전 모델과 확정 후 모델을 분리한다.
- 모델은 하나로 고정하지 않고 동일 데이터셋에서 비교한다.
- 성능 판단은 확률 품질과 승패 적중력을 함께 본다.

## 진행 단계

1. 데이터 기반 구축
   - 최근 5시즌 MLB 경기 결과, 선수 로그, 선발투수 로그, 라인업, 날씨, 구장 정보를 수집한다.
   - source별 raw 데이터를 현재 표준 schema로 변환한다.
   - 누락률과 이상값 리포트를 만든다.

2. Feature Store 안정화
   - 현재 구현된 Feature를 실제 데이터에 적용한다.
   - 누수 방지 테스트를 실제 시즌 샘플로 확장한다.
   - missing value 전략을 모델별로 정리한다.

3. 백테스트 구축
   - 날짜순 split과 시즌별 holdout을 기본 검증 방식으로 사용한다.
   - `pre_lineup`과 `confirmed_lineup` 결과를 분리해서 기록한다.
   - confidence band별 성능을 반드시 함께 본다.

4. 모델 실험
   - Elo baseline으로 최소 기준선을 잡는다.
   - Logistic Regression으로 해석 가능한 기준 모델을 만든다.
   - Random Forest, LightGBM, XGBoost, CatBoost를 비교한다.
   - MLP와 embedding 기반 딥러닝 확장 가능성을 실험한다.
   - 최종적으로 stacking 또는 blending을 검토한다.

5. 설명 가능성
   - diff Feature와 주요 Feature importance로 기본 설명을 만든다.
   - booster 모델이 안정되면 SHAP 기반 설명을 추가한다.
   - 출력에는 승률, 모델명, prediction mode, 주요 근거를 포함한다.

6. 확장
   - 예상 득점 모델을 별도 target으로 추가한다.
   - KBO 데이터 schema와 호환 가능한 부분을 분리한다.
   - 장기적으로 MLB/KBO 공통 Feature와 리그별 Feature를 나눈다.

## 당장 집중할 것

- 실제 데이터 수집 source 확정
- `DATA_REQUIREMENTS.md` 기준으로 source별 수집 adapter 구현
- raw-to-standard schema 변환
- 5시즌 Feature table 생성
- 시즌별 holdout 성능 리포트 생성
- null-rate와 데이터 누수 점검 자동화

## 데이터 source 설계

Feature를 완성하려면 하나의 source만으로는 부족하므로 source별 역할을 분리한다.

- MLB Stats API는 경기 일정, game id, 홈/원정팀, 점수, venue, probable pitcher, boxscore, confirmed lineup의 backbone으로 사용한다.
- Baseball Savant / Statcast는 pitch/PA 이벤트, 좌우 매치업, xwOBA, wOBA value, 타구/투구 품질 계산에 사용한다.
- Retrosheet는 historical game log, 선발 라인업, 날씨, 타자/투수 game log 백업으로 사용한다.
- FanGraphs는 wRC+, FIP, K-BB%, park factor 같은 고급 지표 보조와 검산에 사용한다.
- Lahman은 선수/팀 ID, 시즌 누적, 팀 메타데이터 보조 source로 사용한다.

상세 테이블 요구사항은 `DATA_REQUIREMENTS.md`를 기준으로 한다.
