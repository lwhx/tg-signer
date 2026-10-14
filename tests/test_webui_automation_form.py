"""Regression coverage for the visual relay-rule form and safe regex preview."""

import copy

import pytest

from tg_signer.webui.automation_form import (
    build_relay_rule,
    chat_ids_from_text,
    delete_rule,
    editable_rule,
    replace_rule,
    rule_as_form,
)
from tg_signer.webui.regex_preview import preview_text_match


def sample_rule(**overrides):
    args = dict(
        rule_id="relay_2026_news",
        enabled=True,
        sources="@source_one\n-100123456",
        senders="",
        text_rule="regex",
        text_value=r"20\d{2}.*新闻",
        ignore_case=True,
        ignore_self=True,
        targets=[
            {"chat_id": "@archive", "mode": "forward", "dedup": "message"},
            {
                "chat_id": "-100991",
                "mode": "extract",
                "pattern": r"(https?://[^\s]+)",
                "group": 1,
                "all_matches": True,
                "dedup": "content",
            },
        ],
    )
    args.update(overrides)
    return build_relay_rule(**args)


def test_chat_ids_parse_multiline_and_dedup():
    assert chat_ids_from_text("@A, @A\n-100123\n-100123") == [
        "@A",
        -100123,
    ]


@pytest.mark.parametrize(
    "invalid",
    ["../etc/passwd", "source-name", "abc", "@hello.world", "123a"],
)
def test_invalid_chat_id_rejected(invalid):
    with pytest.raises(ValueError):
        chat_ids_from_text(invalid)


def test_rule_building_and_round_trip():
    rule = sample_rule()
    assert rule["triggers"][0]["params"]["chat_ids"] == [
        "@source_one",
        -100123456,
    ]
    assert rule["handlers"][0]["params"]["targets"][1]["group"] == 1
    assert editable_rule(rule)
    form = rule_as_form(rule)
    assert form["rule_id"] == rule["id"]
    reconstructed = build_relay_rule(**form)
    assert reconstructed == rule


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rule_id": "../illegal"},
        {"sources": ""},
        {"text_rule": "contains", "text_value": ""},
        {"text_rule": "regex", "text_value": "("},
        {"targets": []},
        {"targets": [{"chat_id": "@source_one", "mode": "forward"}]},
        {"targets": [{"chat_id": "@dest", "mode": "unknown"}]},
        {"targets": [{"chat_id": "@dest", "mode": "extract"}]},
        {
            "targets": [
                {"chat_id": "@dest", "mode": "template", "template": "{text"}
            ]
        },
    ],
)
def test_reject_invalid_visual_rule(kwargs):
    with pytest.raises(ValueError):
        sample_rule(**kwargs)


def test_named_capture_and_template_are_supported():
    rule = sample_rule(
        targets=[
            {
                "chat_id": "@dest",
                "mode": "extract",
                "pattern": r"(?P<url>https?://[^\s]+)",
                "group": "url",
                "dedup": "content",
            },
            {
                "chat_id": "@archive",
                "mode": "template",
                "template": "文本：{text}",
                "pattern": r"\w+",
            },
        ]
    )
    assert rule["handlers"][0]["params"]["targets"][0]["group"] == "url"


def test_preserve_unrelated_rules_and_reject_duplicate_ids():
    existing = {
        "rules": [
            {
                "id": "timer_do_not_touch",
                "triggers": [{"type": "timer", "params": {"interval_seconds": 60}}],
                "handlers": [{"handler": "send_text", "params": {"text": "hello"}}],
            }
        ]
    }
    original = copy.deepcopy(existing)
    updated = replace_rule(existing, sample_rule())
    assert existing == original
    assert updated["rules"][0] == original["rules"][0]
    assert len(updated["rules"]) == 2
    with pytest.raises(ValueError):
        replace_rule(updated, sample_rule())
    renamed = sample_rule(rule_id="relay_renamed")
    updated = replace_rule(updated, renamed, old_id="relay_2026_news")
    assert updated["rules"][1]["id"] == "relay_renamed"
    with pytest.raises(ValueError):
        replace_rule(updated, renamed, old_id="missing")
    result = delete_rule(updated, "relay_renamed")
    assert result["rules"] == original["rules"]
    with pytest.raises(ValueError):
        delete_rule(result, "relay_renamed")


def test_advanced_rule_is_not_edited_visually():
    advanced = sample_rule()
    advanced["handlers"].append({"handler": "send_text", "params": {"text": "hi"}})
    assert not editable_rule(advanced)
    with pytest.raises(ValueError):
        rule_as_form(advanced)


def test_dynamic_year_regex_preview_and_capture_groups():
    msg = (
        "2027｜长时｜连载｜国漫｜22T\n"
        "https://115cdn.com/s/abc?password=123#"
    )
    pattern = (
        r"\A20\d{2}｜长时｜连载｜国漫｜[^\r\n]+"
        r"\n(https?://115cdn\.com/s/[^\s]+)\Z"
    )
    result = preview_text_match("regex", pattern, msg)
    assert result["matched"] is True
    assert result["groups"] == [
        "https://115cdn.com/s/abc?password=123#"
    ]
    assert preview_text_match(
        "regex", pattern, msg.replace("长时", "短时")
    )["matched"] is False
    assert preview_text_match("contains", "连载", msg)["matched"] is True
    assert preview_text_match("exact", "ABC", "abc")["matched"] is True
    assert preview_text_match("all", "", "")["matched"] is True


def test_bad_regex_and_preview_input_limits():
    result = preview_text_match("regex", "(", "hello")
    assert "error" in result
    with pytest.raises(ValueError):
        preview_text_match("regex", "a", "x" * 8001)
    with pytest.raises(ValueError):
        preview_text_match("regex", "x" * 2049, "ok")


def test_extract_rejects_nonexistent_capture_groups():
    with pytest.raises(ValueError, match="捕获组"):
        sample_rule(
            targets=[
                {
                    "chat_id": "@dest",
                    "mode": "extract",
                    "pattern": r"(hello)",
                    "group": 2,
                }
            ]
        )
    with pytest.raises(ValueError, match="命名捕获组"):
        sample_rule(
            targets=[
                {
                    "chat_id": "@dest",
                    "mode": "extract",
                    "pattern": r"(hello)",
                    "group": "missing",
                }
            ]
        )


def test_advanced_rule_custom_fields_are_preserved():
    custom = sample_rule()
    custom["description"] = "Do not drop this custom field"
    assert not editable_rule(custom)
    existing = {"rules": [custom]}
    newer = replace_rule(existing, sample_rule(rule_id="other_rule"))
    assert newer["rules"][0] == custom
