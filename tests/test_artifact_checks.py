"""Tests for artifact checks: frontmatter completeness, uniqueness, pins, remnants."""

from formal.checks import (
    check_forbidden_remnants,
    check_frontmatter_complete,
    check_model_pins,
    check_name_uniqueness,
    check_secret_values,
)
from formal.records import ExceptionRecord, Finding


def test_check_frontmatter_complete_when_skill_has_required_fields_then_no_finding():
    findings = check_frontmatter_complete(
        "skill", "/tmp/x/SKILL.md", {"name": "x", "description": "d"}
    )
    assert findings == []


def test_check_frontmatter_complete_when_skill_description_missing_then_finding_names_field():
    findings = check_frontmatter_complete("skill", "/tmp/x/SKILL.md", {"name": "x"})
    assert len(findings) == 1
    assert isinstance(findings[0], Finding)
    assert "description" in findings[0].detail


def test_check_frontmatter_complete_when_agent_mode_missing_then_finding_names_field():
    findings = check_frontmatter_complete("agent", "/tmp/agents/n.md", {"description": "d"})
    assert len(findings) == 1
    assert "mode" in findings[0].detail


def test_check_name_uniqueness_when_two_skills_share_name_then_finding_names_both():
    entries = [("/a/SKILL.md", "alpha"), ("/b/SKILL.md", "alpha")]
    findings = check_name_uniqueness(entries)
    assert len(findings) == 1
    assert "/a/SKILL.md" in findings[0].detail and "/b/SKILL.md" in findings[0].detail


def test_check_name_uniqueness_when_names_distinct_then_no_finding():
    entries = [("/a/SKILL.md", "alpha"), ("/b/SKILL.md", "beta")]
    assert check_name_uniqueness(entries) == []


def test_check_model_pins_when_pin_absent_from_catalog_then_finding():
    findings = check_model_pins(
        [("/tmp/agents/n.md", "CodeCompanionV2/claude-sonnet-5-5")],
        {"synthetic/hf:zai-org/GLM-5.3-Flash"},
    )
    assert len(findings) == 1
    assert "CodeCompanionV2/claude-sonnet-5-5" in findings[0].detail


def test_check_model_pins_when_pin_in_catalog_then_no_finding():
    findings = check_model_pins(
        [("/tmp/agents/n.md", "synthetic/hf:zai-org/GLM-5.3-Flash")],
        {"synthetic/hf:zai-org/GLM-5.3-Flash"},
    )
    assert findings == []


def test_check_model_pins_when_field_absent_then_no_finding():
    findings = check_model_pins([("/tmp/agents/n.md", None)], {"anything"})
    assert findings == []


def test_check_model_pins_when_catalog_unavailable_then_exception_recorded():
    outcomes = check_model_pins([("/tmp/agents/n.md", "some-model")], None)
    assert len(outcomes) == 1
    assert isinstance(outcomes[0], ExceptionRecord)


def test_check_forbidden_remnants_when_excluded_skill_directory_present_then_finding():
    findings = check_forbidden_remnants(
        ["/tmp/skills/converix/SKILL.md", "/tmp/skills/coding/SKILL.md"],
        ["converix"],
    )
    assert len(findings) == 1
    assert "converix" in findings[0].detail


def test_check_forbidden_remnants_when_clean_then_no_finding():
    findings = check_forbidden_remnants(["/tmp/skills/coding/SKILL.md"], ["converix"])
    assert findings == []


def test_check_secret_values_when_credential_assignment_then_finding():
    findings = check_secret_values([("/tmp/a.md", "api_key = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234'")])
    assert len(findings) == 1


def test_check_secret_values_when_permission_glob_mentions_env_then_no_finding():
    findings = check_secret_values([("/tmp/a.md", 'resource: "*.env"\neffect: deny')])
    assert findings == []
