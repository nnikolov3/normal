# AGENTS.md — formal

The workspace program (`~/.opencode/AGENTS.md`) applies in full. formal bindings on top:

- Purpose: the verification and validation pipeline for the deployed OpenCode artifacts — the kernel pair (`~/.opencode/AGENTS.md`, `~/.opencode/CODING_STANDARDS.md`), agent bindings (`~/.config/opencode/agents/`), and skills (`~/.config/opencode/skills/`). Validators are strictly read-only: a FAIL never mutates its target.
- Language and engine: Python (`M_Py`) under `mypy --strict`; environments via `uv venv`, installs via `VIRTUAL_ENV=~/formal/.venv uv pip install ...` (never `pip`, never a system interpreter).
- RED-first is mandatory, doubly so here: every check lands with its discriminating negative control first — the red run is observed and cited before the implementation exists. Test names follow `test_<fn>_when_<input>_then_<outcome>`; zero branches in test bodies.
- Coverage floor: 1.00, ratchet-style (raised as coverage climbs, never lowered). This repo validates kernels; its own suite must be complete.
- Gates: `pytest`, `ruff format --check`, `ruff check`, `mypy --strict` — zero errors, zero warnings, no suppressions, no scope narrowing, run under `set -o pipefail`.
- Commands: `bin/validate --all` (everything), `bin/validate kernel|agents|skills` (one target). Exit 0 = pass with recorded exceptions; nonzero = at least one FAIL.
- Wiring: `~/.opencode/.githooks/pre-commit` execs `bin/validate kernel` — the kernel pair never commits unvalidated. Kit-master drift (`V6`) fails loudly on any divergence between `~/.opencode` and `~/Dropbox/opencode`.
- Everything is configuration-driven: exclusion lists, store paths, and thresholds live in config, zero magic values.
- Phase 2 (TLA+ `Kernel.tla` re-creation + TLC model checking) is deferred pending owner word — capability limitation recorded, not silently dropped.
