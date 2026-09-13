from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from emoji import CHECK, CROSS, WINNER
from manager import GiveawayManager
from ui import ClaimView, GiveawayView
from utils import now_ts, parse_duration


def _valid_image_url(value: str | None) -> bool:
    if not value:
        return True
    return value.startswith(("https://", "http://"))


class GiveawayCog(
    commands.GroupCog,
    group_name="giveaway",
    group_description="HelzerX Studio giveaway management",
):
    def __init__(self, manager: GiveawayManager):
        self.manager = manager
        super().__init__()

    @app_commands.command(name="create", description="Create a fully automated giveaway.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        name="Giveaway title.",
        prize="The prize displayed to participants.",
        duration="How long it runs: 30m, 2h, 3d, or 1d12h.",
        winners="Number of winners (1-20).",
        sponsor="Optional sponsor user.",
        image_url="Optional HTTPS image URL. Falls back to GIVEAWAY_IMAGE_URL.",
        reward="Optional internal/staff reward note.",
        reward_delay="Optional claim delay, e.g. 30m. Defaults to .env setting.",
        ticket_category="Optional category for private reward tickets.",
        required_role="Optional role required to enter.",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 1, 100],
        prize: app_commands.Range[str, 1, 500],
        duration: str,
        winners: app_commands.Range[int, 1, 20],
        sponsor: discord.Member | None = None,
        image_url: str | None = None,
        reward: str | None = None,
        reward_delay: str | None = None,
        ticket_category: discord.CategoryChannel | None = None,
        required_role: discord.Role | None = None,
    ):
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                f"{CROSS} This command must be used in a server text channel.",
                ephemeral=True,
            )
            return

        try:
            seconds = parse_duration(duration)
            delay_seconds = (
                parse_duration(reward_delay)
                if reward_delay and reward_delay.strip()
                else self.manager.settings.default_reward_delay
            )
        except ValueError as exc:
            await interaction.response.send_message(f"{CROSS} {exc}", ephemeral=True)
            return

        image = (image_url or "").strip() or self.manager.settings.giveaway_image_url
        if not _valid_image_url(image):
            await interaction.response.send_message(
                f"{CROSS} image_url must start with http:// or https://.",
                ephemeral=True,
            )
            return

        end_at = now_ts() + seconds
        await interaction.response.defer(ephemeral=True)

        giveaway_id = await self.manager.create(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=0,
            name=name,
            prize=prize,
            host_id=interaction.user.id,
            sponsor_id=sponsor.id if sponsor else None,
            winners_count=int(winners),
            end_at=end_at,
            image_url=image,
            reward=reward.strip() if reward else None,
            reward_delay=delay_seconds,
            ticket_category_id=ticket_category.id if ticket_category else None,
            required_role_id=required_role.id if required_role else None,
        )

        try:
            message = await interaction.channel.send(
                view=GiveawayView(self.manager, giveaway_id),
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except (discord.Forbidden, discord.HTTPException):
            await self.manager.db.execute(
                "UPDATE giveaways SET status='cancelled' WHERE id=?",
                (giveaway_id,),
            )
            self.manager.cache.pop(giveaway_id, None)
            self.manager.entry_cache.pop(giveaway_id, None)
            await interaction.followup.send(
                f"{CROSS} I could not send the giveaway message. Check Send Messages and Components permissions.",
                ephemeral=True,
            )
            return

        await self.manager.db.execute(
            "UPDATE giveaways SET message_id=? WHERE id=?",
            (message.id, giveaway_id),
        )
        self.manager.cache[giveaway_id]["message_id"] = message.id

        await interaction.followup.send(
            f"{CHECK} Giveaway created: {message.jump_url}\n"
            f"ID: `{giveaway_id}`",
            ephemeral=True,
        )

    @app_commands.command(name="end", description="End a giveaway immediately.")
    @app_commands.default_permissions(manage_guild=True)
    async def end(self, interaction: discord.Interaction, giveaway_id: int):
        await interaction.response.defer(ephemeral=True)
        data = await self.manager.db.fetchone(
            "SELECT status FROM giveaways WHERE id=?", (giveaway_id,)
        )
        if not data or data["status"] != "active":
            await interaction.followup.send(
                f"{CROSS} Active giveaway `{giveaway_id}` was not found.",
                ephemeral=True,
            )
            return

        winners = await self.manager.finish(giveaway_id)
        await interaction.followup.send(
            f"{CHECK} Giveaway `{giveaway_id}` ended. "
            f"{len(winners)} winner(s) selected.",
            ephemeral=True,
        )

    @app_commands.command(name="reroll", description="Select an additional winner from eligible entries.")
    @app_commands.default_permissions(manage_guild=True)
    async def reroll(self, interaction: discord.Interaction, giveaway_id: int):
        await interaction.response.defer(ephemeral=True)

        giveaway = await self.manager.db.fetchone(
            "SELECT * FROM giveaways WHERE id=?", (giveaway_id,)
        )
        if not giveaway:
            await interaction.followup.send(
                f"{CROSS} Giveaway not found.", ephemeral=True
            )
            return
        if giveaway["status"] != "ended":
            await interaction.followup.send(
                f"{CROSS} The giveaway must be ended before rerolling.",
                ephemeral=True,
            )
            return

        current = await self.manager.db.fetchall(
            "SELECT user_id FROM winners WHERE giveaway_id=?", (giveaway_id,)
        )
        excluded = {int(row["user_id"]) for row in current}
        candidates = await self.manager.db.fetchall(
            "SELECT user_id FROM entries WHERE giveaway_id=? AND valid=1",
            (giveaway_id,),
        )
        pool = [
            int(row["user_id"])
            for row in candidates
            if int(row["user_id"]) not in excluded
        ]
        if not pool:
            await interaction.followup.send(
                f"{CROSS} No eligible users remain for a reroll.",
                ephemeral=True,
            )
            return

        user_id = random.choice(pool)
        position = len(current) + 1
        ready_at = now_ts() + int(giveaway["reward_delay"])
        expires = ready_at + int(self.manager.settings.claim_window_seconds)

        await self.manager.db.execute(
            """
            INSERT INTO winners
            (giveaway_id, user_id, position, claimed, claim_expires,
             reward_ready_at, reward_status, dm_sent)
            VALUES (?, ?, ?, 0, ?, ?, 'pending', 0)
            """,
            (giveaway_id, user_id, position, expires, ready_at),
        )

        self.manager.bot.add_view(ClaimView(self.manager, giveaway_id, user_id))
        await self.manager.send_winner_dm(giveaway, user_id)

        channel = self.manager.bot.get_channel(giveaway["channel_id"])
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(
                    f"{WINNER} **Reroll winner:** <@{user_id}>",
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            except discord.HTTPException:
                pass

        await interaction.followup.send(
            f"{CHECK} Rerolled winner: <@{user_id}>",
            ephemeral=False,
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    @app_commands.command(name="info", description="Show giveaway information.")
    async def info(self, interaction: discord.Interaction, giveaway_id: int):
        data = await self.manager.db.fetchone(
            "SELECT * FROM giveaways WHERE id=?", (giveaway_id,)
        )
        if not data:
            await interaction.response.send_message(
                f"{CROSS} Giveaway not found.", ephemeral=True
            )
            return

        entries = await self.manager.db.entry_count(giveaway_id)
        sponsor = f"<@{data['sponsor_id']}>" if data["sponsor_id"] else "None"
        reward_delay = data["reward_delay"]

        await interaction.response.send_message(
            f"## {data['name']}\n"
            f"**Prize:** {data['prize']}\n"
            f"**Entries:** `{entries}`\n"
            f"**Winners:** `{data['winners_count']}`\n"
            f"**Status:** `{data['status']}`\n"
            f"**Sponsor:** {sponsor}\n"
            f"**Reward delay:** `{reward_delay}s`\n"
            f"**Ends:** <t:{data['end_at']}:F>",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
