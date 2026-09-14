from __future__ import annotations

import json

from utils import now_ts
from .context import conversation_scope
from .groq_provider import GroqProvider
from .memory import ConversationMemory
from .prompts import system_prompt


def install(agent_class):
    original_init = agent_class.__init__

    def init(self, bot, db, settings):
        original_init(self, bot, db, settings)
        self.groq_provider = GroqProvider(settings.groq_api_key, settings.groq_model)
        # handle_message in the legacy agent checks this before calling ask().
        # Groq replaces the legacy OpenAI path, so a sentinel keeps that
        # compatibility check from silently dropping messages.
        self.client = object()

    async def ask(self, message, prompt):
        if not hasattr(self, "memory"):
            self.memory = ConversationMemory(self.db, limit=20)

        key = conversation_scope(message)
        previous = await self.memory.recent(key)
        self.history[key].clear()
        for role, content in previous:
            self.history[key].append((role, content))

        requester = getattr(message.author, "id", 0)
        context = (
            f"Requester ID: {requester}\n"
            f"Current channel ID: {getattr(message.channel, 'id', 0)}\n"
            f"Mentioned user IDs: {[u.id for u in message.mentions]}\n"
            f"Mentioned channel IDs: {[c.id for c in message.channel_mentions]}\n"
        )
        if message.reference and getattr(message.reference, "resolved", None) is not None:
            replied = message.reference.resolved
            if hasattr(replied, "content"):
                context += f"Message being replied to: {replied.author.display_name}: {replied.content}\n"
        if previous:
            history_text = "\n".join(f"{role}: {content}" for role, content in previous)
            context += f"Recent conversation:\n{history_text}\n"
        context += f"Current request: {prompt}"

        tools = getattr(__import__("ai_agent"), "TOOLS", []) if message.guild else []
        messages = [
            {"role": "system", "content": self.instructions(message.guild)},
            {"role": "user", "content": context},
        ]

        for _ in range(8):
            response = await self.groq_provider.chat(messages, tools)
            calls = self.groq_provider.tool_calls(response)
            if not calls:
                answer = self.groq_provider.text(response) or "Done."
                user_id = int(message.author.id)
                await self.memory.add(key, user_id, "User", prompt, now_ts())
                await self.memory.add(key, user_id, "Helzer", answer, now_ts())
                return answer

            assistant_message = response.get("message") or {"role": "assistant", "content": ""}
            # Chat Completions requires tool calls to be preserved on the
            # assistant message before corresponding tool results are added.
            messages.append(assistant_message)
            for call in calls:
                function = call.get("function") or {}
                name = function.get("name", "")
                raw_args = function.get("arguments", {})
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    args = {}
                result = await self._dispatch_local(message, name, args)
                if result.get("status") == "confirmation_required":
                    from ai_ui import ConfirmationView
                    return ConfirmationView(self, result["action_id"], result["title"], result["details"])
                messages.append(self.groq_provider.tool_result_message(call, result))

        return "The request required too many steps."

    async def _dispatch_local(self, message, name, args):
        return await agent_class.dispatch(self, message, name, args)

    def instructions(self, guild=None):
        guild_name = getattr(guild, "name", None)
        return system_prompt(self.settings.ai_timezone, guild_name)

    agent_class.__init__ = init
    agent_class.ask = ask
    agent_class._dispatch_local = _dispatch_local
    agent_class.instructions = instructions
    agent_class.conversation_key = lambda self, message: conversation_scope(message)
    return agent_class
