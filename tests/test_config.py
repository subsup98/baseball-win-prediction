from datetime import datetime, timezone

from mlb_winprob.config import (
    SeasonHoldoutConfig,
    config_digest,
    load_season_holdout_config,
    versioned_output_dir,
    write_run_metadata,
)


def test_load_season_holdout_config(tmp_path):
    path = tmp_path / "experiment.toml"
    path.write_text(
        """
[season_holdout]
name = "demo"
features = ["data/features.csv"]
output_dir = "outputs/experiments/versioned"
holdout_seasons = [2024, 2025]
models = ["elo", "random_forest"]
prediction_mode = "confirmed_lineup"
versioned_output = true
""".strip(),
        encoding="utf-8",
    )

    config = load_season_holdout_config(path)

    assert config.name == "demo"
    assert config.features == ["data/features.csv"]
    assert config.holdout_seasons == [2024, 2025]
    assert config.models == ["elo", "random_forest"]
    assert config.versioned_output is True


def test_versioned_output_dir_is_stable_shape():
    config = SeasonHoldoutConfig(
        name="demo run",
        features=["features.csv"],
        output_dir="outputs",
        holdout_seasons=[2025],
        models=["random_forest"],
    )
    output = versioned_output_dir(
        "outputs",
        run_name=config.name,
        digest=config_digest(config),
        now=datetime(2026, 5, 20, 8, 0, 0, tzinfo=timezone.utc),
    )

    assert str(output).endswith(f"20260520_170000_demo_run_{config_digest(config)}")


def test_write_run_metadata(tmp_path):
    config = SeasonHoldoutConfig(
        name="demo",
        features=["features.csv"],
        output_dir=str(tmp_path),
        holdout_seasons=[2025],
        models=["random_forest"],
    )

    paths = write_run_metadata(
        tmp_path,
        config=config,
        config_path="configs/demo.toml",
        feature_paths=config.features,
        row_count=10,
        column_count=4,
    )

    assert paths["manifest"].exists()
    assert paths["config_snapshot"].exists()
    assert '"row_count": 10' in paths["manifest"].read_text(encoding="utf-8")
