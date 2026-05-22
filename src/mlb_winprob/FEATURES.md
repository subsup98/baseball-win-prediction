# Feature Builder

구현 파일: `features.py`

## 목적

`FeatureBuilder`는 raw table 여러 개를 받아 한 경기당 한 줄의 Feature Vector를 만듭니다.

```text
games
batting_logs
pitcher_logs
lineups
weather
park_factors
        ↓
FeatureBuilder.build(...)
        ↓
game-level features
```

## 입력 테이블

- `games`: 경기 정보, 홈/원정팀, 선발투수, 점수, 구장.
- `batting_logs`: 선수별 타격 경기 로그.
- `pitcher_logs`: 선수별 투구 경기 로그.
- `lineups`: 예상 또는 확정 라인업.
- `weather`: 경기별 날씨.
- `park_factors`: 구장별 득점/홈런 파크팩터.

## 주요 Feature 그룹

### 선발투수

- `sp_fip_season_to_date`
- `sp_whip_season_to_date`
- `sp_kbb_rate_season_to_date`
- `sp_fip_last_3_starts`
- `sp_fip_last_5_starts`
- `sp_ip_avg_last_3_starts`
- `sp_pitch_count_last_start`
- `sp_rest_days`
- `sp_whiff_rate_to_date`
- `sp_avg_fastball_velocity_to_date`
- `sp_avg_spin_rate_to_date`
- `sp_fastball_usage_to_date`
- `sp_breaking_ball_usage_to_date`
- `sp_offspeed_usage_to_date`

### 라인업

- `lineup_avg_ops`
- `lineup_avg_woba`
- `lineup_weighted_woba_by_order`
- `lineup_top3_woba`
- `lineup_3to5_woba`
- `lineup_bottom4_ops`
- `lineup_lefty_ratio`
- `lineup_vs_rhp_woba`
- `lineup_vs_lhp_woba`
- `lineup_platoon_woba`
- `lineup_platoon_advantage_ratio`
- `lineup_same_hand_ratio`
- `lineup_confidence`
- `lineup_available_ratio`
- `lineup_expected_starter_ratio`
- `lineup_rest_signal_count`
- `lineup_injury_absence_signal_count`
- `lineup_previous_starter_return_rate`
- `lineup_previous_starter_missing_count`

### 팀 흐름

- `team_ops_season_to_date`
- `team_woba_season_to_date`
- `team_runs_per_game_to_date`
- `team_runs_allowed_per_game_to_date`
- `team_recent_7g_win_rate`
- `team_recent_10g_win_rate`
- `team_ops_last_14d`
- `team_ops_last_30d`

### 이동/시차

- `travel_rest_days`
- `travel_distance_miles`
- `travel_timezone_shift`
- `travel_is_back_to_back`
- `travel_travel_day`
- `travel_away_game_streak`
- `travel_home_game_streak`

### 불펜

- `bullpen_fip_season_to_date`
- `bullpen_whip_season_to_date`
- `bullpen_ip_last_1d`
- `bullpen_ip_last_3d`
- `bullpen_ip_last_5d`
- `closer_used_yesterday`
- `high_leverage_rp_fatigue_score`
- `estimated_high_leverage_role_fatigue_score`
- `bullpen_fatigue_score`

### 구장/날씨

- `park_factor_run`
- `park_factor_hr`
- `temperature`
- `wind_speed`
- `wind_direction`
- `humidity`
- `is_dome`
- `home_field_advantage`

## Diff 방향

모든 diff Feature는 양수일수록 홈팀에 유리하도록 정의합니다.

```text
sp_fip_diff = away_sp_fip_season_to_date - home_sp_fip_season_to_date
lineup_woba_diff = home_lineup_avg_woba - away_lineup_avg_woba
lineup_platoon_woba_diff = home_lineup_platoon_woba - away_lineup_platoon_woba
lineup_platoon_advantage_diff = home_lineup_platoon_advantage_ratio - away_lineup_platoon_advantage_ratio
bullpen_fatigue_diff = away_bullpen_fatigue_score - home_bullpen_fatigue_score
team_woba_diff = home_team_woba_season_to_date - away_team_woba_season_to_date
lineup_confidence_diff = home_lineup_confidence - away_lineup_confidence
lineup_injury_absence_signal_diff = away_lineup_injury_absence_signal_count - home_lineup_injury_absence_signal_count
travel_distance_diff = away_travel_distance_miles - home_travel_distance_miles
travel_rest_diff = home_travel_rest_days - away_travel_rest_days
sp_whiff_rate_diff = home_sp_whiff_rate_to_date - away_sp_whiff_rate_to_date
```

## 누수 방지 기준

- 현재 경기의 타격/투구 결과는 현재 경기 Feature에 들어가지 않습니다.
- 누적값은 `cumsum - current_game_value` 방식으로 계산합니다.
- 최근 N경기 또는 최근 N일 Feature는 `shift(1)` 또는 현재 날짜 이전 window만 사용합니다.
- 테스트에서 현재 경기 기록을 극단적으로 바꿔도 현재 경기 전 Feature가 변하지 않는지 확인합니다.
