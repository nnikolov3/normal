"""Tests for kernel checks: citations, bijection, transitions, M_code, lemmas, drift."""

from formal.checks import (
    extract_heading_numbers,
    measure_kit_master_drift,
    resolve_citations,
    verify_law_trap_bijection,
    verify_lemma_stratification,
    verify_m_code_totality,
    verify_transition_targets,
)
from formal.records import ExceptionRecord

KERNEL_SAMPLE = """## 2. Hard Laws

| ID  | Law | Violation (trap) |
| --- | --- | --- |
| H1 | law one | `FABRICATION` |
| H2 | law two | `UNOBSERVED_EXECUTION` |

### 0.1 Kernel tuple

| law | trap |
| --- | --- |
| `H1` | `FABRICATION` |
| `H2` | `UNOBSERVED_EXECUTION` |

## 6. Master State Machine

| State | Work | Rules |
| --- | --- | --- |
| `INTAKE` | intake work | 1. guard -> `CHALLENGE` |
| `CHALLENGE` | challenge work | 1. guard -> `INTAKE` |
| `DELIVER` | report | terminal |

## 10. Trap Architecture

| Trap | Law | Raised when | Resume in |
| --- | --- | --- | --- |
| `FABRICATION` | H1 | invented | raising state |
| `UNOBSERVED_EXECUTION` | H2 | unexecuted | raising state |
"""

STANDARDS_SAMPLE = """```text
SYSTEM_TUPLE := M_code = (S_c, Registers_c, Operations_c, Doctrines_c, Lemmas_c, delta_c, s0_c, F_c)
  S_c  := {SPECIFY, CERTIFIED}
  s0_c := SPECIFY
  F_c  := {CERTIFIED}
```

| Current State `PC_c` | Rule `#` | Guard | Action | Next State `PC_c'` |
|---|---|---|---|---|
| `SPECIFY` | `1` | contract defined | bind signature | `CERTIFIED` |
| `SPECIFY` | `2` | otherwise | hold | `SPECIFY` |
| `CERTIFIED` | - | terminal | - | - |
"""

LEMMA_SAMPLE_CLEAN = """| Lemma | Level | Statement | Proof |
|---|---|---|---|
| `LC1` | `1` | first lemma | direct argument. |
| `LC2` | `1` | second lemma | follows from the earlier lemma; cites LC1. |
| `MLC1` | `2` | meta lemma | cites LC1, LC2. |
"""

LEMMA_SAMPLE_BAD = """| Lemma | Level | Statement | Proof |
|---|---|---|---|
| `LC1` | `1` | first lemma | cites LC2. |
| `LC2` | `1` | second lemma | direct argument. |
| `MLC1` | `2` | meta lemma | cites LC1. |
"""


def test_verify_law_trap_bijection_when_tables_agree_then_no_finding():
    assert verify_law_trap_bijection(KERNEL_SAMPLE) == []


def test_verify_law_trap_bijection_when_trap_table_claims_two_laws_for_one_trap_then_finding():
    mutated = KERNEL_SAMPLE.replace(
        "| `UNOBSERVED_EXECUTION` | H2 |", "| `UNOBSERVED_EXECUTION` | H1 |"
    )
    findings = verify_law_trap_bijection(mutated)
    assert len(findings) >= 1


def test_verify_law_trap_bijection_when_binding_table_disagrees_then_finding():
    mutated = KERNEL_SAMPLE.replace("| `H1` | `FABRICATION` |", "| `H1` | `UNOBSERVED_EXECUTION` |")
    findings = verify_law_trap_bijection(mutated)
    assert len(findings) >= 1


def test_verify_transition_targets_when_every_target_declared_then_no_finding():
    assert verify_transition_targets(KERNEL_SAMPLE) == []


def test_verify_transition_targets_when_target_undeclared_then_finding_names_target():
    mutated = KERNEL_SAMPLE.replace("1. guard -> `CHALLENGE`", "1. guard -> `ORBIT`")
    findings = verify_transition_targets(mutated)
    assert len(findings) == 1
    assert "ORBIT" in findings[0].detail


def test_verify_m_code_totality_when_every_declared_state_has_rules_then_no_finding():
    assert verify_m_code_totality(STANDARDS_SAMPLE) == []


def test_verify_m_code_totality_when_declared_state_lacks_rules_then_finding():
    mutated = STANDARDS_SAMPLE.replace(
        "  S_c  := {SPECIFY, CERTIFIED}", "  S_c  := {SPECIFY, CERTIFIED, REJECTED}"
    )
    findings = verify_m_code_totality(mutated)
    assert len(findings) == 1
    assert "REJECTED" in findings[0].detail


def test_verify_m_code_totality_when_target_column_names_declared_state_then_reachable():
    mutated = STANDARDS_SAMPLE.replace(
        "| `SPECIFY` | `1` | contract defined | bind signature | `CERTIFIED` |", ""
    )
    findings = verify_m_code_totality(mutated)
    assert len(findings) == 1
    assert "unreachable" in findings[0].detail


def test_verify_lemma_stratification_when_same_level_earlier_cited_then_no_finding():
    assert verify_lemma_stratification(LEMMA_SAMPLE_CLEAN) == []


def test_verify_lemma_stratification_when_later_same_level_cited_then_finding():
    findings = verify_lemma_stratification(LEMMA_SAMPLE_BAD)
    assert len(findings) == 1
    assert "LC1" in findings[0].detail and "LC2" in findings[0].detail


def test_resolve_citations_when_all_sections_exist_then_no_finding():
    kernel_text = "## 4. Task State\n\nbody\n"
    standards_text = "## 2.1 Go (`M_Go`)\n\nbody\n"
    findings = resolve_citations(
        ("/tmp/agent.md", "see AGENTS.md 4 and CODING_STANDARDS.md 2.1"),
        extract_heading_numbers(kernel_text),
        extract_heading_numbers(standards_text),
    )
    assert findings == []


def test_resolve_citations_when_section_missing_then_finding_names_reference():
    kernel_text = "## 4. Task State\n\nbody\n"
    findings = resolve_citations(
        ("/tmp/agent.md", "see AGENTS.md 99"),
        extract_heading_numbers(kernel_text),
        set(),
    )
    assert len(findings) == 1
    assert "99" in findings[0].detail


def test_measure_kit_master_drift_when_pair_identical_then_no_finding(tmp_path):
    deployed = tmp_path / "deployed"
    master = tmp_path / "master"
    deployed.mkdir()
    master.mkdir()
    (deployed / "AGENTS.md").write_text("identical", encoding="utf-8")
    (master / "AGENTS.md").write_text("identical", encoding="utf-8")
    findings = measure_kit_master_drift([(deployed / "AGENTS.md", master / "AGENTS.md")])
    assert findings == []


def test_measure_kit_master_drift_when_pair_diverges_then_finding(tmp_path):
    deployed = tmp_path / "deployed"
    master = tmp_path / "master"
    deployed.mkdir()
    master.mkdir()
    (deployed / "AGENTS.md").write_text("changed", encoding="utf-8")
    (master / "AGENTS.md").write_text("original", encoding="utf-8")
    findings = measure_kit_master_drift([(deployed / "AGENTS.md", master / "AGENTS.md")])
    assert len(findings) == 1


def test_measure_kit_master_drift_when_master_absent_then_exception_recorded(tmp_path):
    findings = measure_kit_master_drift([(tmp_path / "deployed.md", tmp_path / "absent.md")])
    assert len(findings) == 1
    assert isinstance(findings[0], ExceptionRecord)
