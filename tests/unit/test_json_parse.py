from src.llm.json_parse import parse_json_robustly, strip_thought_tags


def test_strip_thought_tags_removes_paired_block():
    text = "<thought>internal reasoning</thought>final answer"
    assert strip_thought_tags(text) == "final answer"


def test_strip_thought_tags_drops_prefix_before_closing_tag():
    text = "leftover scratch</thought>actual output"
    assert strip_thought_tags(text) == "actual output"


def test_strip_thought_tags_leaves_clean_text_alone():
    assert strip_thought_tags("hello world") == "hello world"


def test_parse_json_robustly_direct():
    assert parse_json_robustly('{"a": 1}') == {"a": 1}


def test_parse_json_robustly_strips_markdown_fence():
    text = '```json\n{"a": 1, "b": "two"}\n```'
    assert parse_json_robustly(text) == {"a": 1, "b": "two"}


def test_parse_json_robustly_strips_thought_block():
    text = '<thought>let me think</thought>{"a": 1}'
    assert parse_json_robustly(text) == {"a": 1}


def test_parse_json_robustly_brace_scan_fallback():
    text = 'preamble noise {"a": 1, "b": 2} trailing chatter'
    assert parse_json_robustly(text) == {"a": 1, "b": 2}


def test_parse_json_robustly_unwraps_singleton_list():
    text = '[{"a": 1}]'
    assert parse_json_robustly(text) == {"a": 1}


def test_parse_json_robustly_returns_empty_dict_on_garbage():
    assert parse_json_robustly("not json at all") == {}


def test_parse_json_robustly_empty_input():
    assert parse_json_robustly("") == {}
