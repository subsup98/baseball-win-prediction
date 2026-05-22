# KBO Schema Gap

The project schema can support KBO if source-specific collectors map into the same canonical tables.

## Reusable Tables

- `games`
- `lineups`
- `batting_logs`
- `pitcher_logs`
- `weather`
- `park_factors`

## Required Mapping

| Canonical table | MLB source | KBO requirement |
| --- | --- | --- |
| `games` | MLB Stats API schedule | official KBO schedule, teams, venue, probable starters if available |
| `lineups` | MLB boxscore / Retrosheet | starting lineup source with batting order and player IDs |
| `batting_logs` | MLB boxscore / Retrosheet | player game batting logs with PA, hits, walks, HBP, SF, total bases |
| `pitcher_logs` | MLB boxscore / Retrosheet | pitcher game logs with role, IP, BF, pitches if available |
| `weather` | MLB boxscore / Open-Meteo | venue coordinate plus game time weather join |
| `park_factors` | empirical previous season | same empirical builder once venue IDs are stable |

## Likely Gaps

- Stable player ID crosswalk equivalent to Chadwick.
- Batter handedness and pitcher throwing hand coverage.
- Confirmed lineup availability before game time.
- Pitch-level Statcast equivalent for Stuff and pitch-mix features.
- Save/hold/games finished availability for bullpen role inference.
- Venue coordinate and timezone metadata.

## Feature Handling

Features should be split into three groups before a KBO run:

- League-common: rolling team, lineup, starter, bullpen, weather, park factor.
- Source-optional: Statcast pitch quality, pitch-mix, high-resolution batted-ball quality.
- League-specific: KBO-only roster rules, foreign-player slots, ball/park environment adjustments.

The first KBO smoke test should build only league-common features and leave source-optional columns as missing rather than inventing replacements.

## Minimum Smoke Test

1. Build one KBO season into canonical CSV tables.
2. Run `build-features` in `confirmed_lineup` mode.
3. Run `feature-quality-report`.
4. Run a single-season holdout once at least two seasons are available.
5. Compare null rates against the MLB confirmed-lineup baseline.
