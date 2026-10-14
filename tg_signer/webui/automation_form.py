"""Pure helpers for the Automation visual relay-rule editor.

Keep configuration round-trips isolated from NiceGUI, so unsupported automation
rules are never silently rewritten by the limited visual editor.
"""

from __future__ import annotations

import copy
import re
from string import Formatter
from typing import Any

RULE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
MODES = ("forward", "copy", "text", "extract", "template")
DEDUP_MODES = ("message", "content", "off")
MATCH_TYPES = ("all", "contains", "exact", "regex")


def chat_ids_from_text(value: str, *, required: bool = True) -> list[int | str]:
    """Parse comma/newline separated Telegram Chat IDs or @usernames."""
    result: list[int | str] = []
    for item in re.split(r"[,，\n\r]+", value or ""):
        item = item.strip()
        if not item:
            continue
        if item.startswith("@"):
            if not re.fullmatch(r"@[a-zA-Z0-9_]{1,64}", item):
                raise ValueError(f"无效的用户名: {item}")
            parsed: int | str = item
        elif re.fullmatch(r"-?\d{1,20}", item):
            parsed = int(item)
        else:
            raise ValueError(f"请输入 Chat ID 或 @username: {item}")
        if parsed not in result:
            result.append(parsed)
    if required and not result:
        raise ValueError("至少填写一个来源或目标 Chat ID")
    if len(result) > 50:
        raise ValueError("最多支持 50 个来源")
    return result


def identifiers_text(value: list[int | str] | None) -> str:
    return "\n".join(str(v) for v in (value or []))


def validate_regex(pattern: str) -> None:
    if len(pattern) > 2048:
        raise ValueError("正则表达式不能超过 2048 个字符")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"正则表达式无效: {exc}") from exc


def build_relay_rule(
    *,
    rule_id: str,
    enabled: bool,
    sources: str,
    senders: str,
    text_rule: str,
    text_value: str,
    ignore_case: bool,
    ignore_self: bool,
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    rule_id = (rule_id or "").strip()
    if not RULE_ID.fullmatch(rule_id):
        raise ValueError("规则 ID 只能包含 1–64 位字母、数字、点、下划线和短横线")
    source_ids = chat_ids_from_text(sources)
    sender_ids = chat_ids_from_text(senders, required=False)
    if text_rule not in MATCH_TYPES:
        raise ValueError("未知的消息匹配模式")
    text_value = text_value or ""
    if text_rule != "all" and not text_value:
        raise ValueError("非 all 模式必须填写匹配内容")
    if text_rule == "regex":
        validate_regex(text_value)
    if not targets or len(targets) > 25:
        raise ValueError("至少添加 1 个目标，最多 25 个")
    clean_targets: list[dict[str, Any]] = []
    for index, target in enumerate(targets, 1):
        ids = chat_ids_from_text(str(target.get("chat_id") or ""))
        if len(ids) != 1:
            raise ValueError(f"第 {index} 个目标只能填写一个 Chat ID")
        chat_id = ids[0]
        if chat_id in source_ids:
            raise ValueError(f"第 {index} 个目标和来源相同，可能造成消息循环")
        mode = target.get("mode", "forward")
        dedup = target.get("dedup", "message")
        if mode not in MODES or dedup not in DEDUP_MODES:
            raise ValueError(f"第 {index} 个目标的转发模式或去重方式无效")
        clean: dict[str, Any] = {"chat_id": chat_id, "mode": mode, "dedup": dedup}
        if mode in {"extract", "template"}:
            pattern = (target.get("pattern") or "").strip()
            if mode == "extract" and not pattern:
                raise ValueError(f"第 {index} 个目标需要提取正则")
            if pattern:
                validate_regex(pattern)
                clean["pattern"] = pattern
        if mode == "extract":
            raw_group = str(target.get("group", "1")).strip()
            if not raw_group:
                raise ValueError(f"第 {index} 个目标需要捕获组")
            if re.fullmatch(r"\d+", raw_group):
                clean["group"] = int(raw_group)
            elif raw_group.isidentifier():
                clean["group"] = raw_group
            else:
                raise ValueError(f"第 {index} 个目标的捕获组无效")
            clean["all_matches"] = bool(target.get("all_matches", False))
        if mode == "template":
            template = target.get("template") or ""
            if not template:
                raise ValueError(f"第 {index} 个目标的模板不能为空")
            try:
                list(Formatter().parse(template))
            except ValueError as exc:
                raise ValueError(f"第 {index} 个目标模板格式无效: {exc}") from exc
            clean["template"] = template
        clean_targets.append(clean)
    trigger_params: dict[str, Any] = {"chat_ids": source_ids}
    if sender_ids:
        trigger_params["from_user_ids"] = sender_ids
    return {
        "id": rule_id,
        "enabled": bool(enabled),
        "triggers": [{"type": "message", "params": trigger_params}],
        "filters": {
            "text_rule": text_rule,
            "text_value": text_value if text_rule != "all" else None,
            "ignore_case": bool(ignore_case),
        },
        "handlers": [{
            "handler": "relay_message",
            "params": {
                "ignore_self": bool(ignore_self),
                "targets": clean_targets,
            },
        }],
    }


def editable_rule(rule: dict[str, Any]) -> bool:
    """Reject complex rules rather than stripping unfamiliar handlers/fields."""
    triggers = rule.get("triggers") or []
    handlers = rule.get("handlers") or []
    return (
        len(triggers) == 1
        and triggers[0].get("type") == "message"
        and set(triggers[0].get("params", {}))
        <= {"chat_id", "chat_ids", "from_user_ids"}
        and len(handlers) == 1
        and handlers[0].get("handler") == "relay_message"
        and not rule.get("vars")
        and set((rule.get("filters") or {}))
        <= {"text_rule", "text_value", "ignore_case"}
        and set(handlers[0].get("params", {})) <= {"ignore_self", "targets"}
        and all(
            set(target) <= {
                "chat_id", "mode", "dedup", "pattern", "group",
                "all_matches", "template"
            }
            for target in handlers[0].get("params", {}).get("targets", [])
            if isinstance(target, dict)
        )
    )


def rule_as_form(rule: dict[str, Any]) -> dict[str, Any]:
    if not editable_rule(rule):
        raise ValueError("此规则包含高级配置，请使用 JSON 编辑器修改")
    params = rule["triggers"][0]["params"]
    flt = rule.get("filters") or {}
    relay = rule["handlers"][0]["params"]
    return {
        "rule_id": rule["id"],
        "enabled": rule.get("enabled", True),
        "sources": identifiers_text(
            params.get("chat_ids") or (
                [params["chat_id"]] if params.get("chat_id") is not None else []
            )
        ),
        "senders": identifiers_text(params.get("from_user_ids")),
        "text_rule": flt.get("text_rule", "all"),
        "text_value": flt.get("text_value") or "",
        "ignore_case": flt.get("ignore_case", True),
        "ignore_self": relay.get("ignore_self", True),
        "targets": copy.deepcopy(relay.get("targets", [])),
    }


def replace_rule(
    config: dict[str, Any], new_rule: dict[str, Any], old_id: str | None = None
) -> dict[str, Any]:
    result = copy.deepcopy(config)
    if not isinstance(result, dict) or not isinstance(result.get("rules", []), list):
        raise ValueError("Automation 配置格式无效")
    rules = result.setdefault("rules", [])
    found = False
    for index, item in enumerate(rules):
        if item.get("id") == new_rule["id"] and item.get("id") != old_id:
            raise ValueError("规则 ID 已存在")
        if old_id is not None and item.get("id") == old_id:
            rules[index] = copy.deepcopy(new_rule)
            found = True
    if old_id is not None and not found:
        raise ValueError("要编辑的规则不存在")
    if old_id is None:
        rules.append(copy.deepcopy(new_rule))
    return result


def delete_rule(config: dict[str, Any], rule_id: str) -> dict[str, Any]:
    result = copy.deepcopy(config)
    rules = result.get("rules") or []
    result["rules"] = [r for r in rules if r.get("id") != rule_id]
    if len(result["rules"]) == len(rules):
        raise ValueError("规则不存在")
    return result
