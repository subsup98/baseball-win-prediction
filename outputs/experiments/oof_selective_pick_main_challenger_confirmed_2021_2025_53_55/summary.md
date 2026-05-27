# OOF Selective Pick Report

Models: `random_forest, random_forest_shallow, soft_voting`
Primary model: `random_forest`
Agreement challengers: `random_forest_shallow, soft_voting`
Thresholds: lean `0.53`, strong `0.55`

## Actionable Summary

| rule_name | model_name | rule | games | picks | hits | accuracy | coverage | avg_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| model:random_forest | random_forest | actionable | 6636 | 6636 | 3894.0 | 0.5867992766726944 | 0.6827862948863052 | 0.5803632316912235 |
| model:random_forest_shallow | random_forest_shallow | actionable | 6191 | 6191 | 3634.0 | 0.5869811015990954 | 0.6369996913262681 | 0.5728543789307166 |
| model:soft_voting | soft_voting | actionable | 6647 | 6647 | 3964.0 | 0.5963592598164585 | 0.6839180985698117 | 0.5783228968630506 |
| agreement | random_forest | actionable | 6287 | 6287 | 3707.0 | 0.5896293939875934 | 0.6468772507459615 | 0.5824408813374788 |

## Agreement By Holdout

| holdout_season | rule | games | picks | hits | accuracy | coverage | avg_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | actionable | 1557 | 1557 | 925.0 | 0.5940912010276173 | 0.6407407407407407 | 0.5855455435466355 |
| 2023 | actionable | 1586 | 1586 | 916.0 | 0.5775535939470365 | 0.6526748971193416 | 0.582946246430695 |
| 2024 | actionable | 1544 | 1544 | 928.0 | 0.6010362694300518 | 0.6356525319061342 | 0.5796876413293044 |
| 2025 | actionable | 1600 | 1600 | 938.0 | 0.58625 | 0.6584362139917695 | 0.5815755903844311 |
