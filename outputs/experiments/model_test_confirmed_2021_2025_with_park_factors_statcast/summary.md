# Model Test Experiment

Models: `logistic, logistic_l1, logistic_l2_c03, logistic_l2_c3, random_forest, random_forest_shallow, random_forest_deep, extra_trees, hist_gradient_boosting, calibrated_logistic`

## Readout

- Overall log-loss baseline remains `random_forest`.
- `random_forest_shallow` is worse on mean log loss, but has the best mean `accuracy_conf_60`.
- `extra_trees` is not competitive on overall log loss, but can win some high-confidence selection bands with low coverage.
- `calibrated_logistic` improves over plain logistic on log loss, but still trails random forest.
- `hist_gradient_boosting` is not useful in this sklearn-only configuration.

Recommended next baseline:

- Overall model: `random_forest`
- Confidence-band challenger: `random_forest_shallow`
- Calibration challenger: `calibrated_logistic`

Do not replace the main baseline yet. The first model test did not beat `random_forest` on mean log loss.

## Mean By Model

| model_name | mean_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 |
| --- | --- | --- | --- | --- | --- |
| random_forest | 0.6795593902208138 | 0.2432917708908531 | 0.5673428666304107 | 0.6505728913404826 | 0.18623131502574347 |
| random_forest_shallow | 0.6803000921931324 | 0.24364848287444146 | 0.5652847451998909 | 0.6722572308872619 | 0.13097809052820258 |
| random_forest_deep | 0.6806813494954831 | 0.24383352354039012 | 0.5659020291505081 | 0.6471995209110275 | 0.18962658852988662 |
| extra_trees | 0.681978137219813 | 0.2444666233915698 | 0.5590083049977382 | 0.6780748432012911 | 0.07088955979445893 |
| calibrated_logistic | 0.6831314907601721 | 0.24488570694177428 | 0.5610656640355648 | 0.6154416902724036 | 0.17573676782770603 |
| logistic_l1 | 0.6861925653271552 | 0.24588892467796417 | 0.5646664870808322 | 0.6139343743860954 | 0.3974604699388561 |
| logistic_l2_c03 | 0.6886794238953553 | 0.2468848558256446 | 0.564357463909177 | 0.606528635167012 | 0.41803829583208385 |
| logistic | 0.6895865796101959 | 0.24721656766731984 | 0.5648716554256099 | 0.6047868646910187 | 0.4211248002954695 |
| logistic_l2_c3 | 0.6901425920006548 | 0.24739992964737328 | 0.5648715707153107 | 0.6048471472133183 | 0.4223597070379011 |
| hist_gradient_boosting | 0.6926315175587131 | 0.24910071892523994 | 0.5518064047763055 | 0.5996478527005218 | 0.412999430746789 |

## Best By Holdout

| holdout_season | model_name | log_loss | brier_score | accuracy | n_games | accuracy_conf_55 | coverage_conf_55 | accuracy_conf_60 | coverage_conf_60 | accuracy_conf_65 | coverage_conf_65 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | random_forest_shallow | 0.6776207965517396 | 0.24230572070481135 | 0.5740740740740741 | 2430.0 | 0.6196943972835314 | 0.48477366255144033 | 0.6631578947368421 | 0.15637860082304528 | 0.58 | 0.0205761316872428 |
| 2023 | random_forest | 0.6817111390981749 | 0.24436572941393514 | 0.5621399176954732 | 2430.0 | 0.583941605839416 | 0.5074074074074074 | 0.639412997903564 | 0.1962962962962963 | 0.75 | 0.04609053497942387 |
| 2024 | random_forest | 0.67892740117507 | 0.24295837497083775 | 0.5726636475916015 | 2429.0 | 0.6173913043478261 | 0.4734458624948539 | 0.6577017114914425 | 0.16838205022643063 | 0.6593406593406593 | 0.037463976945244955 |
| 2025 | random_forest | 0.679730691481685 | 0.2434048124683492 | 0.5584362139917696 | 2430.0 | 0.6031224322103533 | 0.5008230452674897 | 0.6523702031602708 | 0.18230452674897119 | 0.7232142857142857 | 0.04609053497942387 |
