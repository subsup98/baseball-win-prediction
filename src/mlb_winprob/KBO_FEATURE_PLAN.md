# KBO Feature Plan

KBO should start with two practical tracks:

1. Public-data sabermetrics from official KBO records plus MyKBO validation.
2. MLB-to-KBO proxy features that approximate missing Statcast fields.

Video/OCR or broadcast-derived pitch tracking is deferred.

## Decision Log

- 2026-05-27: Treat public pitch/tracking-level KBO features as out of scope for the near-term model. Assume the following MLB Statcast-style fields are not realistically collectable from current public KBO data: true xwOBA, hard-hit rate, barrel rate, average exit velocity, whiff rate, pitch mix, fastball velocity, spin rate, pitch movement, release point, extension, bat tracking, and fielder movement. When future feature discussions mention these areas, use public-data sabermetrics and clearly labeled proxy features instead unless a new licensed or verified pitch-level source is available.

## Data Storage

Keep KBO files separate from MLB and NPB files.

- Raw official KBO pages/API responses: `data/raw/kbo_official/`
- Raw MyKBO fallback pages: `data/raw/mykbo_stats/`
- Standardized tables: `data/standardized/kbo/<season>/`
- Processed features: `data/processed/kbo/`
- Quality reports: `outputs/quality/kbo/`
- Experiments: `outputs/experiments/kbo/`

## Collection Status

- 2026-05-27: Added a MyKBO secondary-source collector using `requests`, BeautifulSoup/lxml link extraction, and `pandas.read_html(..., flavor="lxml")`.
- 2026-05-27: Collected 2024-2026 MyKBO season pages for `stats`, `batting_ops`, `pitching_era`, `team_splits`, `park_splits`, `schedule`, and `foreign_players`.
- Raw HTML is stored under `data/raw/mykbo_stats/<season>/`.
- Parsed CSV/link outputs are stored under `data/standardized/kbo/<season>/mykbo_tables/`.
- Collection summary is stored at `outputs/quality/kbo/mykbo_collection_2024_2026/collection_summary.csv`.
- 2026-05-27: Added `standardize-mykbo-tables` to create named secondary-source tables under `data/standardized/kbo/<season>/mykbo_standardized/`.
- Standardized MyKBO outputs now include `batting_season.csv`, `pitching_season.csv`, `team_splits.csv`, `league_summary.csv`, `foreign_players_raw.csv`, and `park_splits_raw.csv`.
- Standardized table summary is stored at `outputs/quality/kbo/mykbo_collection_2024_2026/standardized_table_summary.csv`.
- 2026-05-27: Added weekly schedule collection from `/schedule/week_of/YYYY-MM-DD` and created `data/standardized/kbo/games_mykbo_schedule_2024_2026.csv`.
- 2026-05-27: Schedule parse currently covers final, canceled, live, and scheduled games from MyKBO schedule links.
- 2026-05-27: Added sample game-page collection and table standardization. Sample outputs are stored under `data/standardized/kbo/game_pages_sample_standardized/`.
- Sample game-page standardization produced `batting_logs.csv`, `pitcher_logs.csv`, and `lineups.csv` from parsed MyKBO game pages.
- 2026-05-27: Added request throttling (`--delay`, jittered) and parallel fetch (`--workers`) to `collect-mykbo-game-pages`, plus 429 retry with `Retry-After`-aware exponential backoff in `MyKBOStatsCollector.fetch_url`. A single rate-limit response no longer aborts a batch.
- 2026-05-27: Collected all 1,752 final game pages across 2024-2026 (2024: 741, 2025: 737, 2026: 274) into `data/raw/mykbo_stats/game_pages/all/` and parsed 10,512 table files into `data/standardized/kbo/game_tables_all/`.
- 2026-05-27: Standardized full-season canonical tables to `data/standardized/kbo/canonical_2024_2026/`: `batting_logs.csv` (44,733 rows), `pitcher_logs.csv` (17,274 rows), `lineups.csv` (31,536 rows). Coverage is 100% of scheduled finals (1,752 distinct games per table).
- Quality: starter rows (batting_order 1-9) have 0% missing `mykbo_player_id` across all seasons; lineups have 0% missing `player_id`; 2 starting pitchers and 18 lineup slots per game as expected. The ~29.5% of batting rows without IDs are entirely pinch-hitters/runners with no batting order (known crosswalk gap; does not affect confirmed-lineup starters). Coverage summary: `outputs/quality/kbo/canonical_2024_2026/coverage_summary.csv`.
- First Milestone step 1 (one season into canonical tables) is complete and exceeded: three seasons of `games`/`lineups`/`batting_logs`/`pitcher_logs` are available. `weather`/`venues` remain pending. Next: build public-data sabermetric features (step 2).

## Track 2: Public-Data Sabermetrics

Build these from game logs, player metadata, lineups, and season-to-date aggregates.

- Batter: AVG, OBP, SLG, OPS, ISO, BABIP, BB%, K%, BB/K.
- Batter advanced proxy: KBO-custom wOBA, KBO-custom wRC+, OPS+.
- Starter: ERA, WHIP, FIP, xFIP proxy, K/9, BB/9, HR/9, K%, BB%, K-BB%.
- Lineup: weighted OPS/OBP/SLG by batting order, top-3 OPS, 3-to-5 OPS, bottom-4 OPS.
- Team: season-to-date OPS, runs per game, runs allowed per game, recent 7-game and 10-game win rate.
- Bullpen: bullpen FIP, bullpen WHIP, IP last 1/3/5 days, fatigue score, closer-used-yesterday proxy.
- Environment: venue, dome flag, weather join, empirical run park factor, empirical HR park factor.

Use only stats available before the target game. Do not use final season totals as pregame features.

## Track 4: MLB-to-KBO Proxy Features

Use proxy fields when Statcast-quality data is unavailable.

- `lineup_xwoba_proxy`: lineup KBO-custom wOBA, OPS, platoon approximation, and park factor.
- `lineup_hard_contact_proxy`: ISO, HR/PA, XBH/PA, BABIP trend.
- `sp_quality_proxy`: FIP, xFIP proxy, K-BB%, HR/9, recent extra-base hits allowed.
- `sp_whiff_proxy`: K%, K/9, K-BB%, recent strikeout trend.
- `pitch_mix_proxy`: unavailable by default; use only if source data exposes pitch type or pitch velocity.

Proxy fields must use `_proxy` suffix so they are not confused with real Statcast measurements.

Do not name KBO proxy columns as if they were direct Statcast measurements. For example, use `home_sp_whiff_proxy`, not `home_sp_whiff_rate_to_date`, unless real pitch-by-pitch swing/miss data becomes available.

## Deferred Track 3: Video Or Text-Relay Statcast-Lite

- Status: deferred, not part of the near-term KBO model.

- [ ] Research legal and source constraints for broadcast, highlight, and text-relay extraction.
- [ ] Evaluate whether pitch velocity, pitch type, zone, batted-ball type, and spray direction can be collected consistently.
- [ ] Prototype OCR or structured text parsing on a small set of games.
- [ ] Validate extracted pitch/play events against official boxscores.
- [ ] Decide whether the maintenance cost is worth adding this as a production source.

## First Milestone

1. Collect one KBO season into canonical `games`, `lineups`, `batting_logs`, `pitcher_logs`, `weather`, and `venues`.
2. Build public-data sabermetric features.
3. Add MLB-to-KBO proxy columns with `_proxy` suffix.
4. Run feature quality report.
5. Train a first confirmed-lineup KBO holdout model once at least two seasons are available.
