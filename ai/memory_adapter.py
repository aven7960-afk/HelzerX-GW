from __future__ import annotations

import json

from utils import now_ts
from .context import conversation_scope
from .local_provider import OllamaProvider, choose_local_model
from .memory import ConversationMemory
from .prompts import system_prompt


def install(agent_class):
    original_init = agent_class.__init__

    def init(self, bot, db, settings):
        original_init(self, bot, db, settings)
        self.local_provider = OllamaProvider()
        # handle_message in the legacy agent checks this before calling ask().
        # The local provider does not need an OpenAI client, so a sentinel keeps
        # that compatibility check from silently dropping messages.
        if self.client is None:
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
        model = choose_local_model(prompt, bool(message.guild))
        messages = [{"role": "system", "content": self.instructions(message.guild)}]
        messages.append({"role": "user", "content": context})

        for _ in range(8):
            response = await self.local_provider.chat(messages, tools, model)
            calls = self.local_provider.tool_calls(response)
            if not calls:
                answer = self.local_provider.text(response) or "Done."
                user_id = int(message.author.id)
                await self.memory.add(key, user_id, "User", prompt, now_ts())
                await self.memory.add(key, user_id, "Helzer", answer, now_ts())
                return answer

            assistant_message = response.get("message") or {"role": "assistant", "content": ""}
            messages.append(assistant_message)
            for call in calls:
                function = call.get("function") or {}
                name = function.get("name", "")
                raw_args = function.get("arguments", {})
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                result = await self._dispatch_local(message, name, args)
                if result.get("status") == "confirmation_required":
                    from ai_ui import ConfirmationView
                    return ConfirmationView(self, result["action_id"], result["title"], result["details"])
                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result),
                })

        return "The request required too many steps."

    async def _dispatch_local(self, message, name, args):
        # Reuse the existing safety/Discord implementation from the legacy agent.
        return await agent_class.dispatch(self, message, name, args)

    def instructions(self, guild=None):
        guild_name = getattr(guild, "name", None)
        return system_prompt(self.settings.ai_timezone, guild_name)

    agent_class.__init__ = init
    agent_class.ask = ask
    agent_class.instructions = instructions
    agent_class.conversation_key = lambda self, message: conversation_scope(message)
    return agent_class
