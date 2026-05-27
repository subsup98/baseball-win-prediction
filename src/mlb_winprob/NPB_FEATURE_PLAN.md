# NPB Feature Plan

NPB should follow the same multi-league design as KBO, but implementation should start after KBO because source access and reuse restrictions need a separate review.

## Data Storage

Keep NPB files separate from MLB and KBO files.

- Raw official NPB pages/API responses: `data/raw/npb_official/`
- Raw secondary NPB sources: `data/raw/npb_secondary/`
- Standardized tables: `data/standardized/npb/<season>/`
- Processed features: `data/processed/npb/`
- Quality reports: `outputs/quality/npb/`
- Experiments: `outputs/experiments/npb/`

## Initial Feature Direction

Reuse the KBO first-model approach unless a better NPB source is found.

- Public-data sabermetrics from official or stable public records.
- League-common rolling features: starter, lineup, team, bullpen, weather, and park factor.
- MLB-to-NPB proxy fields for missing Statcast-quality measurements.
- League-specific adjustments for NPB roster rules, ball/park context, and interleague structure.

## Expected Gaps

- Public Statcast-equivalent pitch tracking is not assumed.
- Player ID crosswalks need source-specific design.
- Confirmed pregame lineups may need a separate source.
- Batter vs pitcher-hand splits may not be consistently available from official pages.

## First Milestone

1. Verify legal/source constraints for official NPB data reuse.
2. Collect one NPB season into canonical tables.
3. Build league-common and proxy features.
4. Compare null rates and model lift against KBO and MLB baselines.

