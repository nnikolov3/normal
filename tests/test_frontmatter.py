"""Tests for the frontmatter parser (machine-clean subset parser)."""

import pytest

from formal.frontmatter import FrontmatterError, parse_frontmatter


def test_parse_frontmatter_when_well_formed_then_fields_and_body_extracted():
    document = "---\nname: Skill Creator\nmode: all\nsteps: 150\n---\n\n# Body\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["name"] == "Skill Creator"
    assert parsed.fields["mode"] == "all"
    assert parsed.fields["steps"] == "150"
    assert parsed.body.lstrip().startswith("# Body")


def test_parse_frontmatter_when_block_scalar_folded_then_lines_joined_with_space():
    document = "---\ndescription: >\n  First line\n  second line\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["description"] == "First line second line"


def test_parse_frontmatter_when_block_scalar_literal_then_lines_joined_with_newline():
    document = "---\ndescription: |\n  First line\n  second line\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["description"] == "First line\nsecond line"


def test_parse_frontmatter_when_plain_list_then_items_extracted():
    document = "---\nitems:\n  - alpha\n  - beta\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["items"] == ["alpha", "beta"]


def test_parse_frontmatter_when_list_of_maps_then_rows_extracted():
    document = (
        "---\npermissions:\n"
        "  - action: read\n"
        '    resource: "*.env"\n'
        "    effect: deny\n"
        "  - action: shell\n"
        '    resource: "rm -r *"\n'
        "    effect: ask\n"
        "---\nbody\n"
    )
    parsed = parse_frontmatter(document)
    rows = parsed.fields["permissions"]
    assert rows[0] == {"action": "read", "resource": "*.env", "effect": "deny"}
    assert rows[1]["resource"] == "rm -r *"


def test_parse_frontmatter_when_missing_opening_delimiter_then_raises():
    with pytest.raises(FrontmatterError):
        parse_frontmatter("name: orphan document\n")


def test_parse_frontmatter_when_missing_closing_delimiter_then_raises():
    with pytest.raises(FrontmatterError):
        parse_frontmatter("---\nname: broken\nbody without closing delimiter\n")


def test_parse_frontmatter_when_quoted_value_then_quotes_stripped():
    document = '---\nmodel: "synthetic/hf:zai-org/GLM-5.3-Flash"\n---\nbody\n'
    parsed = parse_frontmatter(document)
    assert parsed.fields["model"] == "synthetic/hf:zai-org/GLM-5.3-Flash"


def test_parse_frontmatter_when_folded_block_has_blank_lines_then_blanks_dropped():
    document = "---\ndescription: >\n  First line\n\n  second line\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["description"] == "First line second line"


def test_parse_frontmatter_when_literal_block_has_blank_lines_then_blanks_kept_and_stripped():
    document = "---\ndescription: |\n  First line\n\n  second line\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["description"] == "First line\n\nsecond line"


def test_parse_frontmatter_when_scalar_map_field_then_map_extracted():
    document = "---\nmetadata:\n  key: value\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["metadata"] == {"key": "value"}


def test_parse_frontmatter_when_scalar_map_line_lacks_colon_then_raises():
    with pytest.raises(FrontmatterError):
        parse_frontmatter("---\nmetadata:\n  broken line\n---\nbody\n")


def test_parse_frontmatter_when_top_level_line_starts_with_dash_then_raises():
    with pytest.raises(FrontmatterError):
        parse_frontmatter("---\n- bad: line\n---\nbody\n")


def test_parse_frontmatter_when_single_quoted_value_then_quotes_stripped():
    document = "---\nname: 'quoted name'\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["name"] == "quoted name"


def test_parse_frontmatter_when_chomping_markers_then_accepted():
    document = "---\ndescription: >-\n  folded chomped\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["description"] == "folded chomped"


def test_parse_frontmatter_when_map_item_continuation_has_blank_line_then_skipped():
    document = '---\npermissions:\n  - action: read\n\n    resource: "*.env"\n---\nbody\n'
    parsed = parse_frontmatter(document)
    assert parsed.fields["permissions"] == [{"action": "read", "resource": "*.env"}]


def test_parse_frontmatter_when_field_header_lacks_colon_then_raises():
    with pytest.raises(FrontmatterError):
        parse_frontmatter("---\nname without colon\n---\nbody\n")


def test_parse_frontmatter_when_nested_field_followed_by_sibling_then_empty_and_sibling_kept():
    document = "---\nitems:\nname: sibling\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["items"] == []
    assert parsed.fields["name"] == "sibling"


def test_parse_frontmatter_when_blank_line_between_list_items_then_items_extracted():
    document = "---\nitems:\n  - alpha\n\n  - beta\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["items"] == ["alpha", "beta"]


def test_parse_frontmatter_when_list_item_deeper_indented_then_skipped():
    document = "---\nitems:\n  - alpha\n    - beta\n---\nbody\n"
    parsed = parse_frontmatter(document)
    assert parsed.fields["items"] == ["alpha"]
