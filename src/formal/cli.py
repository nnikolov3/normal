"""Entry point for the validation pipeline.

Targets: kernel (V4/V5/V6 over the deployed kernel pair), agents (V1/V2/V3/V5),
skills (V1/V5). Exit 0 = pass with recorded exceptions; 1 = at least one FAIL;
2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from formal.checks import (
    check_forbidden_remnants,
    check_frontmatter_complete,
    check_model_pins,
    check_name_uniqueness,
    check_secret_values,
    extract_heading_numbers,
    measure_kit_master_drift,
    resolve_citations,
    verify_law_trap_bijection,
    verify_lemma_stratification,
    verify_m_code_totality,
    verify_transition_targets,
)
from formal.config import FormalConfig, load_config
from formal.frontmatter import FrontmatterError, ParsedFrontmatter, parse_frontmatter
from formal.records import ExceptionRecord, Finding

Outcome = Finding | ExceptionRecord


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate", description="Validate OpenCode artifacts")
    parser.add_argument("targets", nargs="*", choices=["kernel", "agents", "skills", "all"])
    parser.add_argument("--all", action="store_true", help="validate every target")
    parser.add_argument("--config", default="config.toml")
    arguments = parser.parse_args(argv)
    targets = ["kernel", "agents", "skills"] if arguments.all else (arguments.targets or ["all"])
    if "all" in targets:
        targets = ["kernel", "agents", "skills"]
    return run_validation(load_config(Path(arguments.config)), targets=targets)


def run_validation(config: FormalConfig, targets: list[str]) -> int:
    outcomes: list[Outcome] = []
    if "kernel" in targets:
        outcomes += validate_kernel(config)
    if "agents" in targets:
        outcomes += validate_agents(config)
    if "skills" in targets:
        outcomes += validate_skills(config)
    for outcome in outcomes:
        marker = "FAIL" if isinstance(outcome, Finding) else "EXCEPTION"
        print(f"{marker}: [{outcome.check_id}] {outcome.path}: {outcome.detail}")
    if any(isinstance(outcome, Finding) for outcome in outcomes):
        return 1
    return 0


def validate_skills(config: FormalConfig) -> list[Outcome]:
    if not config.skills_root.is_dir():
        return [ExceptionRecord("V1", str(config.skills_root), "skills root absent")]
    outcomes: list[Outcome] = []
    name_entries: list[tuple[str, str]] = []
    skill_paths = sorted(config.skills_root.glob("*/SKILL.md"))
    for skill_path in skill_paths:
        document = skill_path.read_text(encoding="utf-8")
        parsed = _parse_or_record(str(skill_path), document, outcomes)
        if parsed is None:
            continue
        outcomes += check_frontmatter_complete("skill", str(skill_path), parsed.fields)
        name_entries.append((str(skill_path), str(parsed.fields.get("name", ""))))
        outcomes += check_secret_values([(str(skill_path), document)])
    outcomes += check_name_uniqueness(name_entries)
    outcomes += check_forbidden_remnants(
        [str(path) for path in skill_paths], list(config.exclusion_terms)
    )
    return outcomes


def validate_agents(config: FormalConfig) -> list[Outcome]:
    if not config.agents_root.is_dir():
        return [ExceptionRecord("V1", str(config.agents_root), "agents root absent")]
    outcomes: list[Outcome] = []
    pin_entries: list[tuple[str, str | None]] = []
    agent_paths = sorted(config.agents_root.glob("*.md"))
    for agent_path in agent_paths:
        document = agent_path.read_text(encoding="utf-8")
        parsed = _parse_or_record(str(agent_path), document, outcomes)
        if parsed is None:
            continue
        outcomes += check_frontmatter_complete("agent", str(agent_path), parsed.fields)
        model_value = parsed.fields.get("model")
        model_pin = str(model_value) if model_value is not None else None
        pin_entries.append((str(agent_path), model_pin))
        outcomes += check_secret_values([(str(agent_path), document)])
    outcomes += check_model_pins(pin_entries, _load_model_catalog(config.model_catalog_path))
    outcomes += _citation_outcomes(config, agent_paths)
    outcomes += check_forbidden_remnants(
        [str(path) for path in agent_paths], list(config.exclusion_terms)
    )
    return outcomes


def validate_kernel(config: FormalConfig) -> list[Outcome]:
    kernel_text = _read_text(config.kernel_path)
    standards_text = _read_text(config.standards_path)
    if kernel_text is None or standards_text is None:
        detail = "kernel pair files absent"
        return [ExceptionRecord("V4", str(config.kernel_path), detail)]
    outcomes: list[Outcome] = []
    outcomes += verify_law_trap_bijection(kernel_text)
    outcomes += verify_transition_targets(kernel_text)
    outcomes += verify_m_code_totality(standards_text)
    outcomes += verify_lemma_stratification(kernel_text, standards_text)
    secret_entries = [
        (str(config.kernel_path), kernel_text),
        (str(config.standards_path), standards_text),
    ]
    outcomes += check_secret_values(secret_entries)
    outcomes += measure_kit_master_drift(
        [
            (config.kernel_path, config.kit_kernel_path),
            (config.standards_path, config.kit_standards_path),
        ]
    )
    return outcomes


def _parse_or_record(path: str, document: str, outcomes: list[Outcome]) -> ParsedFrontmatter | None:
    try:
        return parse_frontmatter(document)
    except FrontmatterError as frontmatter_error:
        outcomes.append(Finding("V1", path, f"frontmatter error: {frontmatter_error}"))
        return None


def _citation_outcomes(config: FormalConfig, agent_paths: list[Path]) -> list[Outcome]:
    kernel_text = _read_text(config.kernel_path)
    standards_text = _read_text(config.standards_path)
    if kernel_text is None or standards_text is None:
        detail = "kernel pair files absent for citation resolution"
        return [ExceptionRecord("V3", str(config.kernel_path), detail)]
    kernel_numbers = extract_heading_numbers(kernel_text)
    standards_numbers = extract_heading_numbers(standards_text)
    outcomes: list[Outcome] = []
    for agent_path in agent_paths:
        source = (str(agent_path), agent_path.read_text(encoding="utf-8"))
        outcomes += resolve_citations(source, kernel_numbers, standards_numbers)
    return outcomes


def _load_model_catalog(catalog_path: Path) -> set[str] | None:
    if not catalog_path.is_file():
        return None
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    providers = payload.get("providers") if isinstance(payload, dict) else None
    if not isinstance(providers, list):
        return None
    identifiers: set[str] = set()
    for provider in providers:
        if not isinstance(provider, dict):
            return None
        for model in provider.get("models", []):
            if isinstance(model, dict) and isinstance(model.get("id"), str):
                identifiers.add(model["id"])
    return identifiers


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
