# Raw Data Collection

이 문서는 `DATA_REQUIREMENTS.md`를 실제 다운로드 명령으로 옮긴 실행 가이드다. 원칙은 원천 데이터를 먼저 `data/raw`에 보존하고, 그 다음 표준 schema로 변환하는 것이다.

## 저장 구조

```text
data/
  raw/
    mlb_stats_api/
      schedule_YYYY.csv
      schedule_YYYY-MM-DD_YYYY-MM-DD.csv
      boxscores_YYYY/
      people_YYYY.csv
      boxscores/
      feeds/
    statcast/
      statcast_YYYY-MM-DD_YYYY-MM-DD.csv
    retrosheet/
      gameinfo.csv
      teamstats.csv
      batting.csv
      pitching.csv
      main_csv.zip
    fangraphs/
      batting_YYYY.csv
      pitching_YYYY.csv
    lahman/
      People.csv
      Batting.csv
      Pitching.csv
      Teams.csv
    chadwick/
      people.csv
```

## MLB Stats API

경기 schedule을 CSV로 저장한다. 이 파일은 `games.csv` 초안의 backbone이다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-schedule `
  --start-date 2024-04-01 `
  --end-date 2024-04-01 `
  --output data/raw/mlb_stats_api/schedule_2024-04-01.csv
```

생성 컬럼 예:

```text
game_id
game_date
season
game_type
status
home_team_id
home_team
home_team_abbrev
away_team_id
away_team
away_team_abbrev
home_score
away_score
home_sp_id
home_sp_name
away_sp_id
away_sp_name
venue_id
venue_name
```

schedule CSV에 들어 있는 `game_id`를 기준으로 boxscore JSON을 저장한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-boxscores `
  --games data/raw/mlb_stats_api/schedule_2024-04-01.csv `
  --output-dir data/raw/mlb_stats_api/boxscores
```

live feed JSON을 저장한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-feeds `
  --games data/raw/mlb_stats_api/schedule_2024-04-01.csv `
  --output-dir data/raw/mlb_stats_api/feeds
```

선수 metadata를 저장한다. 이 파일은 `lineups.bats`와 `batting_logs.opposing_pitcher_hand` 보강에 사용한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-people `
  --inputs `
    data/standardized/mlb_stats_api_2024-04-01_2024-04-07/lineups.csv `
    data/standardized/mlb_stats_api_2024-04-01_2024-04-07/pitcher_logs.csv `
    data/standardized/mlb_stats_api_2024-04-01_2024-04-07/games.csv `
  --output data/raw/mlb_stats_api/people_2024-04-01_2024-04-07.csv
```

boxscore JSON을 표준 CSV로 변환한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli standardize-mlb-boxscores `
  --schedule data/raw/mlb_stats_api/schedule_2024-04-01_2024-04-07.csv `
  --boxscore-dir data/raw/mlb_stats_api/boxscores_2024-04-01_2024-04-07 `
  --people data/raw/mlb_stats_api/people_2024-04-01_2024-04-07.csv `
  --output-dir data/standardized/mlb_stats_api_2024-04-01_2024-04-07 `
  --prediction-mode confirmed_lineup
```

표준 CSV로 feature table을 생성한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli build-features `
  --games data/standardized/mlb_stats_api_2024-04-01_2024-04-07/games.csv `
  --batting-logs data/standardized/mlb_stats_api_2024-04-01_2024-04-07/batting_logs.csv `
  --pitcher-logs data/standardized/mlb_stats_api_2024-04-01_2024-04-07/pitcher_logs.csv `
  --lineups data/standardized/mlb_stats_api_2024-04-01_2024-04-07/lineups.csv `
  --weather data/standardized/mlb_stats_api_2024-04-01_2024-04-07/weather.csv `
  --prediction-mode confirmed_lineup `
  --output data/processed/features_confirmed_2024-04-01_2024-04-07.csv
```

시즌 단위로 schedule, boxscore, people metadata, 표준 CSV, feature table을 한 번에 생성한다. 장시간 수집 중 중단되어도 이미 저장된 boxscore JSON은 기본적으로 건너뛴다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-season-dataset `
  --start-season 2021 `
  --end-season 2025 `
  --output-root data
```

schedule만 먼저 받을 수도 있다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-season-dataset `
  --start-season 2021 `
  --end-season 2025 `
  --output-root data `
  --schedule-only `
  --refresh-schedule
```

시즌별 생성 파일:

```text
data/raw/mlb_stats_api/schedule_YYYY.csv
data/raw/mlb_stats_api/boxscores_YYYY/*.json
data/raw/mlb_stats_api/people_YYYY.csv
data/standardized/mlb_stats_api_YYYY/games.csv
data/standardized/mlb_stats_api_YYYY/lineups.csv
data/standardized/mlb_stats_api_YYYY/batting_logs.csv
data/standardized/mlb_stats_api_YYYY/pitcher_logs.csv
data/standardized/mlb_stats_api_YYYY/weather.csv
data/processed/features_confirmed_YYYY.csv
```

## Baseball Savant / Statcast

`pybaseball`을 통해 Statcast CSV를 저장한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-statcast `
  --start-date 2024-04-01 `
  --end-date 2024-04-07 `
  --output data/raw/statcast/statcast_2024-04-01_2024-04-07.csv
```

필요 extra:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[data]"
```

## Retrosheet

Retrosheet master CSV 또는 archive를 저장한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-retrosheet `
  --dataset gameinfo `
  --output data/raw/retrosheet/gameinfo.csv
```

표준 백업 source 변환:

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli standardize-retrosheet `
  --gameinfo data/raw/retrosheet/gameinfo.csv `
  --teamstats data/raw/retrosheet/teamstats.csv `
  --batting data/raw/retrosheet/batting.csv `
  --pitching data/raw/retrosheet/pitching.csv `
  --output-dir data/standardized/retrosheet_2021_2025 `
  --seasons 2021,2022,2023,2024,2025
```

사용 가능한 dataset:

```text
allplayers
gameinfo
teamstats
batting
pitching
fielding
main_csv
basic_csvs
biodata
```

전체 archive:

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-retrosheet `
  --dataset main_csv `
  --output data/raw/retrosheet/main_csv.zip
```

## FanGraphs

FanGraphs는 현재 모델 입력의 primary source가 아니라 보조/검산 source로 고정한다. 시즌 최종 leaderboard 값은 과거 경기 전 시점에는 알 수 없으므로 feature table에 직접 넣지 않는다. 사용 목적은 다음 세 가지다.

- Retrosheet/MLB Stats API/Statcast 기반 rolling wOBA, FIP, K-BB% 계산값 검산
- empirical park factor와 외부 park factor의 방향성 비교
- 향후 season-to-date FanGraphs split을 안정적으로 재구성할 수 있을 때만 경기 전 feature 후보로 승격

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-fangraphs `
  --season 2024 `
  --table batting `
  --output data/raw/fangraphs/batting_2024.csv
```

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-fangraphs `
  --season 2024 `
  --table pitching `
  --output data/raw/fangraphs/pitching_2024.csv
```

저장 위치:

```text
data/raw/fangraphs/batting_YYYY.csv
data/raw/fangraphs/pitching_YYYY.csv
```

주의: FanGraphs 시즌 최종값은 과거 경기 Feature에 직접 넣으면 데이터 누수다. 현재 운영 기준에서는 raw 보존과 검산만 수행한다.

## 라인업 source 운영 기준

`confirmed_lineup`은 MLB Stats API boxscore의 실제 출전/타순 정보를 primary source로 사용한다. historical fallback은 Retrosheet `teamstats.csv`의 `start_l1`~`start_l9`를 사용한다.

`pre_lineup`은 MLB Stats API schedule의 `probablePitcher`까지는 primary source로 사용하되, 예상 타순은 아직 신뢰 가능한 원천을 고정하지 않는다. 운영 기준은 다음과 같다.

- 확정 라인업 실험과 예상 라인업 실험은 반드시 `prediction_mode`로 분리한다.
- 예상 라인업 raw source를 추가할 때는 `lineups.csv`에 `prediction_mode=pre_lineup`, `lineup_source`, `lineup_confidence`를 기록한다.
- source 후보는 MLB Stats API preview/live feed lineup availability, 공식 club lineup 발표, 신뢰 가능한 lineup feed 순서로 검토한다.
- source 확정 전에는 `confirmed_lineup` 결과를 실제 성능 기준선으로 보고, `pre_lineup`은 별도 연구 확장으로 둔다.

## Lahman / Baseball Databank

Chadwick Bureau Baseball Databank core table을 저장한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-lahman `
  --table People `
  --output data/raw/lahman/People.csv
```

주요 table:

```text
People
Batting
Pitching
Teams
Fielding
Appearances
Parks
HomeGames
```

전체 archive:

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-lahman `
  --archive `
  --output data/raw/lahman/baseballdatabank_master.zip
```

## Chadwick Register

선수 ID mapping용 people.csv를 저장한다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-chadwick-people `
  --output data/raw/chadwick/people.csv
```

ID crosswalk 생성:

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli build-id-map `
  --chadwick-people data/raw/chadwick/people.csv `
  --mlb-people data/raw/mlb_stats_api/people_2021.csv data/raw/mlb_stats_api/people_2022.csv data/raw/mlb_stats_api/people_2023.csv data/raw/mlb_stats_api/people_2024.csv data/raw/mlb_stats_api/people_2025.csv `
  --output data/processed/id_map.csv
```

## Generic Download

필요한 CSV/ZIP URL이 따로 있으면 그대로 저장할 수 있다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli download-url `
  --url https://example.com/file.csv `
  --output data/raw/vendor/file.csv
```

## 검증 기록

2026-05-15에 아래 명령으로 실제 MLB Stats API 수집을 검증했다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-schedule `
  --start-date 2024-04-01 `
  --end-date 2024-04-01 `
  --output data/raw/mlb_stats_api/schedule_2024-04-01.csv
```

결과:

```text
14 MLB Stats API schedule rows
```

2026-05-15에 `2024-04-01`부터 `2024-04-07`까지의 실제 수집/표준화/feature 생성을 검증했다.

결과:

```text
schedule rows: 92
boxscore JSON files: 92
standardized games rows: 90
standardized lineups rows: 1620
lineups.bats non-null ratio: 1.0
feature rows: 90
feature columns: 90
```

2026-05-15에 시즌 단위 수집 파이프라인을 2024년 5경기 제한으로 smoke test했다.

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli collect-mlb-season-dataset `
  --start-season 2024 `
  --end-season 2024 `
  --output-root data\smoke_multi_year `
  --limit 5 `
  --refresh-schedule `
  --refresh-people
```

결과:

```text
schedule rows: 2429
boxscore JSON files: 5
people rows: 119
feature rows: 5
feature columns: 90
```

## 다음 단계

- FanGraphs raw leaderboard를 시즌별로 보존하고 검산 리포트를 추가한다.
- 예상 라인업 source가 확정되면 `lineup_source`와 `lineup_confidence` 컬럼을 표준 schema에 추가한다.
- SHAP 리포트 산출물이 필요한 환경에는 `.[explain]` extra를 설치한다.
