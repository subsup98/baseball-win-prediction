# NPB Feature Gap Log

NPB should stay as close as possible to the MLB confirmed-lineup feature pipeline, but public NPB sources do not currently provide every MLB input.

## Implemented Near-Equivalent Features

- Game backbone: `games.csv` can use NPB public schedule/results once standardized.
- Confirmed lineup features: supported by the shared `lineups.csv` schema when source game pages expose starters.
- Batter rolling form: supported from `batting_logs.csv` using AVG/OBP/SLG-style boxscore stats.
- Starter rolling form: supported from `pitcher_logs.csv` using FIP, WHIP, K-BB%, recent starts, pitch count, and rest days where available.
- Team form: supported from canonical games and batting logs.
- Bullpen usage: supported when relief pitcher game logs are available.
- Park factors: supported by the existing empirical builder once NPB venue IDs are stable.
- Weather: supported through venue coordinates plus Open-Meteo once NPB venue metadata is created.

## Proxy Features

These columns are public-data proxies and are not direct Statcast measurements:

- `lineup_xwoba_proxy`: lineup public-data wOBA approximation.
- `lineup_hard_contact_proxy`: lineup ISO approximation.
- `sp_whiff_proxy`: starter strikeouts per batter faced.
- `sp_run_prevention_proxy`: starter FIP-style run-prevention proxy.
- `sp_command_proxy`: starter K-BB% proxy.

Proxy columns intentionally use the `_proxy` suffix so NPB/KBO runs do not confuse them with MLB Statcast fields.

## Not Available From The Current Public NPB Scope

- True xwOBA.
- Hard-hit rate.
- Barrel rate.
- Average exit velocity.
- Pitch-level whiff rate.
- Pitch velocity, spin rate, movement, release point, and extension.
- Pitch mix usage.
- High-resolution batted-ball location/quality.
- MLBAM/FanGraphs/Retrosheet/Chadwick-style crosswalks.
- Reliable pregame projected lineups before official confirmation.

## Current ProEyeKyuu Game-Page Limitations

- Game-result pages can be standardized to `games.csv`.
- Game pages can currently produce `lineups.csv`, `batting_logs.csv`, and `pitcher_logs.csv`.
- `enrich-proeyekyuu-games-starters` can backfill confirmed `home_sp_id` and `away_sp_id` from `pitcher_logs.csv`, matching the MLB feature builder's starter merge shape.
- `enrich-npb-games-venues` can attach stable venue IDs and venue metadata from `data/standardized/npb/venues_seed.csv`.
- Empirical park factors can run through the shared MLB/KBO `build-empirical-park-factors` command once venue IDs are attached. For leakage-safe modeling, use prior-season NPB canonical directories; same-season smoke output is only a pipeline check.
- `report-proeyekyuu-coverage` records game/log/lineup coverage, starter completeness, player-ID missing rate, and the current batting event-detail gap.
- The parsed game-page batting table exposes AB/R/H/RBI/SB and order/position, but not all boxscore components needed for exact OBP/SLG/wOBA reconstruction.
- `audit-proeyekyuu-batting-detail` currently confirms that parsed game batting tables do not expose 2B/3B/HR/BB/HBP/SF.
- Until a richer ProEyeKyuu game/PA table or CSV endpoint is wired in, game-page batting standardization fills missing 2B/3B/HR/BB/HBP/SF as zero and uses `total_bases = hits`, `plate_appearances = at_bats`. This keeps the shared feature pipeline runnable but makes batter/lineup power and on-base features conservative.
- Pitching tables expose IP/BF/NP/H/HR/BB/HBP/K/R/ER, so starter and bullpen public-data features are closer to the MLB canonical shape than batting features.

## Modeling Difference

NPB models should use the shared league-common feature set plus `_proxy` columns. MLB-only Statcast columns may remain present but null in NPB feature files; model selection should either exclude them for NPB runs or let the existing numeric-feature/null-handling pipeline ignore their lack of signal.

`write-npb-feature-set` exports the current NPB-usable feature list from a built feature file. The 10-game smoke run has 102 included public/proxy numeric features, while MLB-only tracking fields are explicitly excluded.

The 50-game smoke run raises this to 128 included public/proxy numeric features. The added readiness mostly comes from rolling features becoming non-null after more prior games are available; MLB-only Statcast/tracking columns remain excluded.

Use `write-npb-model-ready-features` to create a KBO-style training input. It preserves metadata/target columns plus the included public/proxy feature columns, and drops unavailable MLB-only tracking fields instead of carrying them into NPB modeling.

The first NPB prediction run is only a smoke check: 50 early-season games are split chronologically into 40 train rows and 10 test rows. It verifies that the model-ready feature file can train and score, but it is not enough data for production model selection or reliable probability calibration.
