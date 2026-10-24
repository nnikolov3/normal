"""Tests for the Hermes context freshness check (V7) and its CLI target.

A generated .hermes.md is a build artifact of the kernel pair plus the project
binding. The freshness check regenerates the expected context in memory and
fails on drift, on a missing artifact, and records an exception when a source
is missing so the check cannot run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from formal.hermes_gen import (
    build_project_context,
    write_hermes_context,
)
from formal.records import ExceptionRecord, Finding

KERNEL_TEXT = "# Kernel\n\nA choice without a rule is a question.\n"
STANDARDS_TEXT = "# Coding Standards\n\nCERTIFIED is the only terminal.\n"
BINDING_TEXT = "# Naudible\n\nRebuild before every ./bin/naudibled call.\n"


class _FreshnessConfig:
    def __init__(self, tmp_path: Path) -> None:
        self.kernel_path = tmp_path / "kernel.md"
        self.standards_path = tmp_path / "standards.md"
        self.project_dir = tmp_path / "proj"
        self.kernel_path.write_text(KERNEL_TEXT, encoding="utf-8")
        self.standards_path.write_text(STANDARDS_TEXT, encoding="utf-8")
        self.project_dir.mkdir()
        (self.project_dir / "AGENTS.md").write_text(BINDING_TEXT, encoding="utf-8")
        self.hermes_projects = (self.project_dir,)


def test_check_context_freshness_when_file_matches_regeneration_then_no_outcomes(
    tmp_path: Path,
) -> None:
    from formal.hermes_gen import check_context_freshness

    config = _FreshnessConfig(tmp_path)
    context = build_project_context("proj", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    write_hermes_context(config.project_dir, context)
    assert check_context_freshness(config) == []


def test_check_context_freshness_when_file_drifts_then_finding(
    tmp_path: Path,
) -> None:
    from formal.hermes_gen import check_context_freshness

    config = _FreshnessConfig(tmp_path)
    context = build_project_context("proj", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    written_path = write_hermes_context(config.project_dir, context)
    written_path.write_text(context + "\nstale suffix\n", encoding="utf-8")
    outcomes = check_context_freshness(config)
    assert len(outcomes) == 1
    drift_finding = outcomes[0]
    assert isinstance(drift_finding, Finding)
    assert drift_finding.check_id == "V7"
    assert "drift" in drift_finding.detail


def test_check_context_freshness_when_artifact_missing_then_finding(
    tmp_path: Path,
) -> None:
    from formal.hermes_gen import check_context_freshness

    config = _FreshnessConfig(tmp_path)
    outcomes = check_context_freshness(config)
    assert len(outcomes) == 1
    missing_finding = outcomes[0]
    assert isinstance(missing_finding, Finding)
    assert missing_finding.check_id == "V7"
    assert "not generated" in missing_finding.detail


def test_check_context_freshness_when_binding_missing_then_exception(
    tmp_path: Path,
) -> None:
    from formal.hermes_gen import check_context_freshness

    config = _FreshnessConfig(tmp_path)
    (config.project_dir / "AGENTS.md").unlink()
    outcomes = check_context_freshness(config)
    assert len(outcomes) == 1
    exception_record = outcomes[0]
    assert isinstance(exception_record, ExceptionRecord)
    assert exception_record.check_id == "V7"


def test_check_context_freshness_when_no_projects_then_exception(
    tmp_path: Path,
) -> None:
    from formal.hermes_gen import check_context_freshness

    config = _FreshnessConfig(tmp_path)
    config.hermes_projects = ()
    outcomes = check_context_freshness(config)
    assert len(outcomes) == 1
    exception_record = outcomes[0]
    assert isinstance(exception_record, ExceptionRecord)


def test_validate_hermes_target_when_drift_detected_then_fails_with_v7(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from formal import cli
    from formal.hermes_gen import build_project_context, write_hermes_context

    kernel_path = tmp_path / "kernel.md"
    standards_path = tmp_path / "standards.md"
    kernel_path.write_text(KERNEL_TEXT, encoding="utf-8")
    standards_path.write_text(STANDARDS_TEXT, encoding="utf-8")
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "AGENTS.md").write_text(BINDING_TEXT, encoding="utf-8")
    context = build_project_context("proj", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    written_path = write_hermes_context(project_dir, context)
    written_path.write_text(context + "\nstale suffix\n", encoding="utf-8")

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[paths]\n"
        f'skills_root = "{tmp_path}/skills"\n'
        f'agents_root = "{tmp_path}/agents"\n'
        f'kernel_path = "{kernel_path}"\n'
        f'standards_path = "{standards_path}"\n'
        f'kit_kernel_path = "{tmp_path}/kit-kernel.md"\n'
        f'kit_standards_path = "{tmp_path}/kit-standards.md"\n'
        "[hermes]\n"
        f'projects = ["{project_dir}"]\n',
        encoding="utf-8",
    )

    exit_code = cli.main(["hermes", "--config", str(config_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "FAIL" in captured.out
    assert "V7" in captured.out
    assert "drift" in captured.out
