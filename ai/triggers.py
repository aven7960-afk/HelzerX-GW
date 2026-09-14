from __future__ import annotations

import re


def strip_trigger(content: str, bot_id: int | None = None) -> str:
    if bot_id:
        content = re.sub(rf"<@!?{bot_id}>", " ", content)
    content = re.sub(r"(?i)\bhelzer\b[,!:.;\-]*", " ", content)
    return re.sub(r"\s+", " ", content).strip()


def has_helzer_trigger(content: str, bot_id: int | None = None) -> bool:
    if bot_id and re.search(rf"<@!?{bot_id}>", content):
        return True
    return bool(re.search(r"(?i)\bhelzer\b", content))
