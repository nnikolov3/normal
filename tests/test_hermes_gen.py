"""Tests for the Hermes project-context generator (formal.hermes_gen).

The generated .hermes.md is a build artifact, never a knowledge home: it
concatenates kernel, coding standards, and the project binding verbatim so
Hermes (one project context file per session) sees all three. Provenance and
regeneration instructions live in the header.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from formal.hermes_gen import (
    build_project_context,
    build_project_context_from_paths,
    load_hermes_projects,
    write_hermes_context,
)

KERNEL_TEXT = "# Kernel\n\nA choice without a rule is a question.\n"
STANDARDS_TEXT = "# Coding Standards\n\nCERTIFIED is the only terminal.\n"
BINDING_TEXT = "# Naudible\n\nRebuild before every ./bin/naudibled call.\n"


def _write_source(tmp_path: Path, name: str, text: str) -> Path:
    source_path = tmp_path / name
    source_path.write_text(text, encoding="utf-8")
    return source_path


def test_build_project_context_when_given_sources_then_orders_kernel_standards_binding() -> None:
    context = build_project_context("naudible", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    kernel_position = context.index(KERNEL_TEXT)
    standards_position = context.index(STANDARDS_TEXT)
    binding_position = context.index(BINDING_TEXT)
    assert kernel_position < standards_position < binding_position


def test_build_project_context_when_built_then_header_names_project_and_regeneration() -> None:
    context = build_project_context("naudible", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    header = context.split("---")[0]
    assert "naudible" in header
    assert "do not edit" in header.lower()
    assert "formal" in header


def test_build_project_context_when_built_then_sources_stay_verbatim() -> None:
    context = build_project_context("naudible", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    assert KERNEL_TEXT in context
    assert STANDARDS_TEXT in context
    assert BINDING_TEXT in context


def test_build_project_context_when_built_then_header_avoids_injection_patterns() -> None:
    context = build_project_context("naudible", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    forbidden = [
        "ignore previous instructions",
        "disregard your rules",
        "system prompt override",
        "<!--",
    ]
    for pattern in forbidden:
        assert pattern not in context


def test_build_project_context_from_paths_when_kernel_missing_then_raises_file_not_found(
    tmp_path: Path,
) -> None:
    kernel_path = tmp_path / "absent-kernel.md"
    with pytest.raises(FileNotFoundError):
        build_project_context_from_paths(
            project_name="naudible",
            binding_path=_write_source(tmp_path, "AGENTS.md", BINDING_TEXT),
            kernel_path=kernel_path,
            standards_path=_write_source(tmp_path, "CODING_STANDARDS.md", STANDARDS_TEXT),
        )


def test_load_hermes_projects_when_configured_then_returns_expanded_paths() -> None:
    config = {"hermes": {"projects": ["~/naudible", "~/nanki"]}}
    projects = load_hermes_projects(config)
    assert projects == [Path.home() / "naudible", Path.home() / "nanki"]


def test_load_hermes_projects_when_section_absent_then_returns_empty_list() -> None:
    assert load_hermes_projects({}) == []


def test_write_hermes_context_when_called_then_file_lands_at_project_root(tmp_path: Path) -> None:
    context = build_project_context("naudible", BINDING_TEXT, KERNEL_TEXT, STANDARDS_TEXT)
    written_path = write_hermes_context(tmp_path, context)
    assert written_path == tmp_path / ".hermes.md"
    assert written_path.read_text(encoding="utf-8") == context


def test_build_project_context_from_paths_when_run_then_concatenates_files(
    tmp_path: Path,
) -> None:
    binding_path = _write_source(tmp_path, "AGENTS.md", BINDING_TEXT)
    kernel_path = _write_source(tmp_path, "kernel.md", KERNEL_TEXT)
    standards_path = _write_source(tmp_path, "standards.md", STANDARDS_TEXT)
    context = build_project_context_from_paths(
        project_name="naudible",
        binding_path=binding_path,
        kernel_path=kernel_path,
        standards_path=standards_path,
    )
    assert KERNEL_TEXT in context
    assert STANDARDS_TEXT in context
    assert BINDING_TEXT in context


def _write_tmp_config(tmp_path: Path) -> Path:
    project_dirs = [tmp_path / "proj-a", tmp_path / "proj-b"]
    for project_dir in project_dirs:
        project_dir.mkdir()
        (project_dir / "AGENTS.md").write_text(BINDING_TEXT, encoding="utf-8")
    kernel_path = _write_source(tmp_path, "kernel.md", KERNEL_TEXT)
    standards_path = _write_source(tmp_path, "standards.md", STANDARDS_TEXT)
    projects_toml = ", ".join(f'"{project_dir}"' for project_dir in project_dirs)
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
        f"projects = [{projects_toml}]\n",
        encoding="utf-8",
    )
    return config_path


def test_main_when_run_as_subprocess_then_writes_each_project_context(tmp_path: Path) -> None:
    import subprocess

    config_path = _write_tmp_config(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-m", "formal.hermes_gen", "--config", str(config_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert completed.returncode == 0
    for project_dir in (tmp_path / "proj-a", tmp_path / "proj-b"):
        written_context = (project_dir / ".hermes.md").read_text(encoding="utf-8")
        assert KERNEL_TEXT in written_context
        assert BINDING_TEXT in written_context


def test_module_when_executed_as_main_then_writes_configured_projects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import runpy

    import formal.config

    config_path = _write_tmp_config(tmp_path)

    class _StubConfig:
        kernel_path = tmp_path / "kernel.md"
        standards_path = tmp_path / "standards.md"
        hermes_projects = (tmp_path / "proj-a", tmp_path / "proj-b")

    monkeypatch.setattr(formal.config, "load_config", lambda _path: _StubConfig())
    monkeypatch.setattr(sys, "argv", ["hermes_gen", "--config", str(config_path)])
    sys.modules.pop("formal.hermes_gen", None)
    runpy.run_module("formal.hermes_gen", run_name="__main__")
    for project_dir in (tmp_path / "proj-a", tmp_path / "proj-b"):
        assert (project_dir / ".hermes.md").exists()
