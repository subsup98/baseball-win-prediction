# 데이터 요구사항

이 문서는 현재 설계된 Feature를 만들기 위해 필요한 원천 데이터와 source별 역할을 정리한다. 기준은 MVP가 아니라 최종적으로 좋은 승률 예측 모델을 만들기 위한 전체 Feature set이다.

## 결론

하나의 데이터 source만으로는 부족하다. 우리 Feature는 경기 정보, 라인업, 선수 경기 로그, Statcast 이벤트, 불펜 사용량, 구장/날씨, ID 매핑이 모두 필요하다.

권장 조합:

```text
MLB Stats API
  → 경기/일정/라인업/boxscore backbone

Baseball Savant / Statcast
  → pitch/PA 이벤트와 고급 타구/투구 품질

Retrosheet
  → historical game log, 라인업, 날씨, game log 백업

FanGraphs
  → 고급 세이버 지표와 park factor 보조

Lahman
  → ID/meta/시즌 누적 보조
```

## 우리 표준 테이블

| 테이블 | 목적 | 주 source | 보조 source |
|---|---|---|---|
| `games.csv` | 경기 단위 뼈대, 타깃 생성 | MLB Stats API | Retrosheet |
| `lineups.csv` | 오늘 출전 타자 구성 | MLB Stats API | Retrosheet |
| `batting_logs.csv` | 타자 rolling OPS/wOBA/ISO 계산 | Retrosheet, Statcast 집계 | MLB Stats API boxscore |
| `pitcher_logs.csv` | 선발/불펜 FIP, WHIP, K-BB%, 피로도 계산 | Retrosheet, MLB Stats API boxscore | Statcast 집계 |
| `statcast_events.csv` | 좌우 매치업, xwOBA, 타구/투구 품질 | Baseball Savant / Statcast | pybaseball |
| `weather.csv` | 온도, 바람, 습도, 돔 여부 | Retrosheet, MLB Stats API | 외부 weather API |
| `park_factors.csv` | 구장 득점/홈런 보정 | FanGraphs | Lahman Teams |
| `id_map.csv` | MLBAM/FanGraphs/Retrosheet/Lahman ID 연결 | Lahman, Chadwick register | MLB Stats API |

## Feature별 필요 데이터

### 선발투수 Feature

대상 Feature:

```text
sp_fip_season_to_date
sp_whip_season_to_date
sp_kbb_rate_season_to_date
sp_fip_last_3_starts
sp_fip_last_5_starts
sp_ip_avg_last_3_starts
sp_pitch_count_last_start
sp_rest_days
```

필요 raw 값:

```text
game_id
game_date
season
team
player_id
is_start or role
innings_pitched
hits
home_runs
walks
hit_by_pitch
strikeouts
batters_faced
pitches
```

주 source:

- MLB Stats API boxscore
- Retrosheet pitching
- Statcast pitch aggregation

### 라인업 Feature

대상 Feature:

```text
lineup_avg_ops
lineup_avg_woba
lineup_weighted_woba_by_order
lineup_top3_woba
lineup_3to5_woba
lineup_bottom4_ops
lineup_lefty_ratio
lineup_vs_rhp_woba
lineup_vs_lhp_woba
lineup_platoon_woba
lineup_platoon_advantage_ratio
lineup_same_hand_ratio
```

필요 raw 값:

```text
game_id
game_date
team
player_id
batting_order
bats
prediction_mode
opposing_pitcher_hand
at_bats
hits
doubles
triples
home_runs
walks
hit_by_pitch
sacrifice_flies
total_bases
plate_appearances
```

주 source:

- MLB Stats API lineups / boxscore
- Retrosheet teamstats / batting
- Statcast events for handedness split

### 팀 흐름 Feature

대상 Feature:

```text
team_ops_season_to_date
team_woba_season_to_date
team_runs_per_game_to_date
team_runs_allowed_per_game_to_date
team_recent_7g_win_rate
team_recent_10g_win_rate
team_ops_last_14d
team_ops_last_30d
```

필요 raw 값:

```text
game_id
game_date
season
home_team
away_team
home_score
away_score
team batting totals
```

주 source:

- MLB Stats API schedule / boxscore
- Retrosheet gameinfo / teamstats

### 불펜 Feature

대상 Feature:

```text
bullpen_fip_season_to_date
bullpen_whip_season_to_date
bullpen_ip_last_1d
bullpen_ip_last_3d
bullpen_ip_last_5d
closer_used_yesterday
high_leverage_rp_fatigue_score
bullpen_fatigue_score
```

필요 raw 값:

```text
game_id
game_date
season
team
player_id
role or is_start
innings_pitched
hits
home_runs
walks
hit_by_pitch
strikeouts
batters_faced
pitches
is_closer
is_high_leverage
save / hold / leverage proxy
```

주 source:

- MLB Stats API boxscore
- Retrosheet pitching
- Statcast pitch aggregation

주의:

- `is_closer`, `is_high_leverage`는 원천 데이터에 항상 명시되지 않을 수 있다.
- 초기는 save/hold/recent usage 기반으로 추정하고, 이후 leverage 지표를 보강한다.

### 구장/날씨 Feature

대상 Feature:

```text
park_factor_run
park_factor_hr
temperature
wind_speed
wind_direction
humidity
is_dome
home_field_advantage
```

필요 raw 값:

```text
game_id
venue_id
venue_name
season
temperature
wind_speed
wind_direction
humidity
roof/dome 여부
park_factor_run
park_factor_hr
```

주 source:

- MLB Stats API venue / game metadata
- Retrosheet gameinfo weather fields
- FanGraphs park factors
- Lahman Teams `BPF`, `PPF` 보조

### 좌우 매치업 Feature

필요 raw 값:

```text
batter
pitcher
stand
p_throws
events
woba_value
babip_value
iso_value
estimated_woba_using_speedangle
```

주 source:

- Baseball Savant / Statcast

### Diff Feature

대상 Feature:

```text
sp_fip_diff
lineup_woba_diff
bullpen_fatigue_diff
team_woba_diff
```

필요 raw 값:

- 홈/원정 각각의 계산 완료 Feature.
- 방향은 항상 `positive = home advantage`.

## Source별 가져올 값

### MLB Stats API

역할:

- 경기 일정과 최종 결과의 backbone.
- 현재/미래 경기의 probable pitcher와 confirmed lineup 확보.
- venue와 boxscore 확보.

필요 값:

```text
gamePk
gameDate
season
gameType
status
teams.home.team.id
teams.home.team.name
teams.home.score
teams.away.team.id
teams.away.team.name
teams.away.score
venue.id
venue.name
probablePitcher
boxscore teams.home.players
boxscore teams.away.players
battingOrder
pitching stats
batting stats
```

### Baseball Savant / Statcast

역할:

- pitch/event 단위 세부 성능.
- 좌우 매치업과 xwOBA, 타구/투구 품질.

필요 값:

```text
game_pk
game_date
home_team
away_team
batter
pitcher
player_name
events
description
stand
p_throws
pitch_type
release_speed
release_spin_rate
zone
launch_speed
launch_angle
estimated_woba_using_speedangle
woba_value
babip_value
iso_value
```

### Retrosheet

역할:

- historical game log 안정성.
- 선발 라인업, 날씨, 타자/투수 game log 백업.

필요 파일/값:

```text
gameinfo.csv
  gid
  date
  visteam
  hometeam
  site
  temp
  winddir
  windspeed
  vruns
  hruns

teamstats.csv
  gid
  team
  batting/pitching totals
  start_l1 ... start_l9

batting.csv
  gid
  player
  team
  batting stats

pitching.csv
  gid
  player
  team
  pitching stats
  gs
  p_seq
```

### FanGraphs

역할:

- 검증된 고급 세이버 지표 보조와 검산.
- park factor 보조 비교.
- 현재 운영 기준에서는 시즌 최종 leaderboard를 모델 입력에 직접 사용하지 않는다.

필요 값:

```text
player_id
season
team
wOBA
wRC+
ISO
BABIP
FIP
xFIP
WHIP
K%
BB%
K-BB%
WAR
park_factor_run
park_factor_hr
```

주의:

- 시즌 최종 FanGraphs 값을 과거 경기 Feature로 그대로 쓰면 데이터 누수다.
- rolling 또는 season-to-date 계산이 안 되는 값은 보조/검산용으로 우선 사용한다.
- 경기 전 시점으로 재구성 가능한 split/source가 확보되기 전까지 FanGraphs 값은 raw 보존과 품질 검산에만 사용한다.

### 라인업 source 결정

`confirmed_lineup`:

- primary: MLB Stats API boxscore의 실제 출전 선수와 `battingOrder`.
- fallback: Retrosheet `teamstats.csv`의 선발 라인업 컬럼.
- 용도: historical backtest의 기준 feature set.

`pre_lineup`:

- primary 확정 전: MLB Stats API schedule의 probable pitcher만 고정 사용.
- 예상 타순 source는 별도 raw source가 확정될 때까지 연구 확장 항목으로 둔다.
- source 추가 시 `prediction_mode=pre_lineup`, `lineup_source`, `lineup_confidence`를 함께 기록한다.

### Lahman

역할:

- 선수/팀 ID와 시즌 누적 기록 보조.
- 오래된 시즌 baseline과 팀 메타데이터 보조.

필요 테이블/값:

```text
People
  playerID
  nameFirst
  nameLast
  bats
  throws

Batting
  playerID
  yearID
  teamID
  G
  AB
  H
  2B
  3B
  HR
  BB
  SO

Pitching
  playerID
  yearID
  teamID
  W
  L
  G
  GS
  IPouts
  ERA
  HR
  BB
  SO

Teams
  yearID
  teamID
  teamIDretro
  W
  L
  R
  RA
  BPF
  PPF
```

## 수집 순서

1. MLB Stats API로 `games.csv`, `lineups.csv` 초안을 만든다.
2. Retrosheet로 historical `games`, `lineups`, `batting_logs`, `pitcher_logs`, `weather`를 보강한다.
3. Statcast로 `statcast_events.csv`를 만들고 handedness/xwOBA/타구 품질 집계를 만든다.
4. Lahman 또는 Chadwick register로 `id_map.csv`를 만든다.
5. FanGraphs park factor와 고급 지표를 보조 테이블로 붙인다.
6. 표준 raw table을 만든 뒤 `FeatureBuilder`로 `data/processed/features_*.csv`를 생성한다.

## 데이터 누수 방지 규칙

- 경기일 이후 데이터는 어떤 Feature에도 사용하지 않는다.
- FanGraphs 시즌 최종 지표는 과거 경기 Feature에 직접 넣지 않는다.
- rolling feature는 현재 경기 결과를 제외한다.
- predicted/probable 정보와 confirmed 정보는 `prediction_mode`로 분리한다.
- source별 raw 데이터의 수집일과 적용 가능 시점을 기록한다.
