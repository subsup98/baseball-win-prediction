# MLB Feature Plan

MLB remains the reference implementation for the project.

## Data Storage

Raw and standardized MLB data should stay separate from KBO and NPB data.

- Raw schedule/boxscore/feed: `data/raw/mlb_stats_api/`
- Raw Retrosheet: `data/raw/retrosheet/`
- Raw Statcast: `data/raw/statcast/`
- Standardized tables: `data/standardized/mlb_stats_api_<season>/`
- Processed features: `data/processed/mlb/`
- Legacy processed features may remain at `data/processed/features_*.csv` until migration.

## Current Feature Groups

- Game backbone from MLB Stats API schedule/feed/boxscore.
- Confirmed lineups from MLB boxscore/feed and Retrosheet backup.
- Batter and pitcher logs from MLB Stats API and Retrosheet.
- Handedness from MLB people metadata and Chadwick register.
- Statcast batting/pitching quality: xwOBA, wOBA, hard-hit rate, barrel rate, exit velocity.
- Statcast pitching profile: whiff rate, fastball velocity, spin rate, pitch-type usage.
- Rolling starter, lineup, team, bullpen, weather, travel, and park-factor features.

## Role In Multi-League Work

- Keep MLB as the highest-resolution benchmark.
- Use MLB feature names as the canonical vocabulary where possible.
- For KBO/NPB, preserve missing source-optional columns instead of inventing direct replacements.
- Add league-specific proxy fields only when they are clearly labeled.

