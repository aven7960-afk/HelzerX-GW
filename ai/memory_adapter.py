from __future__ import annotations

from utils import now_ts
from .context import conversation_scope
from .memory import ConversationMemory
from .prompts import system_prompt


def install(agent_class):
    original_ask = agent_class.ask

    async def ask(self, message, prompt):
        if not hasattr(self, "memory"):
            self.memory = ConversationMemory(self.db, limit=20)
        key = conversation_scope(message)
        previous = await self.memory.recent(key)
        self.history[key].clear()
        for role, content in previous:
            self.history[key].append((role, content))
        answer = await original_ask(self, message, prompt)
        if isinstance(answer, str):
            user_id = int(message.author.id)
            await self.memory.add(key, user_id, "User", prompt, now_ts())
            await self.memory.add(key, user_id, "Helzer", answer, now_ts())
        return answer

    def instructions(self, guild=None):
        guild_name = getattr(guild, "name", None)
        return system_prompt(self.settings.ai_timezone, guild_name)

    agent_class.ask = ask
    agent_class.instructions = instructions
    agent_class.conversation_key = lambda self, message: conversation_scope(message)
    return agent_class
