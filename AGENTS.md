# AGENTS.md — formal

The verification and validation pipeline for the deployed OpenCode artifacts.
This repo owns the checks that keep the kernel pair, agent bindings, skills,
and Hermes contexts provably current. It never amends the artifacts it
validates.

## Authority

The workspace kernel (`~/.opencode/AGENTS.md`) and the coding standards
(`~/.opencode/CODING_STANDARDS.md`) apply in full. This file adds only
project-specific constraints, commands, and traps. It restates no kernel or
standards rule: a rule has exactly one home, and restating it here would fork
it and drift on the next amendment. Kernel references use section numbers;
this repo's own cite-resolution check (V3) verifies they resolve.

## What formal is, and is not

- It validates four deployed surfaces: the kernel pair (`~/.opencode`), agent
  bindings (`~/.config/opencode/agents/`), skills
  (`~/.config/opencode/skills/`), and the generated Hermes project contexts
  (V7 freshness).
- It is read-only toward its targets: a validator run never mutates what it
  inspects, and a FAIL never triggers a "repair" from inside the validator.
  Repairs happen at the artifact's canonical home — kernel edits in
  `~/.opencode`, then regeneration and revalidation.
- It holds authority over the verified state of the artifacts, never over
  their content: it is a gate, not an editor and not a deployer.

## Architecture

- Configuration-driven: every path, exclusion list, and project list lives in
  `config.toml` (`[paths]`, `[exclusions]`, `[hermes]`); the provider model
  catalog lives in `model-catalog.json`. Zero magic values anywhere.
- Checks are pure functions returning exactly one of:
  - `Finding` — a detected defect; fails the run (exit 1);
  - `ExceptionRecord` — the check cannot run (missing catalog, unreadable
    source); recorded, exit 0.
    The distinction is contractual: degradation is always visible, and a
    missing source can never silently drop a check.
- CLI: `bin/validate <kernel|agents|skills|hermes|all>`; `bin/hermes-gen`
  regenerates the per-project `.hermes.md` contexts from their canonical
  sources. Every failure line names its check (e.g. `FAIL: [V7] ...`) so a
  failure is attributable from one line of output.
- Wiring: `~/.opencode` sets `core.hooksPath=.githooks`; its pre-commit execs
  `bin/validate kernel` and is fail-closed — the kernel pair never commits
  unvalidated. Remove with `git config --unset core.hooksPath`.

## Project checks beyond the kernel's

- Every check ships discriminating negative controls: mutated fixtures that
  must FAIL. A validator that passes vacuously is worse than one that fails
  wrongly — paid for twice here (a cite pattern that matched nothing and
  passed silently; a `grep -c` exit code masquerading as the validator's
  verdict).
- Full gate runs execute under `set -o pipefail`: a pipe to `tail` once
  masked a red run.

## Development discipline

- Python under `mypy --strict`. Environments via `uv venv`, installs via
  `VIRTUAL_ENV=$HOME/formal/.venv uv pip install ...` — uv silently resolves
  a pre-existing ambient venv when `VIRTUAL_ENV` is unset (observed
  2026-10-24).
- Test names follow `test_<fn>_when_<input>_then_<outcome>` with zero
  branches in test bodies. Coverage floor: 1.00, ratchet-style — raised as it
  climbs, never lowered. This repo validates kernels; its own suite must be
  complete.
- Gates: `pytest`, `ruff format --check`, `ruff check`, `mypy --strict` under
  `set -o pipefail` — zero errors, zero warnings, no suppressions, no scope
  narrowing.
- Commits: atomic — one discrete change per commit; the message documents
  what, why, and the observed evidence, RED-first evidence cited in the body
  (owner directive 2026-10-24).

## Lifecycle

- Edit a validated artifact at its canonical home → regenerate the contexts
  it feeds (`bin/hermes-gen`) → `bin/validate --all` → commit.
- After any kit-master sync (`~/Dropbox/opencode`): the V6 drift guard FAILs
  until the deployed pair is reconciled with the master; then regenerate and
  revalidate.
- Phase 2 (TLA+ `Kernel.tla` re-creation + TLC model checking) is deferred
  pending owner word — capability limitation recorded, not silently dropped.

## Amendment

Changes to this policy pass the kernel Rule Admission Test (§14) with defect
evidence before landing. Changes to validated artifacts follow the lifecycle
above and re-run the full gates before commit.
