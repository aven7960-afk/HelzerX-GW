from .memory import ConversationMemory
from .prompts import system_prompt
from .triggers import strip_trigger

class AIService:
    def __init__(self, db, timezone_name="UTC"):
        self.memory = ConversationMemory(db)
        self.timezone_name = timezone_name

    def prompt(self, guild_name=None):
        return system_prompt(self.timezone_name, guild_name)

    def clean_trigger(self, content, bot_id=None):
        return strip_trigger(content, bot_id)
