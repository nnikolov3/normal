"""Configuration loading for the validation pipeline."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FormalConfig:
    skills_root: Path
    agents_root: Path
    kernel_path: Path
    standards_path: Path
    kit_kernel_path: Path
    kit_standards_path: Path
    model_catalog_path: Path
    exclusion_terms: tuple[str, ...]


def load_config(config_path: Path) -> FormalConfig:
    document = tomllib.loads(config_path.read_text(encoding="utf-8"))
    paths = document["paths"]
    default_catalog = str(config_path.parent / "model-catalog.json")
    return FormalConfig(
        skills_root=Path(paths["skills_root"]),
        agents_root=Path(paths["agents_root"]),
        kernel_path=Path(paths["kernel_path"]),
        standards_path=Path(paths["standards_path"]),
        kit_kernel_path=Path(paths["kit_kernel_path"]),
        kit_standards_path=Path(paths["kit_standards_path"]),
        model_catalog_path=Path(paths.get("model_catalog_path", default_catalog)),
        exclusion_terms=tuple(document.get("exclusions", {}).get("terms", [])),
    )
