"""Tests for the validation entry point: dispatch, exit codes, findings surfaced."""

from formal.cli import run_validation
from formal.config import load_config


def write_skill(root, skill_name, frontmatter, body="work\n"):
    directory = root / skill_name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
    return directory / "SKILL.md"


def write_config(tmp_path, skills_root, forbidden):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[paths]
skills_root = "{skills_root}"
agents_root = "{tmp_path / "agents"}"
kernel_path = "{tmp_path / "kernel" / "AGENTS.md"}"
standards_path = "{tmp_path / "kernel" / "CODING_STANDARDS.md"}"
kit_kernel_path = "{tmp_path / "kit" / "AGENTS.md"}"
kit_standards_path = "{tmp_path / "kit" / "CODING_STANDARDS.md"}"

[exclusions]
terms = {forbidden}
""",
        encoding="utf-8",
    )
    return config_path


def test_run_validation_when_skills_clean_then_exit_zero(tmp_path):
    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    exit_code = run_validation(load_config(config_path), targets=["skills"])
    assert exit_code == 0


def test_run_validation_when_excluded_skill_present_then_exit_nonzero_and_finding_named(tmp_path):
    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    write_skill(tmp_path / "skills", "converix", 'name: Converix\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", '["converix"]')
    exit_code = run_validation(load_config(config_path), targets=["skills"])
    assert exit_code == 1


def test_run_validation_when_skill_frontmatter_incomplete_then_exit_nonzero(tmp_path):
    write_skill(tmp_path / "skills", "coding", "name: Coding\n")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    exit_code = run_validation(load_config(config_path), targets=["skills"])
    assert exit_code == 1


def test_run_validation_when_agents_clean_then_exit_zero(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "n.md").write_text(
        "---\ndescription: >\n  Agent\nmode: all\n---\nbody\n", encoding="utf-8"
    )
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 0


def test_run_validation_when_agent_pin_absent_from_catalog_then_exit_nonzero(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "n.md").write_text(
        "---\ndescription: Agent\nmode: all\nmodel: ghost/model-x\n---\nbody\n", encoding="utf-8"
    )
    (tmp_path / "model-catalog.json").write_text(
        '{"providers": [{"id": "synthetic", "models": [{"id": "synthetic/a"}]}]}', encoding="utf-8"
    )
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 1


def test_run_validation_when_catalog_malformed_then_exception_and_exit_zero(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "n.md").write_text(
        "---\ndescription: Agent\nmode: all\nmodel: synthetic/a\n---\nbody\n", encoding="utf-8"
    )
    (tmp_path / "model-catalog.json").write_text("{broken", encoding="utf-8")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 0


def test_run_validation_when_catalog_shape_invalid_then_exception_and_exit_zero(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "n.md").write_text(
        "---\ndescription: Agent\nmode: all\nmodel: synthetic/a\n---\nbody\n", encoding="utf-8"
    )
    (tmp_path / "model-catalog.json").write_text('{"providers": [7]}', encoding="utf-8")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 0


def test_run_validation_when_kernel_diverges_from_kit_then_exit_nonzero(tmp_path):
    (tmp_path / "kernel").mkdir()
    (tmp_path / "kit").mkdir()
    (tmp_path / "kernel" / "AGENTS.md").write_text("deployed kernel\n", encoding="utf-8")
    (tmp_path / "kernel" / "CODING_STANDARDS.md").write_text(
        "deployed standards\n", encoding="utf-8"
    )
    (tmp_path / "kit" / "AGENTS.md").write_text("master kernel\n", encoding="utf-8")
    (tmp_path / "kit" / "CODING_STANDARDS.md").write_text("master standards\n", encoding="utf-8")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["kernel"]) == 1


def test_run_validation_when_kernel_matches_kit_then_exit_zero(tmp_path):
    (tmp_path / "kernel").mkdir()
    (tmp_path / "kit").mkdir()
    for name in ("AGENTS.md", "CODING_STANDARDS.md"):
        (tmp_path / "kernel" / name).write_text("same bytes\n", encoding="utf-8")
        (tmp_path / "kit" / name).write_text("same bytes\n", encoding="utf-8")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["kernel"]) == 0


def test_run_validation_when_kernel_files_absent_then_exception_and_exit_zero(tmp_path):
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["kernel"]) == 0


def test_run_validation_when_skills_root_absent_then_exception_and_exit_zero(tmp_path):
    config_path = write_config(tmp_path, tmp_path / "absent-skills", "[]")
    assert run_validation(load_config(config_path), targets=["skills"]) == 0


def test_run_validation_when_agents_root_absent_then_exception_and_exit_zero(tmp_path):
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 0


def test_run_validation_when_skill_frontmatter_broken_then_exit_nonzero(tmp_path):
    (tmp_path / "skills" / "coding").mkdir(parents=True)
    (tmp_path / "skills" / "coding" / "SKILL.md").write_text("no delimiters\n", encoding="utf-8")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["skills"]) == 1


def test_main_when_target_given_then_returns_exit_code(tmp_path):
    from formal.cli import main

    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert main(["--config", str(config_path), "skills"]) == 0


def test_main_when_all_target_then_expands_to_three_targets(tmp_path):
    from formal.cli import main

    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert main(["--config", str(config_path), "all"]) == 0


def test_main_when_no_targets_then_defaults_to_all(tmp_path):
    from formal.cli import main

    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert main(["--config", str(config_path)]) == 0


def test_run_validation_when_agent_broken_and_agent_citing_kernel_then_exit_nonzero(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "broken.md").write_text("no delimiters\n", encoding="utf-8")
    (tmp_path / "agents" / "citing.md").write_text(
        "---\ndescription: Agent\nmode: all\n---\nsee `AGENTS.md` 4\n", encoding="utf-8"
    )
    (tmp_path / "kernel").mkdir()
    (tmp_path / "kernel" / "AGENTS.md").write_text("## 4. Task State\n\nbody\n", encoding="utf-8")
    (tmp_path / "kernel" / "CODING_STANDARDS.md").write_text(
        "## 2.1 Go (`M_Go`)\n\nbody\n", encoding="utf-8"
    )
    (tmp_path / "kit").mkdir()
    (tmp_path / "kit" / "AGENTS.md").write_text("## 4. Task State\n\nbody\n", encoding="utf-8")
    (tmp_path / "kit" / "CODING_STANDARDS.md").write_text(
        "## 2.1 Go (`M_Go`)\n\nbody\n", encoding="utf-8"
    )
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 1


def test_run_validation_when_catalog_providers_not_list_then_exception_and_exit_zero(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "n.md").write_text(
        "---\ndescription: Agent\nmode: all\nmodel: synthetic/a\n---\nbody\n", encoding="utf-8"
    )
    (tmp_path / "model-catalog.json").write_text('{"providers": 7}', encoding="utf-8")
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert run_validation(load_config(config_path), targets=["agents"]) == 0


def test_module_entry_when_invoked_as_script_then_exits_zero(tmp_path):
    import subprocess
    import sys

    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    venv_python = tmp_path.parents[0] / ".venv" / "bin" / "python"
    python_path = str(venv_python) if venv_python.is_file() else sys.executable
    completed = subprocess.run(
        [python_path, "-m", "formal.cli", "--config", str(config_path), "skills"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_module_guard_when_executed_as_main_then_exits_zero(tmp_path, monkeypatch):
    import runpy
    import sys

    import pytest

    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    monkeypatch.setattr("sys.argv", ["validate", "--config", str(config_path), "skills"])
    monkeypatch.delitem(sys.modules, "formal.cli", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("formal.cli", run_name="__main__")
    assert exit_info.value.code == 0


def test_main_when_all_flag_then_validates_every_target(tmp_path):
    from formal.cli import main

    write_skill(tmp_path / "skills", "coding", 'name: Coding\ndescription: "work"\n')
    config_path = write_config(tmp_path, tmp_path / "skills", "[]")
    assert main(["--config", str(config_path), "--all"]) == 0
