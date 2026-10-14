"""Interactive message forwarding rule editor for the tg-signer WebUI.

Only a well-defined message/relay_message subset is editable visually.
Other existing Automation rules are kept byte-equivalent as JSON structures.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Callable

from nicegui import ui

from tg_signer.config import AutomationConfig
from tg_signer.webui.automation_form import (
    DEDUP_MODES,
    MATCH_TYPES,
    MODES,
    build_relay_rule,
    delete_rule,
    editable_rule,
    replace_rule,
    rule_as_form,
)
from tg_signer.webui.regex_preview import preview_text_match

MATCH_LABELS = {
    "all": "全部消息",
    "contains": "包含关键词",
    "exact": "完全匹配",
    "regex": "正则表达式",
}
MODE_LABELS = {
    "forward": "原生转发（保留来源）",
    "copy": "复制消息（不显示来源）",
    "text": "发送纯文本",
    "extract": "正则提取后发送",
    "template": "按模板生成文本",
}
DEDUP_LABELS = {
    "message": "按来源消息去重",
    "content": "按内容去重",
    "off": "不去重",
}


class RelayTargetCard:
    def __init__(
        self, position: int, initial: dict[str, Any], on_remove, on_mode_change
    ) -> None:
        with ui.card().classes("w-full border rounded-lg p-3") as self.container:
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(f"目标 {position + 1}").classes("font-semibold")
                ui.button(
                    "移除", icon="delete",
                    on_click=lambda: on_remove(self),
                ).props("flat dense color=negative")
            self.chat = ui.input(
                "发送到 Chat ID / @username",
                value=str(initial.get("chat_id") or ""),
                placeholder="@target_channel 或 -100123456789",
            ).classes("w-full")
            with ui.row().classes("w-full gap-3"):
                self.mode = ui.select(
                    {key: MODE_LABELS[key] for key in MODES},
                    value=initial.get("mode", "forward"),
                    label="转发方式",
                ).classes("min-w-[230px]")
                self.dedup = ui.select(
                    {key: DEDUP_LABELS[key] for key in DEDUP_MODES},
                    value=initial.get("dedup", "message"),
                    label="去重规则",
                ).classes("min-w-[210px]")
            self.pattern = ui.input(
                "提取正则（extract 必填，template 可选）",
                value=initial.get("pattern", ""),
            ).classes("w-full")
            self.group = ui.input(
                "捕获组（数字或命名组）",
                value=str(initial.get("group", 1)),
            ).classes("w-full")
            self.all_matches = ui.switch(
                "提取所有匹配（上限 20 条）",
                value=bool(initial.get("all_matches", False)),
            )
            self.template = ui.textarea(
                "消息模板",
                value=initial.get("template", ""),
                placeholder="例如：来源 {chat_id}，正文：{text}",
            ).classes("w-full")
            self.mode.on_value_change(
                lambda _: (self.refresh_visibility(), on_mode_change())
            )
            self.refresh_visibility()

    def refresh_visibility(self) -> None:
        mode = self.mode.value
        self.pattern.visible = mode in {"extract", "template"}
        self.group.visible = mode == "extract"
        self.all_matches.visible = mode == "extract"
        self.template.visible = mode == "template"

    def values(self) -> dict[str, Any]:
        return {
            "chat_id": self.chat.value or "",
            "mode": self.mode.value,
            "dedup": self.dedup.value,
            "pattern": self.pattern.value or "",
            "group": self.group.value or "1",
            "all_matches": bool(self.all_matches.value),
            "template": self.template.value or "",
        }


class RelayRuleDialog:
    def __init__(
        self,
        payload: dict[str, Any],
        on_apply: Callable[[dict[str, Any]], None],
    ) -> None:
        self.payload = copy.deepcopy(payload)
        self.on_apply = on_apply
        self.targets: list[RelayTargetCard] = []
        self.selected_id: str | None = None

    def open(self) -> None:
        editable = {
            str(r.get("id")): str(r.get("id"))
            for r in self.payload.get("rules", [])
            if isinstance(r, dict) and editable_rule(r)
        }
        total = len(self.payload.get("rules", []))
        with ui.dialog() as self.dialog:
            with ui.card().classes("w-full max-w-5xl p-4 gap-4"):
                ui.label("通用消息监控与转发 · 可视化规则").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "仅编辑普通消息转发规则；定时任务、签到等高级规则不会被覆盖。"
                    "修改后仍需点击配置页面的「保存」按钮写入磁盘。"
                ).classes("text-sm text-gray-600")
                if total > len(editable):
                    ui.label(
                        f"另有 {total - len(editable)} 条高级规则，请使用 JSON 编辑器。"
                    ).classes("text-sm text-amber-700")
                self.rule_select = ui.select(
                    {"": "＋ 新建消息转发规则", **editable},
                    value="",
                    label="选择要编辑的规则",
                ).classes("w-full")
                self.rule_select.on_value_change(self.load_selected)

                with ui.scroll_area().classes("w-full").style("max-height: 65vh"):
                    with ui.column().classes("w-full gap-3"):
                        with ui.expansion(
                            "1. 来源与匹配条件", icon="filter_alt", value=True
                        ).classes("w-full border rounded-lg"):
                            self.rule_id = ui.input(
                                "规则 ID", placeholder="relay_news"
                            ).classes("w-full")
                            self.enabled = ui.switch("启用此规则", value=True)
                            self.sources = ui.textarea(
                                "来源频道 / 群组 Chat ID（每行一个）",
                                placeholder="@channel_name\n-100123456789",
                            ).classes("w-full")
                            self.senders = ui.textarea(
                                "仅接收这些发送者（可选，每行一个）"
                            ).classes("w-full")
                            self.text_rule = ui.select(
                                MATCH_LABELS, value="all", label="匹配类型"
                            ).classes("w-full")
                            self.text_value = ui.textarea(
                                "匹配关键词 / 正则表达式"
                            ).classes("w-full")
                            self.ignore_case = ui.switch(
                                "忽略英文大小写", value=True
                            )
                            self.ignore_self = ui.switch(
                                "忽略自己发送的消息，防止循环", value=True
                            )
                            self.text_rule.on_value_change(
                                lambda _: self.toggle_filter()
                            )
                        with ui.expansion(
                            "2. 转发目标（可配置多个）", icon="send", value=True
                        ).classes("w-full border rounded-lg"):
                            self.target_container = ui.column().classes(
                                "w-full gap-3"
                            )
                            ui.button(
                                "添加目标", icon="add", on_click=self.add_target
                            ).props("outline")
                        with ui.expansion(
                            "3. 正则匹配测试", icon="science", value=False
                        ).classes("w-full border rounded-lg"):
                            self.test_scope = ui.select(
                                {"filter": "测试消息过滤"},
                                value="filter",
                                label="测试对象",
                            ).classes("w-full")
                            self.sample = ui.textarea(
                                "粘贴 Telegram 消息样本",
                                placeholder="在此粘贴实际收到的消息正文",
                            ).classes("w-full")
                            ui.button(
                                "测试匹配", icon="play_arrow",
                                on_click=self.run_preview,
                            ).props("outline")
                            self.preview = ui.code(
                                "等待测试", language="json"
                            ).classes("w-full")
                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button(
                        "删除选中规则",
                        on_click=self.confirm_delete,
                    ).props("flat color=negative")
                    ui.button("取消", on_click=self.dialog.close).props("flat")
                    ui.button(
                        "应用到 JSON 编辑器",
                        on_click=self.apply,
                    ).props("color=primary")
        self.reset_form()
        self.dialog.open()

    def reset_form(self) -> None:
        self.selected_id = None
        self.rule_id.value = ""
        self.enabled.value = True
        self.sources.value = ""
        self.senders.value = ""
        self.text_rule.value = "all"
        self.text_value.value = ""
        self.ignore_case.value = True
        self.ignore_self.value = True
        self.set_targets([{"chat_id": "", "mode": "forward", "dedup": "message"}])
        self.toggle_filter()

    def toggle_filter(self) -> None:
        self.text_value.visible = self.text_rule.value != "all"

    def load_selected(self, _=None) -> None:
        rule_id = self.rule_select.value
        if not rule_id:
            self.reset_form()
            return
        selected = next(
            (r for r in self.payload.get("rules", []) if r.get("id") == rule_id),
            None,
        )
        if selected is None:
            return
        try:
            values = rule_as_form(selected)
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
            return
        self.selected_id = str(rule_id)
        self.rule_id.value = values["rule_id"]
        self.enabled.value = values["enabled"]
        self.sources.value = values["sources"]
        self.senders.value = values["senders"]
        self.text_rule.value = values["text_rule"]
        self.text_value.value = values["text_value"]
        self.ignore_case.value = values["ignore_case"]
        self.ignore_self.value = values["ignore_self"]
        self.set_targets(values["targets"])
        self.toggle_filter()

    def set_targets(self, targets: list[dict[str, Any]]) -> None:
        self.target_container.clear()
        self.targets = []
        with self.target_container:
            for item in targets:
                card = RelayTargetCard(
                    len(self.targets), item, self.remove_target, self.refresh_test_options
                )
                self.targets.append(card)
        self.refresh_test_options()

    def add_target(self) -> None:
        if len(self.targets) >= 25:
            ui.notify("最多支持 25 个目标", type="warning")
            return
        with self.target_container:
            self.targets.append(
                RelayTargetCard(
                    len(self.targets), {}, self.remove_target,
                    self.refresh_test_options,
                )
            )
        self.refresh_test_options()

    def remove_target(self, card: RelayTargetCard) -> None:
        values = [w.values() for w in self.targets if w is not card]
        self.set_targets(values)

    def refresh_test_options(self) -> None:
        if not hasattr(self, "test_scope"):
            return
        options = {"filter": "测试消息过滤"}
        for i, card in enumerate(self.targets):
            if card.mode.value in {"extract", "template"}:
                options[str(i)] = f"测试目标 {i + 1} 的提取正则"
        self.test_scope.options = options
        if self.test_scope.value not in options:
            self.test_scope.value = "filter"
        self.test_scope.update()

    def run_preview(self) -> None:
        try:
            scope = self.test_scope.value
            if scope == "filter":
                mode = self.text_rule.value
                pattern = self.text_value.value or ""
                ignore_case = bool(self.ignore_case.value)
            else:
                idx = int(scope)
                target = self.targets[idx].values()
                mode = "regex"
                pattern = target["pattern"]
                ignore_case = True
                if not pattern:
                    raise ValueError("所选目标尚未设置提取正则")
            result = preview_text_match(
                mode, pattern, self.sample.value or "", ignore_case
            )
            self.preview.content = json.dumps(result, ensure_ascii=False, indent=2)
            self.preview.update()
        except (ValueError, IndexError) as exc:
            ui.notify(str(exc), type="negative")

    def apply(self) -> None:
        try:
            rule = build_relay_rule(
                rule_id=self.rule_id.value or "",
                enabled=bool(self.enabled.value),
                sources=self.sources.value or "",
                senders=self.senders.value or "",
                text_rule=self.text_rule.value,
                text_value=self.text_value.value or "",
                ignore_case=bool(self.ignore_case.value),
                ignore_self=bool(self.ignore_self.value),
                targets=[card.values() for card in self.targets],
            )
            payload = replace_rule(self.payload, rule, self.selected_id)
            AutomationConfig.model_validate(payload)
            self.on_apply(payload)
            self.dialog.close()
            ui.notify(
                "规则已更新到 JSON 编辑器，请点击下面的「保存」按钮",
                type="positive",
            )
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"规则无法保存: {exc}", type="negative")

    def confirm_delete(self) -> None:
        if not self.selected_id:
            ui.notify("请先选择一条已有规则", type="warning")
            return
        with ui.dialog() as confirm:
            with ui.card().classes("p-4 gap-3"):
                ui.label(f"确定从配置中删除规则 {self.selected_id} 吗？")
                ui.label("该操作只更新编辑器，必须再次点击保存才会写入磁盘。")
                with ui.row():
                    ui.button("取消", on_click=confirm.close).props("flat")

                    def remove() -> None:
                        try:
                            updated = delete_rule(self.payload, self.selected_id)
                            AutomationConfig.model_validate(updated)
                            self.on_apply(updated)
                            confirm.close()
                            self.dialog.close()
                            ui.notify(
                                "规则已从 JSON 编辑器移除，请点击保存",
                                type="positive",
                            )
                        except ValueError as exc:
                            ui.notify(str(exc), type="negative")

                    ui.button("确认删除", on_click=remove).props("color=negative")
        confirm.open()
