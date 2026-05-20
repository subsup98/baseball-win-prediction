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

`pybaseball`을 통해 batting/pitching leaderboard를 저장한다.

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

주의: FanGraphs 시즌 최종값은 과거 경기 Feature에 직접 넣으면 데이터 누수다. 우선 보조/검산용으로 저장한다.

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

- 2021-2025 시즌 단위 원천 데이터와 feature CSV를 구축한다.
- Statcast event row를 handedness split과 xwOBA 집계로 변환한다.
- Retrosheet CSV를 historical fallback table로 변환한다.
