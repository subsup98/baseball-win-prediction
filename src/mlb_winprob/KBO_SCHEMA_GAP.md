# KBO Schema Gap

The project schema can support KBO if source-specific collectors map into the same canonical tables.

Detailed KBO feature planning is tracked separately in `KBO_FEATURE_PLAN.md`.

Near-term decision: public pitch/tracking-level KBO features are considered unavailable. Build around public-data sabermetrics and explicitly named proxy features unless a verified licensed or pitch-level source is added later.

## MyKBO Stats Feasibility Check

Checked on 2026-05-27.

MyKBO Stats is useful as a secondary source, but it does not make KBO equivalent to the current MLB + Statcast pipeline.

Observed useful coverage:

- Schedule, daily game pages, current standings, and team records.
- Player handedness and primary role on player pages.
- Season batting leaderboards with OPS, BA, OBP, SLG, 1B, 2B, 3B, HR, BB, HBP, AB, and PA.
- Season pitching leaderboards with ERA, WHIP, IP, ER, R, H, HR, BB, and HBP.
- Player game logs for hitters and pitchers.
- Team splits, park splits, and win matrix pages.
- Game pages with final score context and per-game links.

Observed limitations:

- No confirmed public pitch-level Statcast equivalent.
- No public xwOBA, hard-hit, barrel, exit velocity, whiff, spin, or pitch-mix fields.
- No clearly exposed individual batter vs LHP/RHP split table on MyKBO pages checked.
- MyKBO states that it is unofficial and not affiliated with KBO, so it should not be the sole source of truth for historical archives.

Recommended use:

- Primary: KBO official site for schedule, game results, player metadata, and official season/game logs where available.
- Secondary: MyKBO Stats for English-friendly player IDs/names, handedness checks, game logs, team/park splits, and missing-data validation.
- Do not block the first KBO model on MyKBO-only advanced data. Use league-common features first.

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

## First KBO Model Feature Set

The first KBO model should be intentionally smaller than the MLB model.

Use these features if game-level batting and pitching logs can be collected:

- Starter form: season-to-date FIP, WHIP, K-BB%, FIP over last 3 starts, FIP over last 5 starts, average IP over last 3 starts, pitch count from previous start, rest days.
- Lineup quality: average OPS, OBP, SLG, weighted OPS/OBP/SLG by batting order, top-3 OPS, 3-to-5 OPS, bottom-4 OPS.
- Lineup handedness: lefty ratio, righty ratio, switch-hitter ratio, same-hand ratio against the opposing starter.
- Optional platoon approximation: lineup OPS against opposing starter hand if official KBO pitcher-type splits can be collected reliably.
- Team form: season-to-date OPS, runs per game, runs allowed per game, recent 7-game win rate, recent 10-game win rate, OPS over last 14 days, OPS over last 30 days.
- Bullpen load: bullpen FIP, bullpen WHIP, bullpen IP over last 1/3/5 days, bullpen fatigue score, closer-used-yesterday proxy if saves/role data is available.
- Environment: venue ID, dome flag, weather from venue/time join, empirical run park factor, empirical HR park factor, home-field advantage.

Defer these MLB features for KBO until better source data exists:

- Batter and pitcher Statcast xwOBA/wOBA from pitch events.
- Hard-hit rate, barrel rate, average exit velocity.
- Pitcher whiff rate, fastball velocity, spin rate, pitch-mix usage.
- High-confidence projected lineup availability before official lineup release.
- MLBAM/FanGraphs/Retrosheet/Lahman crosswalk-equivalent joins.
- Advanced bullpen leverage from pitch/play-level leverage index.

## MLB vs KBO Feature Differences

| Feature group | MLB current pipeline | KBO first model |
| --- | --- | --- |
| Game backbone | MLB Stats API schedule/feed/boxscore | KBO official schedule/results, MyKBO validation |
| Confirmed lineups | MLB boxscore/feed and Retrosheet backup | KBO official/MyKBO game pages when available |
| Player game logs | MLB Stats API and Retrosheet | KBO official logs; MyKBO player game logs as fallback |
| Player IDs | MLBAM plus Chadwick/Lahman/FanGraphs mappings | KBO official player ID plus MyKBO/Korean-name mapping |
| Handedness | MLB people endpoint and Chadwick | KBO official player detail and MyKBO player pages |
| Platoon splits | Retrosheet/Statcast-derived splits | Only if KBO pitcher-type splits are collectable; otherwise approximation from batter hand and pitcher hand |
| Statcast quality | xwOBA, hard-hit, barrel, exit velocity, whiff, velocity, spin, pitch mix | Not available in first model |
| Weather | venue coordinates plus Open-Meteo/Retrosheet | venue coordinates plus Open-Meteo; MyKBO weather only as secondary metadata |
| Park factors | empirical builder from canonical games/logs | same empirical builder once KBO venue IDs are stable |
| Bullpen roles | saves/holds/recent usage and optional role inference | saves/holds/recent usage if available; simpler role proxy first |

## Minimum Smoke Test

1. Build one KBO season into canonical CSV tables.
2. Run `build-features` in `confirmed_lineup` mode.
3. Run `feature-quality-report`.
4. Run a single-season holdout once at least two seasons are available.
5. Compare null rates against the MLB confirmed-lineup baseline.
