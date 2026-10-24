"""Parser for the machine-clean frontmatter subset used by skills and agents.

Supports: scalar fields, double-quoted scalars, folded (``>``) and literal
(``|``) block scalars, plain lists, and lists of flat string maps.
"""

from __future__ import annotations

from dataclasses import dataclass

_BLOCK_MARKERS = {">", "|", ">-", "|-"}


class FrontmatterError(ValueError):
    """Raised when a frontmatter block is structurally invalid."""


@dataclass(frozen=True)
class ParsedFrontmatter:
    fields: dict[str, object]
    body: str


def parse_frontmatter(document: str) -> ParsedFrontmatter:
    lines = document.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("missing opening '---' delimiter")
    closing_index = _find_closing_delimiter(lines)
    fields = _parse_fields(lines[1:closing_index])
    return ParsedFrontmatter(fields, "\n".join(lines[closing_index + 1 :]))


def _find_closing_delimiter(lines: list[str]) -> int:
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    raise FrontmatterError("missing closing '---' delimiter")


def _parse_fields(section_lines: list[str]) -> dict[str, object]:
    fields: dict[str, object] = {}
    index = 0
    while index < len(section_lines):
        header_key, header_value, header_indent = _parse_field_header(section_lines[index])
        if header_value in _BLOCK_MARKERS:
            block_value, index = _parse_block_scalar(
                section_lines, index + 1, header_indent, folded=header_value.startswith(">")
            )
            fields[header_key] = block_value
        elif header_value == "":
            nested_value, index = _parse_nested(section_lines, index + 1, header_indent)
            fields[header_key] = nested_value
        else:
            fields[header_key] = _clean_value(header_value)
            index += 1
    return fields


def _parse_field_header(line: str) -> tuple[str, str, int]:
    if line.startswith((" ", "\t", "-")):
        raise FrontmatterError(f"unsupported frontmatter line: {line!r}")
    stripped = line.strip()
    separator = stripped.find(":")
    if separator <= 0:
        raise FrontmatterError(f"unsupported frontmatter line: {line!r}")
    key = stripped[:separator].strip()
    value = stripped[separator + 1 :].strip()
    return key, value, _indent_width(line)


def _parse_nested(section_lines: list[str], index: int, parent_indent: int) -> tuple[object, int]:
    nested: list[str] = []
    while index < len(section_lines):
        line = section_lines[index]
        if not line.strip():
            index += 1
            continue
        if _indent_width(line) <= parent_indent:
            break
        nested.append(line)
        index += 1
    if not nested:
        return [], index
    if nested[0].lstrip().startswith("- "):
        return _parse_list_items(nested), index
    return _parse_scalar_map(nested), index


def _parse_list_items(nested_lines: list[str]) -> list[object]:
    items: list[object] = []
    item_indent = _indent_width(nested_lines[0])
    index = 0
    while index < len(nested_lines):
        line = nested_lines[index]
        if _indent_width(line) != item_indent:
            index += 1
            continue
        content = line.strip()[2:]
        if ":" in content:
            item, index = _parse_map_item(nested_lines, index, item_indent)
            items.append(item)
        else:
            items.append(_clean_value(content))
            index += 1
    return items


def _parse_map_item(
    nested_lines: list[str], index: int, item_indent: int
) -> tuple[dict[str, str], int]:
    item_key, item_value = _split_key_value(nested_lines[index].strip()[2:])
    item: dict[str, str] = {item_key: _clean_value(item_value)}
    index += 1
    while index < len(nested_lines):
        line = nested_lines[index]
        if _indent_width(line) <= item_indent:
            break
        continuation_key, continuation_value = _split_key_value(line.strip())
        item[continuation_key] = _clean_value(continuation_value)
        index += 1
    return item, index


def _parse_scalar_map(nested_lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in nested_lines:
        key, value = _split_key_value(line.strip())
        result[key] = _clean_value(value)
    return result


def _parse_block_scalar(
    section_lines: list[str], index: int, parent_indent: int, folded: bool
) -> tuple[str, int]:
    content_lines: list[str] = []
    while index < len(section_lines):
        line = section_lines[index]
        if not line.strip():
            content_lines.append("")
            index += 1
            continue
        if _indent_width(line) <= parent_indent:
            break
        content_lines.append(line.strip())
        index += 1
    if folded:
        return " ".join(part for part in content_lines if part), index
    return "\n".join(content_lines).rstrip("\n"), index


def _split_key_value(text: str) -> tuple[str, str]:
    separator = text.find(":")
    if separator <= 0:
        raise FrontmatterError(f"unsupported map item: {text!r}")
    return text[:separator].strip(), text[separator + 1 :].strip()


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
