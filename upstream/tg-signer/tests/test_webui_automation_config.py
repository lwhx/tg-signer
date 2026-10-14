"""Ensure native Automation task configs are managed safely by the WebUI."""

import pytest

from tg_signer.webui.data import (
    delete_config,
    list_task_names,
    load_config,
    save_config,
)


def test_automation_config_crud(tmp_path):
    payload = {
        "rules": [
            {
                "id": "test_automation",
                "enabled": True,
                "triggers": [{"type": "message", "params": {"chat_id": "@source"}}],
                "filters": {"text_rule": "all"},
                "handlers": [
                    {
                        "handler": "relay_message",
                        "params": {
                            "targets": [
                                {
                                    "chat_id": "@target",
                                    "mode": "forward",
                                    "dedup": "message",
                                }
                            ]
                        },
                    }
                ],
            }
        ]
    }
    path = save_config("automation", "test_task", payload, workdir=tmp_path)
    assert path == tmp_path / "automations" / "test_task" / "config.json"
    assert list_task_names("automation", tmp_path) == ["test_task"]
    loaded = load_config("automation", "test_task", tmp_path)
    assert loaded.payload["rules"][0]["id"] == "test_automation"
    assert loaded.payload["rules"][0]["handlers"][0]["handler"] == "relay_message"
    delete_config("automation", "test_task", tmp_path)
    assert list_task_names("automation", tmp_path) == []


@pytest.mark.parametrize("name", ["../escape", "/tmp/evil", "a/b", "a\\b", "..", "a\n"])
def test_reject_config_path_traversal(tmp_path, name):
    with pytest.raises(ValueError):
        save_config("automation", name, {"rules": []}, workdir=tmp_path)


def test_existing_signer_and_monitor_kinds_remain_registered():
    from tg_signer.webui.data import CONFIG_META

    assert set(CONFIG_META) >= {"signer", "monitor", "automation"}
