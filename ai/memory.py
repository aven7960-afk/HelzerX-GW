from __future__ import annotations


class ConversationMemory:
    def __init__(self, db, limit: int = 20):
        self.db = db
        self.limit = limit
        self._ready = False

    async def ensure(self) -> None:
        if self._ready:
            return
        await self.db.execute("CREATE TABLE IF NOT EXISTS ai_conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, scope_key TEXT NOT NULL, user_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at INTEGER NOT NULL)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_ai_conversations_scope ON ai_conversations(scope_key, id)")
        self._ready = True

    async def recent(self, scope_key: str) -> list[tuple[str, str]]:
        await self.ensure()
        rows = await self.db.fetchall("SELECT role, content FROM ai_conversations WHERE scope_key=? ORDER BY id DESC LIMIT ?", (scope_key, self.limit))
        rows.reverse()
        return [(row["role"], row["content"]) for row in rows]

    async def add(self, scope_key: str, user_id: int, role: str, content: str, created_at: int) -> None:
        await self.ensure()
        await self.db.insert("INSERT INTO ai_conversations(scope_key,user_id,role,content,created_at) VALUES (?,?,?,?,?)", (scope_key, user_id, role, content[:12000], created_at))
        await self.db.execute("DELETE FROM ai_conversations WHERE scope_key=? AND id NOT IN (SELECT id FROM ai_conversations WHERE scope_key=? ORDER BY id DESC LIMIT ?)", (scope_key, scope_key, self.limit * 2))
