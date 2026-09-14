from __future__ import annotations

from utils import now_ts
from .context import conversation_scope
from .memory import ConversationMemory


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
        user_id = int(message.author.id)
        await self.memory.add(key, user_id, "User", prompt, now_ts())
        await self.memory.add(key, user_id, "Helzer", str(answer), now_ts())
        return answer

    agent_class.ask = ask
    agent_class.conversation_key = lambda self, message: conversation_scope(message)
    return agent_class
