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
- [x] 라인업 확정 전 예상 라인업 confidence Feature 추가
- [x] 선수 부상/휴식/결장 신호 추가
- [x] 팀 이동거리와 시차 Feature 추가
- [x] 불펜 high-leverage role 자동 추정
- [x] 선발투수 pitch-mix / Stuff 계열 Feature 검토
- [x] 딥러닝용 선수 embedding 실험 설계
- [x] 모델 앙상블 selection rule 확정
- [x] 예상 득점 모델 확장
- [x] KBO 확장 가능 schema 점검

### 연구 확장 우선순위 메모

다음 단계는 실제 경기 전 예측 품질에 바로 붙을 가능성이 높은 항목부터 진행한다.

1. 라인업 확정 전 예상 라인업 confidence Feature 추가
   - `pre_lineup`용 예상 타순 source 후보 확정
   - `lineup_source`, `lineup_confidence`, `expected_batting_order` 표준 컬럼 검토
   - confirmed lineup 대비 과거 예상 라인업 적중률 산출
   - confidence band별 holdout 성능 비교

2. 팀 이동거리와 시차 Feature 추가
   - venue 좌표 기반 팀별 이동거리 계산
   - home/away 연속 경기, 원정 연전, getaway/travel day 신호 추가
   - timezone 변화와 휴식일 결합 feature 검토
   - 이동거리 feature의 null-rate 및 holdout 성능 영향 확인

3. 불펜 high-leverage role 자동 추정
   - save/hold, games finished, 최근 등판 순서 기반 role score 설계
   - closer/setup/middle relief proxy feature 생성
   - high-leverage pitcher fatigue를 팀 bullpen fatigue와 분리 평가
   - 기존 `is_high_leverage` 수동/원천값과 자동 추정값 비교

4. 선수 부상/휴식/결장 신호 추가
   - IL, day-to-day, 최근 결장, 라인업 제외 신호 source 조사
   - 주전 결장 여부와 lineup strength 감소량 feature 설계
   - source 신뢰도와 경기 전 이용 가능 시점 기록

5. 선발투수 pitch-mix / Stuff 계열 Feature 검토
   - Statcast pitch type 비율, 구속, 회전, whiff, called-strike/whiff 계열 후보 정리
   - 선발투수 season-to-date 및 최근 N경기 pitch profile 계산
   - Stuff 계열 feature가 기존 FIP/xwOBA 허용 feature를 보완하는지 확인

완료 반영:

- 라인업 confidence/availability/rest/injury signal과 이전 경기 라인업 continuity feature를 추가했다.
- venue 좌표와 timezone offset이 있으면 팀별 이동거리, 휴식일, 시차 변화, 원정/홈 연속 경기 feature를 계산한다.
- RP save/hold/games finished/save opportunity 누적으로 high-leverage role fatigue proxy를 자동 추정한다.
- Statcast pitch type, whiff, fastball velocity, spin 기반 선발투수 pitch-mix/Stuff feature를 추가했다.
- `.venv` 기준 `pytest` 전체 통과 및 2021 시즌 feature build smoke test를 확인했다.

6. 모델 앙상블 selection rule 확정
   - 시즌별 best model 고정 대신 confidence/coverage 구간별 selection rule 검토
   - random forest, logistic, Elo, booster 모델의 calibration 차이 비교
   - rule 기반 선택과 stacking/blending 성능 비교

7. 예상 득점 모델 확장
   - 홈/원정 예상 득점, run differential, total runs target 설계
   - 승률 모델 feature와 공유 가능한 feature set 분리
   - 득점 예측 calibration 및 betting line 미사용 원칙 유지

8. 딥러닝용 선수 embedding 실험 설계
   - 선수 ID embedding, lineup sequence, pitcher/batter interaction 입력 구조 검토
   - season holdout에서 누수 없는 embedding 학습 방식 정리
   - tabular baseline 대비 이득이 있는지 소규모 실험 설계

9. KBO 확장 가능 schema 점검
   - MLB/KBO 공통 `games`, `lineups`, `batting_logs`, `pitcher_logs`, `weather`, `park_factors` schema 비교
   - KBO에서 대체 source가 필요한 컬럼 목록 작성
   - 리그 공통 feature와 리그별 feature 분리 기준 정리

완료 반영:

- `season-holdout-report`에 `model_selection_rules.csv` 산출물을 추가했다.
- `expected-runs-report` CLI를 추가해 홈/원정 예상 득점, total runs, run differential holdout metric을 생성한다.
- 선수 embedding 실험 설계를 `src/mlb_winprob/RESEARCH_EXTENSIONS.md`에 정리했다.
- KBO schema gap과 최소 smoke test 기준을 `src/mlb_winprob/KBO_SCHEMA_GAP.md`에 정리했다.

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

## 2026-05-22 모델 baseline 확정 및 다음 작업

### 완료

- [x] `MODEL_IMPROVEMENT_LOG.md` 추가
  - 모델 후보, 실험 이유, metric, 이전 대비 변화, 채택/보류/폐기 판정을 누적 기록한다.
- [x] 현재 모델 baseline 문서화
  - main baseline: `full + random_forest`
  - confidence-band challenger: `full + random_forest_shallow`
  - calibration challenger: `calibrated_logistic`
  - watchlist: `without_bullpen_role + random_forest`
- [x] `README.md`, `src/mlb_winprob/MODELS_AND_EXPERIMENTS.md`에 현재 baseline 요약 추가
- [x] `without_bullpen_role` feature variant 생성
  - `data/processed/model_experiments/features_confirmed_2021_2025_with_park_factors_statcast_without_bullpen_role.csv`
- [x] bullpen role 제거 10-seed 안정성 검증
  - output: `outputs/experiments/model_multiseed_rf_bullpen_role_confirmed_2021_2025/`
  - result: 평균 log loss/accuracy는 소폭 개선, log-loss win rate 55%
  - decision: baseline 교체는 보류, watchlist 유지
- [x] confidence-band selection rule 비교
  - output: `outputs/experiments/confidence_band_selection_rules_confirmed_2021_2025/`
  - result: `random_forest_shallow`는 `accuracy_conf_60` 개선, coverage 및 overall log loss 악화
  - decision: 기본 모델은 `random_forest`, shallow는 고확신 분석용 challenger
- [x] `pre_lineup` readiness 점검
  - output: `outputs/experiments/pre_lineup_readiness_confirmed_2021_2025/`
  - result: 현재 2021-2025 lineup/feature는 모두 `confirmed_lineup`
  - decision: projected/expected lineup source 확보 전까지 pre-game 성능 평가는 blocked
- [x] expected-runs 2022-2025 전체 holdout 재실행
  - output: `outputs/experiments/expected_runs_confirmed_2021_2025_full_check/`
  - decision: 별도 리포트로는 유효하지만 win-probability feature로 붙이려면 OOF prediction feature가 필요
- [x] booster dependency 설치 및 LightGBM/XGBoost/CatBoost 비교
  - output: `outputs/experiments/model_test_boosters_confirmed_2021_2025_with_park_factors_statcast/`
  - decision: 기본 설정 기준 booster는 RF를 대체하지 못함. CatBoost만 추후 튜닝 후보
- [x] 전체 테스트 재실행
  - command: `.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp`
  - result: `38 passed`

### 다음 우선순위

1. [x] `pre_lineup` source 확보 및 schema 검증
   - projected/expected lineup source 후보 조사
   - 표준 `lineups.csv`에 `prediction_mode=pre_lineup` row를 만들 수 있는지 검증
   - `lineup_source`, `lineup_confidence`, `expected_batting_order`, `is_expected_starter` 실제 source 매핑 확인
   - `pre_lineup` feature build smoke test 생성
   - 완료 반영:
     - `PRE_LINEUP_SOURCE_PLAN.md` 추가
     - pre-lineup 모드가 confirmed rows로 fallback하지 않도록 수정
     - `data/smoke_pre_lineup/features_pre_lineup_2024-04-01.csv` smoke build 성공

2. [x] Expected-runs OOF feature 실험
   - season holdout 기준으로 train season에서 득점 모델 학습
   - holdout season에 대해 `expected_home_runs`, `expected_away_runs`, `expected_total_runs`, `expected_run_diff` 생성
   - 해당 예측값을 win-probability feature에 추가
   - `full + random_forest` baseline 대비 log loss/brier/accuracy 변화 측정
   - 완료 반영:
     - `scripts/run_expected_runs_feature_experiment.py` 추가
     - ridge/RF-regressor OOF expected-runs 모두 평균 log loss와 accuracy 개선 실패
     - expected-runs는 adjacent report로 유지

3. [x] Bullpen high-leverage role proxy 개선
   - save/hold/games finished/save opportunity 기반 role score 재설계
   - 최근 등판 순서와 leverage proxy 가중치 점검
   - `without_bullpen_role` watchlist와 개선판을 10-seed로 재비교
   - 완료 반영:
     - estimated role score IP contribution을 `0..1`로 cap
     - `outputs/experiments/model_multiseed_rf_bullpen_role_capped_confirmed_2021_2025/`
     - baseline 판정 변화 없음

4. [x] CatBoost targeted tuning
   - 현재 기본 CatBoost는 RF보다 약함
   - depth, learning_rate, l2_leaf_reg, iterations 후보를 좁혀 소규모 holdout 비교
   - calibration 적용 전/후 비교
   - RF보다 개선되지 않으면 booster 계열은 장기 보류
   - 완료 반영:
     - `catboost_shallow`, `catboost_l2`, `catboost_lr02` 후보 추가
     - `outputs/experiments/model_test_catboost_tuning_confirmed_2021_2025_with_park_factors_statcast/`
     - RF 평균 log loss를 넘지 못해 season-dependent challenger로만 유지

5. [x] Feature stability / SHAP 정리
   - 시즌별 feature importance top feature 비교
   - SHAP summary의 시즌 간 안정성 확인
   - 유지 feature, watchlist feature, pruning 후보 feature를 `MODEL_IMPROVEMENT_LOG.md` 또는 별도 summary에 정리
   - 완료 반영:
     - `scripts/summarize_feature_stability.py` 추가
     - `outputs/experiments/feature_stability_confirmed_2021_2025/`
     - 안정 feature와 low-stability watch feature CSV 생성

6. [x] 실험 runbook 정리
   - 데이터 갱신 -> feature build -> quality report -> holdout -> model test -> decision log 업데이트 순서 문서화
   - generated output과 source/config 파일 구분
   - pytest는 Windows temp 이슈를 피하기 위해 `--basetemp .pytest_tmp` 사용 권장
   - 완료 반영:
     - `EXPERIMENT_RUNBOOK.md` 추가

### 다음 우선순위

1. [x] 실제 projected lineup source 1개를 선택해 collector/normalizer 구현
   - 후보 source의 ToS/API 조건 확인
   - `captured_at` 기준 pre-game snapshot 저장
   - historical backfill 가능 여부 확인
   - 완료 반영:
     - BALLDONTLIE MLB Lineups API collector/normalizer MVP 추가
     - `collect-balldontlie-lineups`, `standardize-balldontlie-lineups` CLI 추가
     - provider `external_game_id`/`external_player_id` 보존 및 MLBAM ID mapping 옵션 추가
     - `build-external-lineup-id-maps` CLI 추가
     - normalized name 기반 player map, game date/team pair 기반 game map 생성 경로 추가
     - 실제 운영 전 API 키, provider terms, ID map 검증 필요

2. [x] `pre_lineup` 실제 source smoke test
   - 실제 source row로 `lineups_projected_*.csv` 생성
   - `build-features --prediction-mode pre_lineup` 실행
   - confirmed-lineup feature 대비 null-rate와 성능 차이 확인
   - 선행 조건:
     - 실제 API response schema 확인
     - 자동 매핑에서 누락된 ambiguous ID 수동 검토
   - 준비 완료:
     - `scripts/run_pre_lineup_fixture_smoke.py` 추가
     - fixture-backed provider JSON -> standardize -> ID map -> re-standardize -> pre-lineup feature build 통과
     - output: `outputs/pre_lineup_fixture_smoke/`
     - result: 18 projected rows, 1 game mapped, 14 players auto-mapped, 1 pre-lineup feature row 생성
   - 실제 무료 source smoke:
     - MLB Stats API schedule/boxscore snapshot 기반 `collect-mlb-lineup-snapshots` CLI 추가
     - output: `outputs/mlb_lineup_snapshot_smoke/`
     - result: 2026-05-26 schedule 15경기, snapshot 15개, pre-lineup feature 15행 생성
     - 현재 snapshot 시점에는 공식 batting order 미게시 상태라 lineup feature는 null 유지
   - 완료 경기 공식 라인업 smoke:
     - output: `outputs/mlb_completed_lineup_smoke/`
     - result: 2026-05-25 완료 경기 13경기, 공식 lineup 234행, pre-lineup feature 13행 생성
     - result: baseline prediction CSV 생성, 9/13 winner direction 일치
     - 주의: 완료 경기 boxscore 기반이므로 공식 라인업 연결 검증용이며 true pre-game 성능 아님
   - 수동 입력 경로:
     - `write-manual-lineup-template`, `standardize-manual-lineups` CLI 추가
     - output: `outputs/manual_lineup_smoke/`
     - result: 수동 18행 라인업 입력 -> 표준 lineups -> pre-lineup feature 생성 확인
     - `fit-final-model` CLI 추가 및 `random_forest` 최종 모델 번들 생성
     - `predict --game-ids` 필터 추가
     - result: 수동 라인업 feature -> `pre_lineup` 승률 JSON 출력 확인
     - `fit-final-runs-model`, `predict-runs` CLI 추가
     - result: expected-runs 기반 언오버 baseline 생성
     - output: `outputs/mlb_completed_lineup_smoke/over_under_predictions_8_5.csv`
     - result: fixed line 8.5에서 7/13 방향 일치, 대부분 pass margin

3. [x] CatBoost season-dependent selection rule 검증
   - 2022/2024/2025 일부 holdout에서 CatBoost가 best였으므로 season별 switch가 일반화되는지 multi-seed로 확인
   - RF default를 대체하지 않고 challenger rule로만 검증
   - 완료 반영:
     - `scripts/run_multiseed_model_experiment.py` 5 seed × 4 holdout 실행
     - `outputs/experiments/catboost_season_rule_multiseed_2021_2025/`
     - 판정: season-switch rule 채택 안 함. CatBoost가 seed에 걸쳐 안정적으로 이기는 시즌은 2024뿐이며 margin도 미미(-0.00072). RF 단일 default 유지 (MODEL_IMPROVEMENT_LOG 2026-05-27)

4. [x] Stable feature group ablation
   - feature stability 결과를 기반으로 stable group / low-stability group ablation 구성
   - one-off feature 삭제 대신 그룹 단위로 log loss 영향을 확인
   - 완료 반영:
     - `scripts/run_stable_group_ablation.py` + `outputs/experiments/stable_group_ablation_confirmed_2021_2025/`
     - 안정 13개가 신호 지배(제거 시 log_loss +0.0037), 저안정 19개는 노이즈(제거해도 -0.00004)
     - 판정: full 유지. 저안정 그룹은 경량화 시 안전 prune 후보 (MODEL_IMPROVEMENT_LOG 2026-05-27)

5. [x] Windows test warning 정리
   - sklearn/joblib subprocess reader thread의 cp949 decode warning 원인 확인
   - 테스트 통과에는 영향 없지만 CI/로그 품질 개선 후보
   - 완료 반영:
     - cp949 decode warning은 현재 sklearn 1.8 환경에서 재현되지 않음(이미 해소)
     - `logistic_l1`을 deprecated `penalty="l1"` -> `l1_ratio=1.0, solver="saga"` 새 API로 마이그레이션 (sklearn 1.10 제거 대비)
     - benign LightGBM feature-name UserWarning을 `pyproject.toml` filterwarnings로 범위 한정 억제
     - 결과: `pytest` 68 passed, 0 warnings
# 2026-05-26 Score/OU baseline direction update

- [x] Confirm actual scores are stored as `home_score` / `away_score`
- [x] Train first direct OU baseline with fixed `total_line=8.5`
- [x] Add combined win + score + OU prediction output via `predict-game`
- [x] Document that expected score / expected total should be the primary output
- [x] Document that direct OU model is currently a secondary confirmation signal
- [x] Add score-model-focused holdout report for total runs and synthetic OU lines
- [x] Compare score model alternatives beyond current random forest regressor
  - 완료 반영:
    - `make_regressor`에 gradient_boosting/hist_gradient_boosting/lightgbm/xgboost/catboost regressor 추가
    - `scripts/run_score_model_comparison.py` + `outputs/experiments/score_model_comparison_confirmed_2021_2025/`
    - 판정: **catboost_regressor 채택** - 4개 holdout 전부에서 total_mae·OU@8.5 정확도 RF 대비 우위
    - 최종 번들: `outputs/final_models/runs_catboost_confirmed_2021_2025_statcast/runs_model.joblib`
    - `fit-final-runs-model --model-name` 선택지 확장 (MODEL_IMPROVEMENT_LOG 2026-05-27)
- [x] Add combined recommendation rules: pass / lean / strong
  - 완료 반영:
    - `apply_ou_pick_rules` / `summarize_ou_pick_rules` + `ou-pick-rule-report` CLI 추가 (win-pick과 동일 구조)
    - margin 기반 pass(<0.5) / lean(>=0.5) / strong(>=1.5) 규칙, scored-only/daily 지원
    - 2026 season-to-date(catboost runs) 검증: lean 60.3%(390픽), strong 70.6%(85픽), margin↑ 정확도↑ 단조
    - 테스트 3종 추가 (test_evaluation.py), pytest 86 passed
- [ ] Backfill historical game-specific market total lines and odds
- [ ] Improve predicted total calibration/dispersion around middle lines such as 8.5

# 2026-05-26 Win probability improvement

- [x] Run expected-run-diff-as-win-feature experiment
- [x] Compare baseline vs expected-runs feature variant across major classifier candidates
- [x] Confirm current overall win baseline remains `baseline + random_forest`
- [x] Identify confidence-band challengers: `random_forest_shallow`, `extra_trees`
- [x] Add dedicated confidence-band report across model candidates
- [x] Evaluate 55/58/60 confidence bands on recent completed games
- [x] Run feature group ablation for win-probability candidates
- [x] Create reduced feature table by removing optional/redundant lineup features
- [x] Formalize pass/lean/strong win-pick rules
- [x] Train/save reduced `random_forest_shallow` challenger bundle
- [x] Compare reduced shallow challenger on recent completed-week smoke
- [x] Add soft voting / booster voting / booster stacking model candidates
- [x] Run boosting/voting/stacking full-feature holdout comparison
- [x] Train final soft-voting candidate bundle
- [x] Compare soft-voting candidate on recent completed-week smoke
- [x] Build formal out-of-fold selective-pick report for main/challenger agreement
- [x] Build 2026-ready season-to-date feature pipeline before promoting ensemble models
  - 완료 반영:
    - `scripts/build_season_to_date_features.py` 추가 (명시적 snapshot 디렉터리 기반, leakage-safe)
    - 2026 Statcast 수집: `data/raw/statcast/statcast_2026.csv` 237836행
    - `data/processed/features_confirmed_2026_to_2026-05-26_with_park_factors_statcast.csv` 807행 생성
    - 5월 이후 null-rate가 과거 baseline 수준으로 정상화 (lineup statcast 0.0%, SP statcast 6.8%)
    - soft_voting recent-week 과신/오답 해소: acc 0.411->0.521, conf 0.614->0.545
- [x] Test recent-season weighting or 2024-2025-only training challenger
  - 완료 반영:
    - `scripts/run_recent_season_challenger.py` 추가 (2024-2025-only + recency-weighted RF)
    - `outputs/experiments/recent_season_challenger_2026/`
    - 판정: baseline(전 시즌) 유지. 2026 소표본에선 소폭 우위지만 2025 holdout에선 baseline이 최선 (MODEL_IMPROVEMENT_LOG 2026-05-27 참조)

# 2026-05-26 Recent-week failure diagnostics

- [x] Isolate 2026-05-23 scored games from recent completed-game smoke
- [x] Correct 2026-05-23 denominator to scored games only: `3 / 15 = 20.0%`
- [x] Check whether 2026-05-23 was a simple home/away bias
- [x] Confirm 2026-05-23 was mostly forced low-confidence picks: average favorite confidence `52.2%`
- [x] Save 2026-05-23 diagnostic CSVs under `outputs/mlb_recent_week_predictions_2026-05-19_2026-05-25/may23_diagnostics/`
- [x] Build formal pass/lean/strong rules before evaluating all recent games as actionable picks
- [x] Add daily breakdown report that excludes games without final scores
- [x] Build 2026 season-to-date feature pipeline to reduce current smoke-test distribution mismatch
  - `scripts/build_season_to_date_features.py` + 2026 Statcast 수집으로 해소 (0.1.52 참조)

# 2026-05-26 Win pick rule baseline

- [x] Add reusable `apply_win_pick_rules` and `summarize_win_pick_rules`
- [x] Add `win-pick-rule-report` CLI
- [x] Generate recent-week main RF rule reports for `53/55`, `54/57`, and `55/60`
- [x] Verify default `55/60` rule: 11 actionable picks, 7/11 correct
- [x] Verify `54/57` comparison rule: 20 actionable picks, 13/20 correct
- [x] Validate pick thresholds on historical out-of-fold predictions
- [x] Add agreement-based rule using main RF + reduced shallow + soft voting candidates

# 2026-05-28 Status Sync

## Completed Since Last Sync

- [x] Adopt score/expected-runs `catboost_regressor` after 2022-2025 holdout comparison
- [x] Add OU pass/lean/strong pick-rule utilities and CLI report
- [x] Validate OU rules on 2026 season-to-date predictions with fixed 8.5 line
- [x] Build KBO 2021-2026 canonical feature table and multi-season holdout reports
- [x] Select KBO-tuned `random_forest_shallow` final win model
- [x] Add NPB public-source collectors/standardizers for official NPB, ProEyeKyuu, and BaseballData.jp
- [x] Build ProEyeKyuu NPB 50-game canonical smoke sample
- [x] Add NPB venue enrichment, coverage report, batting-detail audit, feature-set export, and model-ready feature export
- [x] Run first NPB chronological smoke model comparison on 50 games
- [x] Document NPB public/proxy feature gaps in `src/mlb_winprob/NPB_FEATURE_GAP.md`

## Current Decisions

- [x] MLB win probability default remains `full + random_forest`
- [x] MLB score/expected-runs default is now `catboost_regressor`
- [x] KBO win model default is `full env/public-proxy + random_forest_shallow` trained on 2021-2026
- [x] NPB is pipeline-smoke ready only; no production model decision yet

## Next Priority

- [ ] Backfill real historical market totals/odds for OU validation
- [ ] Improve predicted-total calibration/dispersion around common middle lines
- [x] Test MLB Recent Form Feature Pack v1
  - Completed: weighted recent win/run-diff/runs-for/runs-allowed, low-run/5+ rates, volatility, one-run/pythag/close dependency
  - Evaluation: `outputs/experiments/mlb_recent_form_multiseed_2021_2025/`
  - Decision: do not adopt as full feature pack; baseline RF remains better by mean log_loss about 0.0015
- [ ] Build MLB Recent Form v2 as narrower ablation/overlay instead of full raw feature pack
  - Initial ablation completed: `outputs/experiments/mlb_recent_form_v2_ablation_2021_2025/`
  - Best narrow RF candidates: `pythag_only`, `volatility_only`, `scoring_only`
  - Decision: not adopted yet; lift is tiny and needs confirmation before default-model use
  - [ ] Confirm top Recent Form v2 groups with more seeds and/or recent-season holdout
  - [ ] Test the best Recent Form v2 signal as a pick-rule/reporting overlay
- [x] Expand KBO public-data sabermetric/proxy features beyond the current league-common set
  - Completed: venue seed, dome stub, empirical park factor, public batting/pitching rates, starter/lineup `_proxy` columns
  - Evaluation: `outputs/experiments/kbo/feature_stage_multiseed_kbo_2021_2026_env_public_proxy/`
  - Decision: keep upgraded KBO full + `random_forest_shallow`; baseline-like 대비 log_loss -0.00221, accuracy +1.31%p
- [ ] Backfill real KBO outdoor weather observations; current KBO weather path only supplies dome status offline
- [ ] Expand NPB beyond the 50-game ProEyeKyuu smoke sample into a full-season or multi-season canonical dataset
- [ ] Find or wire a richer NPB batting-detail source for 2B/3B/HR/BB/HBP/SF before treating lineup power/on-base features as reliable
- [ ] Re-run NPB model selection only after a materially larger sample is available
