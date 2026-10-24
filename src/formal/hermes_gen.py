"""Generate Hermes project-context files (.hermes.md) from canonical sources.

The generated file is a build artifact, never a knowledge home: it concatenates
the engineering kernel, the coding standards, and the project binding verbatim
so Hermes (one project context file per session) sees all three. The ~/formal
hermes freshness check fails when the file drifts from regeneration.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

CONTEXT_FILE_NAME = ".hermes.md"

_HEADER_TEMPLATE = """\
# Hermes Project Context — {project_name}

Generated file — do not edit by hand.
Sources, in the load order below: this directory's AGENTS.md (project binding),
~/.opencode/AGENTS.md (engineering kernel), and ~/.opencode/CODING_STANDARDS.md
(coding standards). Regenerate with `~/formal/bin/hermes-gen`; the ~/formal
validator fails when this file drifts from regeneration. Hermes loads one
project context file per session, so this file carries all three documents in
place of the directory's AGENTS.md.
"""


def load_hermes_projects(document: dict[str, Any]) -> list[Path]:
    """Project directories configured under [hermes] projects, ~-expanded."""
    section = document.get("hermes") or {}
    entries = section.get("projects") or []
    return [Path(str(entry)).expanduser() for entry in entries]


def build_project_context(
    project_name: str,
    binding_text: str,
    kernel_text: str,
    standards_text: str,
) -> str:
    """Concatenate kernel, standards, and binding verbatim under a provenance header."""
    parts = [_HEADER_TEMPLATE.format(project_name=project_name)]
    for title, document_text in (
        ("Engineering kernel", kernel_text),
        ("Coding standards", standards_text),
        ("Project binding", binding_text),
    ):
        parts.append(f"\n---\n\n## {title}\n\n{document_text}")
    return "".join(parts)


def build_project_context_from_paths(
    project_name: str,
    binding_path: Path,
    kernel_path: Path,
    standards_path: Path,
) -> str:
    """Read the three sources and build the context; a missing source raises FileNotFoundError."""
    return build_project_context(
        project_name=project_name,
        binding_text=binding_path.read_text(encoding="utf-8"),
        kernel_text=kernel_path.read_text(encoding="utf-8"),
        standards_text=standards_path.read_text(encoding="utf-8"),
    )


def write_hermes_context(project_dir: Path, context_text: str) -> Path:
    """Write the context file at the project root and return its path."""
    context_path = project_dir / CONTEXT_FILE_NAME
    context_path.write_text(context_text, encoding="utf-8")
    return context_path


def main() -> None:
    """Generate .hermes.md for every configured project directory."""
    from formal.config import load_config

    argument_parser = argparse.ArgumentParser(description=main.__doc__)
    argument_parser.add_argument("--config", type=Path, required=True)
    arguments = argument_parser.parse_args()
    formal_config = load_config(arguments.config)
    for project_dir in formal_config.hermes_projects:
        context = build_project_context_from_paths(
            project_name=project_dir.name,
            binding_path=project_dir / "AGENTS.md",
            kernel_path=formal_config.kernel_path,
            standards_path=formal_config.standards_path,
        )
        written_path = write_hermes_context(project_dir, context)
        print(f"wrote {written_path} ({len(context)} characters)")


if __name__ == "__main__":
    main()
