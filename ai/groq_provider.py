from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b"


class GroqProvider:
    """Groq-backed chat provider using the existing OpenAI SDK."""

    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL):
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing")
        self.model = model or DEFAULT_MODEL
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None):
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "reasoning_effort": "low",
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        return {
            "message": {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in (message.tool_calls or [])
                ],
            }
        }

    @staticmethod
    def tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        return (response.get("message") or {}).get("tool_calls") or []

    @staticmethod
    def text(response: dict[str, Any]) -> str:
        return ((response.get("message") or {}).get("content") or "").strip()

    @staticmethod
    def tool_result_message(call: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": call.get("id", ""),
            "content": json.dumps(result),
        }
