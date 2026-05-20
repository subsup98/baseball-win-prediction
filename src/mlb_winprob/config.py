"""Experiment configuration and run-version helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib
from typing import Any


@dataclass(frozen=True)
class SeasonHoldoutConfig:
    name: str
    features: list[str]
    output_dir: str
    holdout_seasons: list[int]
    models: list[str]
    prediction_mode: str = "confirmed_lineup"
    versioned_output: bool = False


def _string_list(value: Any, *, field_name: str) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"{field_name} must be a string or list of strings.")


def _int_list(value: Any, *, field_name: str) -> list[int]:
    if isinstance(value, str):
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    if isinstance(value, list) and all(isinstance(item, int) for item in value):
        return value
    raise ValueError(f"{field_name} must be a string or list of integers.")


def load_season_holdout_config(path: str | Path) -> SeasonHoldoutConfig:
    config_path = Path(path)
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    experiment = payload.get("season_holdout", payload)
    required = ["features", "output_dir"]
    missing = [field for field in required if field not in experiment]
    if missing:
        raise ValueError(f"Missing required config fields: {', '.join(missing)}")

    return SeasonHoldoutConfig(
        name=str(experiment.get("name", config_path.stem)),
        features=_string_list(experiment["features"], field_name="features"),
        output_dir=str(experiment["output_dir"]),
        holdout_seasons=_int_list(experiment.get("holdout_seasons", "2022,2023,2024,2025"), field_name="holdout_seasons"),
        models=_string_list(experiment.get("models", "elo,logistic,random_forest"), field_name="models"),
        prediction_mode=str(experiment.get("prediction_mode", "confirmed_lineup")),
        versioned_output=bool(experiment.get("versioned_output", False)),
    )


def config_digest(config: SeasonHoldoutConfig | dict[str, Any]) -> str:
    payload = asdict(config) if isinstance(config, SeasonHoldoutConfig) else config
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def versioned_output_dir(base_dir: str | Path, *, run_name: str, digest: str, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now(timezone.utc)).astimezone().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in run_name).strip("_")
    return Path(base_dir) / f"{timestamp}_{safe_name}_{digest}"


def write_run_metadata(
    output_dir: str | Path,
    *,
    config: SeasonHoldoutConfig | None,
    config_path: str | Path | None,
    feature_paths: list[str],
    row_count: int,
    column_count: int,
) -> dict[str, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    snapshot = asdict(config) if config is not None else None
    digest = config_digest(snapshot or {"feature_paths": feature_paths})
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path) if config_path is not None else None,
        "config_digest": digest,
        "feature_paths": feature_paths,
        "row_count": int(row_count),
        "column_count": int(column_count),
    }
    manifest_path = target / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths = {"manifest": manifest_path}
    if snapshot is not None:
        snapshot_path = target / "config_snapshot.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths["config_snapshot"] = snapshot_path
    return paths
