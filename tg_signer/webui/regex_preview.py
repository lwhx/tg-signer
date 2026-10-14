"""Bounded regex preview used by the visual rules editor.

Python's re engine has no timeout. Run untrusted preview patterns in a short-lived
child process to avoid freezing the long-running NiceGUI server on backtracking.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any

_WORKER = """
import json
import re
import sys

try:
    data = json.loads(sys.stdin.read())
    flags = re.IGNORECASE if data['ignore_case'] else 0
    match = re.search(data['pattern'], data['sample'], flags=flags)
    if match:
        result = {
            'matched': True,
            'span': list(match.span()),
            'match': match.group(0)[:2000],
            'groups': [(g or '')[:2000] for g in match.groups()[:20]],
            'named_groups': {
                k: (v or '')[:2000] for k, v in match.groupdict().items()
            },
        }
    else:
        result = {'matched': False}
except (re.error, ValueError, KeyError, TypeError) as exc:
    result = {'error': str(exc)[:500]}
print(json.dumps(result, ensure_ascii=False))
"""


def preview_text_match(
    text_rule: str, pattern: str, sample: str, ignore_case: bool = True
) -> dict[str, Any]:
    if not isinstance(sample, str) or len(sample) > 8000:
        raise ValueError("测试消息最多 8000 个字符")
    if not isinstance(pattern, str) or len(pattern) > 2048:
        raise ValueError("匹配表达式最多 2048 个字符")
    if text_rule == "all":
        return {"matched": True, "match": "(全部消息)"}
    if text_rule == "exact":
        same = sample.casefold() == pattern.casefold() if ignore_case else sample == pattern
        return {"matched": same, "match": sample if same else ""}
    if text_rule == "contains":
        found = pattern.casefold() in sample.casefold() if ignore_case else pattern in sample
        return {"matched": found, "match": pattern if found else ""}
    if text_rule != "regex":
        raise ValueError("未知匹配模式")
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", _WORKER],
            input=json.dumps({
                "pattern": pattern,
                "sample": sample,
                "ignore_case": bool(ignore_case),
            }, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=1.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("正则匹配超时，请简化表达式") from exc
    if completed.returncode != 0:
        raise ValueError("正则测试进程异常")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("正则测试未返回有效结果") from exc
