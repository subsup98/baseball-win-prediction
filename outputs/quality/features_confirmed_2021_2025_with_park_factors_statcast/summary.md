# Feature Quality Report

Rows: 12148
Columns: 121

## Seasons

| season | rows | first_game_date | last_game_date | home_win_rate |
| --- | --- | --- | --- | --- |
| 2021 | 2429 | 2021-04-01 17:05:00+00:00 | 2021-10-03 19:20:00+00:00 | 0.5384932070811034 |
| 2022 | 2430 | 2022-04-07 18:20:00+00:00 | 2022-10-05 20:20:00+00:00 | 0.5329218106995884 |
| 2023 | 2430 | 2023-03-30 17:05:00+00:00 | 2023-10-02 17:10:00+00:00 | 0.5209876543209877 |
| 2024 | 2429 | 2024-03-20 10:05:00+00:00 | 2024-09-30 17:15:00+00:00 | 0.521613832853026 |
| 2025 | 2430 | 2025-03-18 10:10:00+00:00 | 2025-09-28 19:20:00+00:00 | 0.5427983539094651 |

## Highest Null Rates

| column | null_rate |
| --- | --- |
| park_factor_hr | 0.2148501810997695 |
| park_factor_run | 0.2148501810997695 |
| wind_direction | 0.16965755679947317 |
| sp_statcast_xwoba_allowed_diff | 0.16908133026012512 |
| sp_fip_diff | 0.12347711557458017 |
| home_sp_avg_exit_velocity_allowed_to_date | 0.10248600592690155 |
| home_sp_barrel_rate_allowed_to_date | 0.10248600592690155 |
| home_sp_hard_hit_rate_allowed_to_date | 0.10248600592690155 |
| home_sp_statcast_woba_allowed_to_date | 0.10248600592690155 |
| home_sp_statcast_xwoba_allowed_to_date | 0.10248600592690155 |
| away_sp_avg_exit_velocity_allowed_to_date | 0.10190977938755351 |
| away_sp_barrel_rate_allowed_to_date | 0.10190977938755351 |

## Rolling Feature Readiness

| season | column | null_rate_may_onward |
| --- | --- | --- |
| 2021 | home_sp_fip_last_3_starts | 0.056447688564476885 |
| 2021 | home_sp_fip_last_5_starts | 0.056447688564476885 |
| 2021 | home_sp_fip_season_to_date | 0.056447688564476885 |
| 2021 | home_sp_ip_avg_last_3_starts | 0.056447688564476885 |
| 2021 | home_sp_kbb_rate_season_to_date | 0.056447688564476885 |
| 2021 | home_sp_pitch_count_last_start | 0.056447688564476885 |
| 2021 | home_sp_rest_days | 0.056447688564476885 |
| 2021 | home_sp_whip_season_to_date | 0.056447688564476885 |
| 2022 | away_sp_fip_last_3_starts | 0.04964539007092199 |
| 2022 | away_sp_fip_last_5_starts | 0.04964539007092199 |
| 2022 | away_sp_fip_season_to_date | 0.04964539007092199 |
| 2022 | away_sp_kbb_rate_season_to_date | 0.04964539007092199 |
