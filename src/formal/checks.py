"""Validation checks over skills, agents, and the kernel pair."""

from __future__ import annotations

import re
from pathlib import Path

from formal.records import ExceptionRecord, Finding

_REQUIRED_FRONTMATTER: dict[str, tuple[str, ...]] = {
    "skill": ("name", "description"),
    "agent": ("description", "mode"),
}

_SECRET_PATTERNS = (
    re.compile(r"(api_?key|secret|token|password)\s*=\s*['\"][^'\"]{12,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)

_HEADING_PATTERN = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)*)\.?\s")
_CITATION_PATTERN = re.compile(r"(AGENTS\.md|CODING_STANDARDS\.md)`?\s*§?\s*(\d+(?:\.\d+)*)")
_LAW_ROW_PATTERN = re.compile(r"^\|\s*H(\d+)\s*\|.*?\|\s*`([A-Z_]+)`\s*\|\s*$")
_BINDING_ROW_PATTERN = re.compile(r"^\|\s*`?H(\d+)`?\s*\|\s*`([A-Z_]+)`\s*\|\s*$")
_TRAP_ROW_PATTERN = re.compile(r"^\|\s*`([A-Z_]+)`\s*\|\s*H(\d+)\s*\|")
_STATE_ROW_PATTERN = re.compile(r"^\|\s*`([A-Z_]+)`\s*\|")
_TRANSITION_PATTERN = re.compile(r"->\s*`([A-Z_]+)`")
_STATE_SET_PATTERN = re.compile(r"S_c\s*:=\s*\{([^}]*)\}")
_START_STATE_PATTERN = re.compile(r"s0_c\s*:=\s*([A-Z_]+)")
_M_CODE_ROW_PATTERN = re.compile(r"^\|\s*`([A-Z_]+)`\s*\|")
_LEMMA_ROW_PATTERN = re.compile(r"^\|\s*`?([A-Za-z]+\d+)`?\s*\|\s*`?(\d+)`?\s*\|")
_CITES_PATTERN = re.compile(r"[Cc]ites?\s+([^|]+)")


def extract_heading_numbers(text: str) -> set[str]:
    numbers: set[str] = set()
    for line in text.splitlines():
        match = _HEADING_PATTERN.match(line)
        if match is not None:
            numbers.add(match.group(1))
    return numbers


def resolve_citations(
    source: tuple[str, str],
    kernel_numbers: set[str],
    standards_numbers: set[str],
) -> list[Finding]:
    path, text = source
    findings: list[Finding] = []
    for match in _CITATION_PATTERN.finditer(text):
        file_name = match.group(1)
        section = match.group(2)
        known_numbers = kernel_numbers if file_name == "AGENTS.md" else standards_numbers
        if section not in known_numbers:
            findings.append(Finding("V3", path, f"citation {file_name} {section} does not resolve"))
    return findings


def check_frontmatter_complete(
    target_type: str,
    path: str,
    fields: dict[str, object],
) -> list[Finding]:
    required_fields = _REQUIRED_FRONTMATTER[target_type]
    findings: list[Finding] = []
    for field_name in required_fields:
        if fields.get(field_name) in (None, ""):
            findings.append(
                Finding("V1", path, f"frontmatter field '{field_name}' required in {target_type}")
            )
    return findings


def check_name_uniqueness(entries: list[tuple[str, str]]) -> list[Finding]:
    paths_by_name: dict[str, list[str]] = {}
    for path, name in entries:
        paths_by_name.setdefault(name, []).append(path)
    findings: list[Finding] = []
    for name, paths in paths_by_name.items():
        if len(paths) > 1:
            detail = f"name '{name}' claimed by {', '.join(paths)}"
            findings.append(Finding("V1", paths[0], detail))
    return findings


def check_model_pins(
    entries: list[tuple[str, str | None]],
    catalog: set[str] | None,
) -> list[Finding | ExceptionRecord]:
    outcomes: list[Finding | ExceptionRecord] = []
    for path, model_pin in entries:
        if model_pin is None:
            continue
        if catalog is None:
            outcomes.append(
                ExceptionRecord("V2", path, "model catalog unavailable; pin not verified")
            )
        elif model_pin not in catalog:
            detail = f"model pin '{model_pin}' absent from provider catalog"
            outcomes.append(Finding("V2", path, detail))
    return outcomes


def check_forbidden_remnants(paths: list[str], terms: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        for term in terms:
            if term in path:
                findings.append(Finding("V5", path, f"forbidden term '{term}' present"))
    return findings


def check_secret_values(entries: list[tuple[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, content in entries:
        for pattern in _SECRET_PATTERNS:
            if pattern.search(content) is not None:
                findings.append(Finding("V5", path, f"secret pattern '{pattern.pattern}' matched"))
    return findings


def verify_law_trap_bijection(kernel_text: str) -> list[Finding]:
    law_to_trap: dict[str, str] = {}
    binding_to_trap: dict[str, str] = {}
    trap_to_law: dict[str, str] = {}
    for line in kernel_text.splitlines():
        law_match = _LAW_ROW_PATTERN.match(line)
        if law_match is not None:
            law_to_trap[f"H{law_match.group(1)}"] = law_match.group(2)
            continue
        binding_match = _BINDING_ROW_PATTERN.match(line)
        if binding_match is not None:
            binding_to_trap[f"H{binding_match.group(1)}"] = binding_match.group(2)
            continue
        trap_match = _TRAP_ROW_PATTERN.match(line)
        if trap_match is not None:
            trap_to_law[trap_match.group(1)] = f"H{trap_match.group(2)}"
    findings: list[Finding] = []
    for law_id, trap_name in law_to_trap.items():
        binding_trap = binding_to_trap.get(law_id)
        if binding_trap is not None and binding_trap != trap_name:
            detail = f"{law_id} binds {trap_name} in the law table but {binding_trap} in the tuple"
            findings.append(Finding("V4", "kernel AGENTS.md", detail))
        claimed_traps = [name for name, claimed_law in trap_to_law.items() if claimed_law == law_id]
        for claimed_trap in claimed_traps:
            if claimed_trap != trap_name:
                detail = (
                    f"trap table maps {claimed_trap} to {law_id} but the law table maps {trap_name}"
                )
                findings.append(Finding("V4", "kernel AGENTS.md", detail))
    claimed_laws = list(trap_to_law.values())
    if len(claimed_laws) != len(set(claimed_laws)):
        detail = f"two traps claim one law: {sorted(claimed_laws)}"
        findings.append(Finding("V4", "kernel AGENTS.md", detail))
    return findings


def verify_transition_targets(kernel_text: str) -> list[Finding]:
    declared_states: set[str] = set()
    for line in kernel_text.splitlines():
        state_match = _STATE_ROW_PATTERN.match(line)
        if state_match is not None:
            declared_states.add(state_match.group(1))
    findings: list[Finding] = []
    for line in kernel_text.splitlines():
        for transition_match in _TRANSITION_PATTERN.finditer(line):
            target_state = transition_match.group(1)
            if target_state not in declared_states:
                detail = f"transition target {target_state} is not a declared state"
                findings.append(Finding("V4", "kernel AGENTS.md", detail))
    return findings


def verify_m_code_totality(standards_text: str) -> list[Finding]:
    findings: list[Finding] = []
    declared_states: set[str] = set()
    state_match = _STATE_SET_PATTERN.search(standards_text)
    if state_match is not None:
        declared_states = {name.strip() for name in state_match.group(1).split(",")}
    row_states: set[str] = set()
    edges: dict[str, set[str]] = {}
    backticked_states = re.compile(r"`([A-Z_]+)`")
    for line in standards_text.splitlines():
        row_match = _M_CODE_ROW_PATTERN.match(line)
        if row_match is None:
            continue
        row_states.add(row_match.group(1))
        tokens = backticked_states.findall(line)
        if len(tokens) >= 2:
            edges.setdefault(row_match.group(1), set()).add(tokens[-1])
    for missing_state in sorted(declared_states - row_states):
        detail = f"state {missing_state} declared in S_c but absent from delta_c"
        findings.append(Finding("V4", "kernel CODING_STANDARDS.md", detail))
    start_match = _START_STATE_PATTERN.search(standards_text)
    if start_match is not None:
        reachable = _reachable_states(edges, start_match.group(1))
        if "CERTIFIED" in declared_states and "CERTIFIED" not in reachable:
            detail = "CERTIFIED terminal is unreachable from s0"
            findings.append(Finding("V4", "kernel CODING_STANDARDS.md", detail))
    return findings


def _reachable_states(edges: dict[str, set[str]], start_state: str) -> set[str]:
    reachable = {start_state}
    frontier = [start_state]
    while frontier:
        current_state = frontier.pop()
        for next_state in edges.get(current_state, set()):
            if next_state not in reachable:
                reachable.add(next_state)
                frontier.append(next_state)
    return reachable


def verify_lemma_stratification(kernel_text: str, standards_text: str = "") -> list[Finding]:
    lemma_rows: list[tuple[str, int, str, str]] = []
    for file_name, text in (("kernel", kernel_text), ("standards", standards_text)):
        for line in text.splitlines():
            row_match = _LEMMA_ROW_PATTERN.match(line)
            if row_match is not None:
                lemma_rows.append((row_match.group(1), int(row_match.group(2)), file_name, line))
    identifier_rows = {row[0]: index for index, row in enumerate(lemma_rows)}
    findings: list[Finding] = []
    for index, (lemma_id, level, file_name, line) in enumerate(lemma_rows):
        cites_match = _CITES_PATTERN.search(line)
        if cites_match is None:
            continue
        for cited_token in re.split(r"[,\s]+", cites_match.group(1)):
            cited_id = cited_token.strip("`.")
            cited_index = identifier_rows.get(cited_id)
            if cited_id == lemma_id or cited_index is None:
                continue
            cited_level = lemma_rows[cited_index][1]
            cited_file = lemma_rows[cited_index][2]
            violates_level = cited_level > level
            violates_order = (
                cited_file == file_name and cited_level == level and cited_index > index
            )
            if violates_level or violates_order:
                detail = f"{lemma_id} cites {cited_id} at level {cited_level} (level {level})"
                findings.append(Finding("V4", f"{file_name} lemma table", detail))
    return findings


def measure_kit_master_drift(pairs: list[tuple[Path, Path]]) -> list[Finding | ExceptionRecord]:
    outcomes: list[Finding | ExceptionRecord] = []
    for deployed_path, master_path in pairs:
        master_text = _read_bytes(master_path)
        if master_text is None:
            detail = f"kit master absent: {master_path}"
            outcomes.append(ExceptionRecord("V6", str(deployed_path), detail))
        elif _read_bytes(deployed_path) != master_text:
            detail = f"deployed pair diverges from kit master: {master_path}"
            outcomes.append(Finding("V6", str(deployed_path), detail))
    return outcomes


def _read_bytes(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes()
