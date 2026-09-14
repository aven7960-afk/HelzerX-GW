from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from typing import Any


ACTION_HINTS = (
    "lock", "unlock", "ban", "kick", "timeout", "mute", "delete", "purge",
    "remove role", "add role", "give role", "send dm", "message", "schedule",
    "channel eka", "channel", "server eka", "server", "member", "user", "role",
    "block", "unblock",
)


def choose_local_model(prompt: str, has_guild: bool) -> str:
    if not has_guild:
        return "qwen3:1.7b"
    lowered = prompt.casefold()
    return "qwen2.5:7b" if any(hint in lowered for hint in ACTION_HINTS) else "qwen3:1.7b"


def ollama_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        converted.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        })
    return converted


class OllamaProvider:
    def __init__(self, base_url: str | None = None, timeout: float = 180.0):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.2},
        }
        if tools:
            payload["tools"] = ollama_tools(tools)
        return await asyncio.to_thread(self._request, payload)

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama is unavailable at {self.base_url}: {exc}") from exc

    @staticmethod
    def tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        message = response.get("message") or {}
        return message.get("tool_calls") or []

    @staticmethod
    def text(response: dict[str, Any]) -> str:
        return ((response.get("message") or {}).get("content") or "").strip()
