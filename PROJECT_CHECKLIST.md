# 프로젝트 체크리스트

## 1. 현재 완료

- [x] Python 패키지 구조 생성
- [x] Feature Builder 구현
- [x] `pre_lineup` / `confirmed_lineup` 예측 모드 분리
- [x] 선발투수 Feature 구현
- [x] 라인업 Feature 구현
- [x] 팀 흐름 Feature 구현
- [x] 불펜 Feature 구현
- [x] 구장/날씨 Feature 병합 구현
- [x] `positive = home advantage` diff Feature 구현
- [x] 모델 실험 파이프라인 구현
- [x] Elo baseline 구현
- [x] Logistic Regression, Random Forest, MLP, optional booster 모델 구조 구현
- [x] Hybrid stacking 구조 구현
- [x] 평가 지표 구현
- [x] CLI 구현
- [x] 기본 테스트 추가
- [x] `pytest` 통과 확인
- [x] 프로젝트 문서 및 버전 문서 추가
- [x] Feature 생성에 필요한 데이터 source 요구사항 정리
- [x] MLB Stats API / Statcast / Retrosheet / FanGraphs / Lahman 역할 분리
- [x] source-to-table 매핑 문서화
- [x] MLB Stats API schedule 수집 CLI 구현
- [x] MLB Stats API boxscore/feed JSON 수집 CLI 구현
- [x] Retrosheet CSV/ZIP 다운로드 CLI 구현
- [x] Lahman/Baseball Databank 다운로드 CLI 구현
- [x] Chadwick Register people.csv 다운로드 CLI 구현
- [x] FanGraphs leaderboard 수집 CLI 구현
- [x] 실제 MLB Stats API schedule 하루치 수집 검증
- [x] MLB Stats API people metadata 수집 CLI 구현
- [x] 라인업 타자 손 방향 `bats` 보강
- [x] 상대 선발 투수 손 방향 `opposing_pitcher_hand` 보강
- [x] MLB Stats API boxscore 표준 변환 CLI 구현
- [x] 일주일치 실제 MLB 데이터로 feature CSV 생성 검증
- [x] 시즌 단위 MLB Stats API 수집/표준화/feature 생성 CLI 구현
- [x] 중단 후 재개 가능한 boxscore 수집 구조 구현
- [x] 시즌 단위 수집 smoke test 실행
- [x] 2021-2025 최근 5시즌 전체 MLB Stats API 데이터셋 구축 완료
- [x] 2021-2025 confirmed lineup feature 통합 CSV 생성 완료
- [x] Feature 품질 리포트 CLI 및 산출물 생성 완료
- [x] 2022-2025 시즌별 holdout 백테스트 리포트 생성 완료
- [x] Empirical park factor 생성 및 전 시즌 값 적용 방식 구현 완료
- [x] Park factor 포함 feature 품질/holdout 리포트 생성 완료
- [x] 현재 `.venv` 기준 `pytest` 14개 통과 확인
- [x] MLB Stats API boxscore 기반 weather 파서 보강
- [x] `Roof Closed`/돔 경기 `is_dome` 판정 자동화
- [x] weather 표준 CSV에 `weather_condition`, `weather_source` 기록 추가
- [x] weather 파서 보강 후 2021-2025 feature/품질/holdout 산출물 재생성
- [x] MLB Stats API live feed collector URL을 `api/v1.1` 경로로 수정
- [x] live feed 샘플 5경기 수집 및 weather 필드 확인
- [x] 현재 `.venv` 기준 `pytest` 17개 통과 확인
- [x] MLB Stats API venue 좌표 CSV 생성
- [x] Open-Meteo Historical Weather API 기반 humidity 보강 CLI 구현
- [x] 2021-2025 전체 `humidity` 결측 해소
- [x] humidity 보강 후 feature/품질/holdout 산출물 재생성
- [x] 현재 `.venv` 기준 `pytest` 20개 통과 확인
- [x] Statcast event 집계 모듈 구현
- [x] `aggregate-statcast` CLI 추가
- [x] `merge-statcast-logs` CLI 추가
- [x] Statcast 품질 컬럼 기반 선택적 feature 계산 연동
- [x] 현재 `.venv` 기준 `pytest` 24개 통과 확인
- [x] `pybaseball` data extra 설치/확인
- [x] 2024-04-01~2024-04-07 Statcast event smoke test 수집
- [x] Statcast smoke test 집계/merge/feature/품질 리포트 생성
- [x] 2021-2025 Statcast 포함 feature/report 재생성 운영 스크립트 추가
- [x] Retrosheet 백업 source 표준 변환 경로 구현
- [x] Chadwick 기반 `id_map.csv` 구축
- [x] Calibration plot 이미지 저장 기능 추가
- [x] Feature importance 기반 설명 리포트 추가
- [x] FanGraphs 보조 지표 수집 방식 확정
- [x] 공식 라인업/예상 라인업 source 최종 결정
- [x] weather source 결정 및 `weather` 테이블 자동화
- [x] SHAP 기반 설명 리포트 경로 추가
- [x] 실험별 config 파일 도입
- [x] 실험 결과 버전 관리 방식 확정
- [x] 타자/투수 handedness matchup 정교화

## 2. 다음 작업

- [x] MLB Stats API에서 `games.csv` 초안용 schedule 원천 데이터 수집 가능
- [x] MLB Stats API schedule CSV를 표준 `games.csv` schema로 변환
- [x] MLB Stats API boxscore JSON을 표준 `lineups.csv`, `batting_logs.csv`, `pitcher_logs.csv`로 변환
- [x] Baseball Savant / Statcast에서 2021-2025 전체 `statcast_events.csv` 수집
- [x] Statcast event row를 `batting_logs.csv` / `pitcher_logs.csv` 계산에 사용할 수 있게 집계
- [x] Retrosheet CSV에서 historical `gameinfo`, `teamstats`, `batting`, `pitching` 수집
- [x] Retrosheet 데이터를 `games.csv`, `lineups.csv`, `weather.csv` 백업 source로 변환
- [x] FanGraphs에서 wOBA, wRC+, FIP, K-BB%, park factor 보조 데이터 수집 방식 확정
- [x] Lahman 또는 Chadwick register 기반 `id_map.csv` 구축
- [x] 공식 라인업/예상 라인업 source 최종 결정
- [x] weather source 결정 및 `weather` 테이블 자동화
- [x] park factor source 결정 및 시즌별 보정 방식 확정
- [x] 2021-2025 최근 5시즌 schedule 수집
- [x] 2021-2025 최근 5시즌 boxscore JSON 수집
- [x] 2021-2025 최근 5시즌 표준 CSV 생성
- [x] 2021-2025 최근 5시즌 confirmed lineup feature CSV 생성
- [x] 충분한 이전 경기 기록이 있는 기간으로 rolling Feature 품질 검증
- [x] 실제 데이터 기준 Feature null-rate 리포트 생성
- [x] 시즌별 holdout 백테스트 실행
- [x] 모델별 성능 리포트 자동 생성
- [x] Calibration plot 이미지 저장 기능 추가
- [x] Feature importance 기반 설명 리포트 추가
- [x] SHAP 기반 설명 기능 추가

## 3. 연구 확장

- [x] 타자/투수 handedness matchup 정교화
- [ ] 라인업 확정 전 예상 라인업 confidence Feature 추가
- [ ] 선수 부상/휴식/결장 신호 추가
- [ ] 팀 이동거리와 시차 Feature 추가
- [ ] 불펜 high-leverage role 자동 추정
- [ ] 선발투수 pitch-mix / Stuff 계열 Feature 검토
- [ ] 딥러닝용 선수 embedding 실험 설계
- [ ] 모델 앙상블 selection rule 확정
- [ ] 예상 득점 모델 확장
- [ ] KBO 확장 가능 schema 점검

## 4. 운영 기준

- [x] 데이터 갱신 명령 표준화
- [x] 학습/검증 실행 명령 표준화
- [x] 결과물 저장 디렉터리 표준화
- [x] 실험별 config 파일 도입
- [x] 실험 결과 버전 관리 방식 확정

## 2026-05-19 데이터 수집 완료 기록

- [x] 2021-2025 최근 5시즌 MLB Stats API schedule CSV 수집 완료
- [x] 2021-2025 최근 5시즌 MLB Stats API boxscore JSON 수집 완료
- [x] 2021-2025 최근 5시즌 MLB Stats API people metadata CSV 생성 완료
- [x] 2021-2025 최근 5시즌 표준 CSV 생성 완료
- [x] 2021-2025 최근 5시즌 confirmed lineup feature CSV 생성 완료
- [x] boxscore 병렬 수집 및 진행 카운트 출력 적용

완료 산출물:

```text
data/raw/mlb_stats_api/schedule_2021.csv
data/raw/mlb_stats_api/schedule_2022.csv
data/raw/mlb_stats_api/schedule_2023.csv
data/raw/mlb_stats_api/schedule_2024.csv
data/raw/mlb_stats_api/schedule_2025.csv

data/raw/mlb_stats_api/boxscores_2021/*.json  2429 files
data/raw/mlb_stats_api/boxscores_2022/*.json  2430 files
data/raw/mlb_stats_api/boxscores_2023/*.json  2430 files
data/raw/mlb_stats_api/boxscores_2024/*.json  2429 files
data/raw/mlb_stats_api/boxscores_2025/*.json  2430 files

data/standardized/mlb_stats_api_2021/games.csv  2429 rows
data/standardized/mlb_stats_api_2022/games.csv  2430 rows
data/standardized/mlb_stats_api_2023/games.csv  2430 rows
data/standardized/mlb_stats_api_2024/games.csv  2429 rows
data/standardized/mlb_stats_api_2025/games.csv  2430 rows

data/processed/features_confirmed_2021.csv  2429 rows
data/processed/features_confirmed_2022.csv  2430 rows
data/processed/features_confirmed_2023.csv  2430 rows
data/processed/features_confirmed_2024.csv  2429 rows
data/processed/features_confirmed_2025.csv  2430 rows
```

## 2026-05-19 품질 리포트 및 백테스트 완료 기록

- [x] 2021-2025 feature CSV 통합 파일 생성
- [x] 실제 데이터 기준 feature null-rate 리포트 생성
- [x] rolling/season-to-date feature 품질 리포트 생성
- [x] 2022-2025 시즌별 holdout 백테스트 실행
- [x] Elo, Logistic Regression, Random Forest 기준 성능 비교 리포트 생성

완료 산출물:

```text
data/processed/features_confirmed_2021_2025.csv  12148 rows

outputs/quality/features_confirmed_2021_2025/feature_null_rates.csv
outputs/quality/features_confirmed_2021_2025/rolling_feature_readiness.csv
outputs/quality/features_confirmed_2021_2025/season_summary.csv
outputs/quality/features_confirmed_2021_2025/summary.md

outputs/experiments/season_holdout_confirmed_2021_2025/metrics_by_holdout.csv
outputs/experiments/season_holdout_confirmed_2021_2025/best_by_holdout.csv
outputs/experiments/season_holdout_confirmed_2021_2025/calibration/
```

주요 확인 사항:

```text
humidity, park_factor_run, park_factor_hr: null_rate 1.0
wind_direction: null_rate 0.1697
sp_fip_diff: null_rate 0.1235

Best model by log_loss:
2022 random_forest log_loss 0.6790 accuracy 0.5605
2023 random_forest log_loss 0.6841 accuracy 0.5531
2024 random_forest log_loss 0.6773 accuracy 0.5706
2025 random_forest log_loss 0.6818 accuracy 0.5510
```

## 2026-05-19 Park Factor 보강 완료 기록

- [x] 표준 경기/타격 로그 기반 empirical park factor 생성 CLI 추가
- [x] 같은 시즌 최종값 누수를 피하기 위해 전 시즌 값을 다음 시즌에 적용하는 방식으로 확정
- [x] 2021-2025 표준 데이터에서 2022-2026 적용용 park factor CSV 생성
- [x] park factor 포함 2021-2025 feature CSV 재생성
- [x] park factor 포함 품질 리포트 및 시즌별 holdout 리포트 생성

완료 산출물:

```text
data/processed/park_factors_empirical_previous_season_2022_2026.csv  152 rows

data/processed/features_confirmed_2021_with_park_factors.csv
data/processed/features_confirmed_2022_with_park_factors.csv
data/processed/features_confirmed_2023_with_park_factors.csv
data/processed/features_confirmed_2024_with_park_factors.csv
data/processed/features_confirmed_2025_with_park_factors.csv
data/processed/features_confirmed_2021_2025_with_park_factors.csv  12148 rows

outputs/quality/features_confirmed_2021_2025_with_park_factors/
outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors/
```

주요 확인 사항:

```text
park_factor_run null_rate: 1.0000 -> 0.2149
park_factor_hr  null_rate: 1.0000 -> 0.2149
humidity        null_rate: 1.0000 유지

Best model by log_loss with park factors:
2022 random_forest log_loss 0.6790 accuracy 0.5605
2023 random_forest log_loss 0.6840 accuracy 0.5580
2024 random_forest log_loss 0.6786 accuracy 0.5583
2025 random_forest log_loss 0.6809 accuracy 0.5551
```

## 2026-05-20 진행 상황 점검 및 남은 작업

현재 완료 상태:

- [x] 2021-2025 정규시즌 schedule, boxscore JSON, people metadata 수집 상태 확인
- [x] 2021-2025 표준 CSV 및 confirmed lineup feature CSV 행 수 확인
- [x] park factor 포함 통합 feature CSV 행 수 `12148` 확인
- [x] park factor 포함 품질 리포트 `outputs/quality/features_confirmed_2021_2025_with_park_factors/summary.md` 확인
- [x] park factor 포함 holdout best model 리포트 확인
- [x] `.venv` 환경에서 테스트 재실행: `14 passed`

다음 우선순위:

- [x] `humidity` 결측 100% 해소를 위한 weather source 결정 및 자동화
- [x] MLB Stats API boxscore를 temperature/wind/roof primary source로 사용하도록 파서 보강
- [x] `humidity` 결측 100% 해소를 위한 별도 weather source 결정 및 자동화
- [x] Baseball Savant / Statcast event 수집 및 투타 로그 집계 연동
- [x] Retrosheet 백업 source 변환 경로 구현
- [x] FanGraphs 보조 지표 수집 방식 확정
- [x] Lahman 또는 Chadwick register 기반 `id_map.csv` 구축
- [x] Calibration plot 이미지 저장 기능 추가
- [x] Feature importance / SHAP 기반 설명 리포트 추가
- [x] 데이터 갱신/학습/검증 명령과 결과 디렉터리 운영 표준화

## 2026-05-20 Weather 1차 보강 완료 기록

- [x] MLB Stats API boxscore `Weather`, `Wind` 정보 파싱 강화
- [x] `weather_condition`과 `weather_source`를 표준 `weather.csv`에 추가
- [x] `Roof Closed`, `Dome`, `Indoor` 계열 문구 기반 `is_dome=1` 판정 추가
- [x] 현재 원천에 습도 문구가 들어올 경우를 대비한 humidity parser 추가
- [x] 2021-2025 표준 CSV 재생성
- [x] 2021-2025 confirmed lineup feature CSV 재생성
- [x] 2021-2025 park factor 포함 feature CSV 재생성
- [x] 품질 리포트 및 시즌별 holdout 리포트 재생성
- [x] MLB Stats API live feed URL 수정 및 샘플 5경기 수집
- [x] `.venv` 기준 테스트 재실행: `17 passed`

확인 결과:

```text
data/processed/features_confirmed_2021_2025_with_park_factors.csv  12148 rows

temperature null_rate: 0.0000
is_dome null_rate: 0.0000
wind_speed null_rate: 0.0001
wind_direction null_rate: 0.1697
humidity null_rate: 1.0000

2024 weather.csv is_dome:
is_dome=1  457 games
is_dome=0  1972 games
```

남은 weather 작업:

- [x] MLB Stats API live feed에 습도/상세 날씨가 존재하는지 샘플 수집으로 확인
- [x] 샘플 live feed에는 `condition`, `temp`, `wind`만 있고 `humidity`가 없음을 확인
- [x] 외부 historical weather source 후보 확정
- [x] 외부 source 사용 시 venue 위치/경기 시각 기준 weather join 구현

## 2026-05-20 Weather 2차 보강 완료 기록

- [x] Open-Meteo Historical Weather API를 humidity 보강 source로 채택
- [x] MLB Stats API venue endpoint에서 `venue_id`, `venue_name`, `latitude`, `longitude` 수집
- [x] MLB venue endpoint에 좌표가 없는 `Estadio Alfredo Harp Helu`는 fallback 좌표 적용
- [x] `collect-mlb-venues` CLI 추가
- [x] `augment-weather-openmeteo` CLI 추가
- [x] 2021-2025 전체 `weather.csv`에 Open-Meteo humidity join
- [x] 2021-2025 기본 feature 및 park factor 포함 feature 재생성
- [x] 품질 리포트 및 시즌별 holdout 리포트 재생성
- [x] `.venv` 기준 테스트 재실행: `20 passed`

완료 산출물:

```text
data/raw/mlb_stats_api/venues_2021_2025.csv  42 rows

data/standardized/mlb_stats_api_2021/weather.csv
data/standardized/mlb_stats_api_2022/weather.csv
data/standardized/mlb_stats_api_2023/weather.csv
data/standardized/mlb_stats_api_2024/weather.csv
data/standardized/mlb_stats_api_2025/weather.csv

data/processed/features_confirmed_2021_2025.csv  12148 rows
data/processed/features_confirmed_2021_2025_with_park_factors.csv  12148 rows
```

품질 확인:

```text
humidity null_rate: 1.0000 -> 0.0000
temperature null_rate: 0.0000
is_dome null_rate: 0.0000
wind_speed null_rate: 0.0001
wind_direction null_rate: 0.1697
```

park factor 포함 holdout 기준 best model:

```text
2022 random_forest log_loss 0.6780 accuracy 0.5675
2023 random_forest log_loss 0.6821 accuracy 0.5564
2024 random_forest log_loss 0.6777 accuracy 0.5677
2025 random_forest log_loss 0.6821 accuracy 0.5514
```

## 2026-05-20 Statcast 집계/Feature 연동 완료 기록

- [x] Statcast event CSV를 선수/경기 단위 품질 집계로 변환하는 모듈 추가
- [x] 타자 품질 집계 추가
  - `statcast_pa`
  - `statcast_batted_balls`
  - `statcast_hard_hit_balls`
  - `statcast_barrels`
  - `statcast_xwoba_sum/count`
  - `statcast_woba_sum/count`
  - `statcast_launch_speed_sum`
- [x] 투수 허용 품질 집계 추가
  - `statcast_batters_faced`
  - `statcast_batted_balls_allowed`
  - `statcast_hard_hit_balls_allowed`
  - `statcast_barrels_allowed`
  - `statcast_xwoba_allowed_sum/count`
  - `statcast_woba_allowed_sum/count`
  - `statcast_launch_speed_allowed_sum`
- [x] 기존 표준 `batting_logs.csv`, `pitcher_logs.csv`에 Statcast 품질 컬럼을 병합하는 경로 추가
- [x] FeatureBuilder가 Statcast 품질 컬럼이 있을 때만 고급 feature를 계산하도록 연동
- [x] CLI 추가
  - `aggregate-statcast`
  - `merge-statcast-logs`
- [x] 단위 테스트 추가 및 재실행: `24 passed`

남은 Statcast 작업:

- [x] `pybaseball` data extra 설치/확인
- [x] 2024-04-01~2024-04-07 Statcast smoke test 수집
- [x] 2024-04-01~2024-04-07 Statcast 포함 feature/품질 리포트 생성
- [x] 2021-2025 Statcast event CSV 실제 수집
- [x] 2021-2025 표준 로그에 Statcast 품질 컬럼 병합
- [x] Statcast 포함 feature/품질/holdout 리포트 별도 생성

Statcast smoke test 산출물:

```text
data/raw/statcast/statcast_2024-04-01_2024-04-07.csv  26072 rows
data/standardized/statcast_2024-04-01_2024-04-07/batting_quality.csv  1771 rows
data/standardized/statcast_2024-04-01_2024-04-07/pitching_quality.csv  738 rows
data/standardized/mlb_stats_api_2024-04-01_2024-04-07/batting_logs_statcast.csv  1894 rows
data/standardized/mlb_stats_api_2024-04-01_2024-04-07/pitcher_logs_statcast.csv  752 rows
data/processed/features_confirmed_2024-04-01_2024-04-07_with_statcast.csv  90 rows
outputs/quality/features_confirmed_2024-04-01_2024-04-07_with_statcast/
```

Smoke test 품질 확인:

```text
home_lineup_statcast_xwoba non_null: 73 / 90
away_lineup_statcast_xwoba non_null: 72 / 90
home_sp_statcast_xwoba_allowed_to_date non_null: 13 / 90
away_sp_statcast_xwoba_allowed_to_date non_null: 13 / 90
```
