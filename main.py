from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()

import discord
from discord.ext import commands

from commands import GiveawayCog
from config import Settings
from db import Database
from manager import GiveawayManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("helzerx-giveaway")


class HelzerXBot(commands.Bot):
    def __init__(self, settings: Settings, db: Database):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.db = db
        self.giveaways = GiveawayManager(self, db, settings)

    async def setup_hook(self) -> None:
        await self.db.init()
        await self.add_cog(GiveawayCog(self.giveaways))
        await self.giveaways.load_active()
        self.giveaways.start()

        if self.settings.sync_guild_id:
            guild = discord.Object(id=self.settings.sync_guild_id)
            await self.tree.sync(guild=guild)
            log.info("Application commands synced to guild %s.", guild.id)
        else:
            await self.tree.sync()
            log.info("Application commands synced globally.")

    async def on_ready(self) -> None:
        log.info(
            "Logged in as %s (%s) | %d guild(s)",
            self.user,
            self.user.id if self.user else "unknown",
            len(self.guilds),
        )


def main() -> None:
    settings = Settings.from_env()
    db = Database(settings.database_path)
    bot = HelzerXBot(settings, db)
    bot.run(settings.token)


if __name__ == "__main__":
    main()
