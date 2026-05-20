# Data And CLI

구현 파일: `data_sources.py`, `cli.py`

## 역할

`data_sources.py`는 세 가지 역할을 한다.

- CSV table 읽기/쓰기
- API/CSV/ZIP 원천 데이터 다운로드
- optional `pybaseball` adapter 제공

핵심 함수:

- `read_csv_table(path)`
- `write_csv_table(frame, path)`
- `download_url(url, output)`
- `fetch_json(url, params)`
- `write_json(data, path)`

## Collector

### MLBStatsApiCollector

MLB Stats API에서 schedule, boxscore, live feed를 수집한다.

- `schedule(start_date, end_date)`
- `boxscore(game_pk)`
- `game_feed(game_pk)`
- `people(player_ids)`
- `save_boxscores(game_ids, output_dir)`
- `save_game_feeds(game_ids, output_dir)`

### PyBaseballCollector

`pybaseball` 기반으로 Statcast와 FanGraphs leaderboard를 수집한다.

- `statcast(start_date, end_date)`
- `batting_stats(season)`
- `pitching_stats(season)`
- `statcast_batter(start_date, end_date, player_id)`
- `statcast_pitcher(start_date, end_date, player_id)`

### RetrosheetCollector

Retrosheet CSV/ZIP 파일을 다운로드한다.

지원 dataset:

- `allplayers`
- `gameinfo`
- `teamstats`
- `batting`
- `pitching`
- `fielding`
- `main_csv`
- `basic_csvs`
- `biodata`

### LahmanCollector

Chadwick Bureau Baseball Databank/Lahman core table을 다운로드한다.

주요 table:

- `People`
- `Batting`
- `Pitching`
- `Teams`
- `Fielding`
- `Appearances`
- `Parks`
- `HomeGames`

### ChadwickRegisterCollector

ID mapping용 Chadwick Register `people.csv`를 다운로드한다.

## CLI

### collect-mlb-schedule

```powershell
mlb-winprob collect-mlb-schedule `
  --start-date 2024-04-01 `
  --end-date 2024-04-01 `
  --output data/raw/mlb_stats_api/schedule_2024-04-01.csv
```

### collect-mlb-boxscores

```powershell
mlb-winprob collect-mlb-boxscores `
  --games data/raw/mlb_stats_api/schedule_2024-04-01.csv `
  --output-dir data/raw/mlb_stats_api/boxscores
```

### collect-mlb-feeds

```powershell
mlb-winprob collect-mlb-feeds `
  --games data/raw/mlb_stats_api/schedule_2024-04-01.csv `
  --output-dir data/raw/mlb_stats_api/feeds
```

### collect-mlb-people

```powershell
mlb-winprob collect-mlb-people `
  --inputs data/standardized/mlb_stats_api_2024-04-01_2024-04-07/lineups.csv `
           data/standardized/mlb_stats_api_2024-04-01_2024-04-07/pitcher_logs.csv `
           data/standardized/mlb_stats_api_2024-04-01_2024-04-07/games.csv `
  --output data/raw/mlb_stats_api/people_2024-04-01_2024-04-07.csv
```

### collect-mlb-season-dataset

```powershell
mlb-winprob collect-mlb-season-dataset `
  --start-season 2021 `
  --end-season 2025 `
  --output-root data
```

시즌별 schedule, boxscore JSON, people metadata, 표준 CSV, confirmed lineup feature CSV를 생성한다. 이미 저장된 boxscore JSON은 기본적으로 건너뛰므로 중단 후 재개할 수 있다.

### standardize-mlb-boxscores

```powershell
mlb-winprob standardize-mlb-boxscores `
  --schedule data/raw/mlb_stats_api/schedule_2024-04-01_2024-04-07.csv `
  --boxscore-dir data/raw/mlb_stats_api/boxscores_2024-04-01_2024-04-07 `
  --people data/raw/mlb_stats_api/people_2024-04-01_2024-04-07.csv `
  --output-dir data/standardized/mlb_stats_api_2024-04-01_2024-04-07 `
  --prediction-mode confirmed_lineup
```

### collect-statcast

```powershell
mlb-winprob collect-statcast `
  --start-date 2024-04-01 `
  --end-date 2024-04-07 `
  --output data/raw/statcast/statcast_2024-04-01_2024-04-07.csv
```

### aggregate-statcast

Statcast event CSV를 선수/경기 단위 품질 집계로 변환한다.

```powershell
mlb-winprob aggregate-statcast `
  --statcast data/raw/statcast/statcast_2024-04-01_2024-04-07.csv `
  --batting-output data/standardized/statcast_2024-04-01_2024-04-07/batting_quality.csv `
  --pitching-output data/standardized/statcast_2024-04-01_2024-04-07/pitching_quality.csv
```

생성되는 주요 품질 집계:

```text
statcast_xwoba_sum / count
statcast_woba_sum / count
statcast_batted_balls
statcast_hard_hit_balls
statcast_barrels
statcast_launch_speed_sum
```

### merge-statcast-logs

집계된 Statcast 품질 컬럼을 기존 표준 `batting_logs.csv`, `pitcher_logs.csv`에 병합한다.

```powershell
mlb-winprob merge-statcast-logs `
  --batting-logs data/standardized/mlb_stats_api_2024/batting_logs.csv `
  --pitcher-logs data/standardized/mlb_stats_api_2024/pitcher_logs.csv `
  --statcast-batting data/standardized/statcast_2024/batting_quality.csv `
  --statcast-pitching data/standardized/statcast_2024/pitching_quality.csv `
  --batting-output data/standardized/mlb_stats_api_2024/batting_logs_statcast.csv `
  --pitching-output data/standardized/mlb_stats_api_2024/pitcher_logs_statcast.csv
```

FeatureBuilder는 병합된 Statcast 품질 컬럼이 있을 때만 다음 계열 feature를 추가로 계산한다.

```text
lineup_statcast_xwoba
lineup_statcast_woba
lineup_hard_hit_rate
lineup_barrel_rate
lineup_avg_exit_velocity
sp_statcast_xwoba_allowed_to_date
sp_statcast_woba_allowed_to_date
sp_hard_hit_rate_allowed_to_date
sp_barrel_rate_allowed_to_date
sp_avg_exit_velocity_allowed_to_date
```

### collect-fangraphs

```powershell
mlb-winprob collect-fangraphs `
  --season 2024 `
  --table batting `
  --output data/raw/fangraphs/batting_2024.csv
```

### collect-retrosheet

```powershell
mlb-winprob collect-retrosheet `
  --dataset gameinfo `
  --output data/raw/retrosheet/gameinfo.csv
```

### collect-lahman

```powershell
mlb-winprob collect-lahman `
  --table People `
  --output data/raw/lahman/People.csv
```

### collect-chadwick-people

```powershell
mlb-winprob collect-chadwick-people `
  --output data/raw/chadwick/people.csv
```

### download-url

```powershell
mlb-winprob download-url `
  --url https://example.com/file.csv `
  --output data/raw/vendor/file.csv
```

## 다음 데이터 작업

- 2021-2025 시즌 단위 feature CSV를 구축한다.
- Statcast row를 현재 `batting_logs` / `pitcher_logs`에 병합 가능한 품질 집계로 변환하는 adapter를 추가했다.
- Retrosheet CSV를 historical fallback table로 변환한다.
