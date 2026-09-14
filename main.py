from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands

from commands import GiveawayCog
from config import Settings
from db import Database
from manager import GiveawayManager
from ai import HelzerAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("helzerx-giveaway")

class HelzerXBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.db = Database(settings.database_path)
        self.giveaways = GiveawayManager(self, self.db, settings)
        self.ai = HelzerAI(self, self.db, settings)

    async def setup_hook(self) -> None:
        await self.db.init()
        await self.add_cog(GiveawayCog(self.giveaways))
        if self.settings.sync_guild_id:
            guild = discord.Object(id=self.settings.sync_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Application commands synced to guild %s: %s", guild.id, [c.name for c in synced])
        else:
            synced = await self.tree.sync()
            log.info("Application commands synced globally: %s", [c.name for c in synced])
        await self.giveaways.load_active()
        self.giveaways.start()
        if self.settings.ai_enabled:
            self.ai.start()

    async def on_message(self, message: discord.Message) -> None:
        await self.ai.handle_message(message)
        await self.process_commands(message)

    async def on_ready(self) -> None:
        log.info("Logged in as %s (%s) | %d guild(s)", self.user, self.user.id if self.user else "unknown", len(self.guilds))

async def main() -> None:
    settings = Settings.from_env()
    bot = HelzerXBot(settings)
    async with bot:
        await bot.start(settings.token)

if __name__ == "__main__":
    asyncio.run(main())
