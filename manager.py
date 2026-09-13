from __future__ import annotations

import asyncio
import random

import discord
from discord.ext import tasks

from db import Database
from emoji import CHECK, CROSS
from ui import ClaimView, GiveawayView, TicketView, WinnerView
from utils import now_ts


class GiveawayManager:
    def __init__(self, bot: discord.Client, db: Database, settings):
        self.bot = bot
        self.db = db
        self.settings = settings
        self.cache: dict[int, dict] = {}
        self.entry_cache: dict[int, int] = {}

    async def load_active(self) -> None:
        active = await self.db.fetchall("SELECT * FROM giveaways WHERE status='active'")
        for row in active:
            row["winner_image_url"] = self.settings.winner_image_url
            self.cache[row["id"]] = row
            self.entry_cache[row["id"]] = await self.db.entry_count(row["id"])

        # Re-register all persistent claim/ticket buttons after a restart.
        winners = await self.db.fetchall(
            "SELECT * FROM winners WHERE reward_status IN ('pending', 'ticket_open')"
        )
        for row in winners:
            giveaway = await self.db.fetchone(
                "SELECT * FROM giveaways WHERE id=?", (row["giveaway_id"],)
            )
            if not giveaway:
                continue
            giveaway["winner_image_url"] = self.settings.winner_image_url
            if row["reward_status"] == "pending":
                self.bot.add_view(ClaimView(self, row["giveaway_id"], row["user_id"]))
            elif row["reward_status"] == "ticket_open":
                # Persistent custom_id handlers can be registered before the channel
                # itself is cached; Discord will route future button interactions to it.
                self.bot.add_view(TicketView(self, giveaway, row["user_id"]))

    def start(self) -> None:
        if not self.finalizer.is_running():
            self.finalizer.start()

    async def create(
        self,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        name: str,
        prize: str,
        host_id: int,
        sponsor_id: int | None,
        winners_count: int,
        end_at: int,
        image_url: str | None,
        reward: str | None,
        reward_delay: int,
        ticket_category_id: int | None,
        required_role_id: int | None,
    ) -> int:
        giveaway_id = await self.db.insert(
            """
            INSERT INTO giveaways
            (guild_id, channel_id, message_id, name, prize, host_id, sponsor_id,
             winners_count, end_at, image_url, reward, reward_delay,
             ticket_category_id, required_role_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                guild_id, channel_id, message_id, name, prize, host_id, sponsor_id,
                winners_count, end_at, image_url, reward, reward_delay,
                ticket_category_id, required_role_id, now_ts(),
            ),
        )
        row = await self.db.fetchone("SELECT * FROM giveaways WHERE id=?", (giveaway_id,))
        row["winner_image_url"] = self.settings.winner_image_url
        self.cache[giveaway_id] = row
        self.entry_cache[giveaway_id] = 0
        return giveaway_id

    async def enter_giveaway(self, interaction: discord.Interaction, giveaway_id: int) -> None:
        data = self.cache.get(giveaway_id)
        if not data or data["status"] != "active" or data["end_at"] <= now_ts():
            await interaction.response.send_message(
                f"{CROSS} This giveaway has already ended.", ephemeral=True
            )
            return

        if not interaction.guild:
            await interaction.response.send_message(
                f"{CROSS} Giveaways can only be entered inside a server.", ephemeral=True
            )
            return

        if data["required_role_id"]:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                try:
                    member = await interaction.guild.fetch_member(interaction.user.id)
                except discord.HTTPException:
                    member = None
            if not member or data["required_role_id"] not in {r.id for r in member.roles}:
                await interaction.response.send_message(
                    f"{CROSS} You do not have the required role to enter this giveaway.",
                    ephemeral=True,
                )
                return

        added = await self.db.add_entry(giveaway_id, interaction.user.id, now_ts())
        if not added:
            await interaction.response.send_message(
                f"{CROSS} You are already entered in this giveaway.", ephemeral=True
            )
            return

        self.entry_cache[giveaway_id] = self.entry_cache.get(giveaway_id, 0) + 1
        await interaction.response.send_message(
            f"{CHECK} You entered the giveaway.", ephemeral=True
        )
        await self.refresh_message(giveaway_id)

    async def refresh_message(self, giveaway_id: int) -> None:
        data = self.cache.get(giveaway_id)
        if not data:
            return
        channel = self.bot.get_channel(data["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            message = await channel.fetch_message(data["message_id"])
            await message.edit(
                view=GiveawayView(
                    self, giveaway_id, disabled=data["status"] != "active"
                )
            )
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    @tasks.loop(seconds=5)
    async def finalizer(self) -> None:
        due = await self.db.fetchall(
            "SELECT id FROM giveaways WHERE status='active' AND end_at <= ?",
            (now_ts(),),
        )
        for row in due:
            try:
                await self.finish(row["id"])
            except Exception:
                # One broken giveaway must not stop the scheduler for every other giveaway.
                import logging
                logging.getLogger("helzerx-giveaway").exception(
                    "Failed to finalize giveaway %s", row["id"]
                )

    @finalizer.before_loop
    async def before_finalizer(self) -> None:
        await self.bot.wait_until_ready()

    async def finish(self, giveaway_id: int) -> list[int]:
        data = await self.db.fetchone("SELECT * FROM giveaways WHERE id=?", (giveaway_id,))
        if not data or data["status"] != "active":
            return []

        # Claim the giveaway atomically at the application level before doing Discord I/O.
        await self.db.execute(
            "UPDATE giveaways SET status='ended' WHERE id=? AND status='active'",
            (giveaway_id,),
        )
        data = await self.db.fetchone("SELECT * FROM giveaways WHERE id=?", (giveaway_id,))
        if not data or data["status"] != "ended":
            return []

        entries = await self.db.fetchall(
            "SELECT user_id FROM entries WHERE giveaway_id=? AND valid=1",
            (giveaway_id,),
        )
        candidates = [int(row["user_id"]) for row in entries]
        winners = (
            random.sample(candidates, min(data["winners_count"], len(candidates)))
            if candidates
            else []
        )

        self.cache.pop(giveaway_id, None)
        self.entry_cache.pop(giveaway_id, None)

        if winners:
            ready_at = now_ts() + int(data["reward_delay"])
            claim_expires = ready_at + int(self.settings.claim_window_seconds)
            for position, user_id in enumerate(winners, start=1):
                await self.db.execute(
                    """
                    INSERT OR REPLACE INTO winners
                    (giveaway_id, user_id, position, claimed, claim_expires,
                     reward_ready_at, reward_status, dm_sent)
                    VALUES (?, ?, ?, 0, ?, ?, 'pending', 0)
                    """,
                    (giveaway_id, user_id, position, claim_expires, ready_at),
                )

        data["winner_image_url"] = self.settings.winner_image_url

        channel = self.bot.get_channel(data["channel_id"])
        if isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(data["message_id"])
                # Rebuild the view from a temporary ended-state cache.
                self.cache[giveaway_id] = dict(data)
                self.cache[giveaway_id]["status"] = "ended"
                self.entry_cache[giveaway_id] = len(candidates)
                await message.edit(
                    view=GiveawayView(self, giveaway_id, disabled=True)
                )
                await channel.send(
                    view=WinnerView(self, data, winners),
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
            finally:
                self.cache.pop(giveaway_id, None)
                self.entry_cache.pop(giveaway_id, None)

        for user_id in winners:
            self.bot.add_view(ClaimView(self, giveaway_id, user_id))
            await self.send_winner_dm(data, user_id)

        return winners

    async def send_winner_dm(self, giveaway: dict, user_id: int) -> None:
        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            await user.send(
                view=ClaimView(self, giveaway["id"], user_id),
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            await self.db.execute(
                "UPDATE winners SET dm_sent=1 WHERE giveaway_id=? AND user_id=?",
                (giveaway["id"], user_id),
            )
        except (discord.Forbidden, discord.HTTPException):
            return

    async def claim_reward(
        self, interaction: discord.Interaction, giveaway_id: int, user_id: int
    ) -> None:
        if interaction.user.id != user_id:
            await interaction.response.send_message(
                f"{CROSS} This reward belongs to another user.", ephemeral=True
            )
            return

        winner = await self.db.fetchone(
            "SELECT * FROM winners WHERE giveaway_id=? AND user_id=?",
            (giveaway_id, user_id),
        )
        giveaway = await self.db.fetchone(
            "SELECT * FROM giveaways WHERE id=?", (giveaway_id,)
        )
        if not winner or not giveaway:
            await interaction.response.send_message(
                f"{CROSS} Reward record not found.", ephemeral=True
            )
            return

        if winner["ticket_channel_id"]:
            await interaction.response.send_message(
                f"{CHECK} Your reward ticket has already been created.", ephemeral=True
            )
            return

        if winner["reward_status"] != "pending":
            await interaction.response.send_message(
                f"{CROSS} This reward is no longer claimable.", ephemeral=True
            )
            return

        current = now_ts()
        ready_at = winner.get("reward_ready_at") or 0
        if ready_at > current:
            await interaction.response.send_message(
                f"{CHECK} Your reward unlocks <t:{ready_at}:R>.", ephemeral=True
            )
            return

        if winner.get("claim_expires") and winner["claim_expires"] < current:
            await interaction.response.send_message(
                f"{CROSS} The reward claim window has expired. Ask staff for a reroll.",
                ephemeral=True,
            )
            return

        guild = self.bot.get_guild(giveaway["guild_id"])
        if not guild:
            await interaction.response.send_message(
                f"{CROSS} The giveaway server is unavailable.", ephemeral=True
            )
            return

        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                await interaction.response.send_message(
                    f"{CROSS} I could not find you in the giveaway server.",
                    ephemeral=True,
                )
                return

        me = guild.me
        if me is None:
            await interaction.response.send_message(
                f"{CROSS} Bot member information is unavailable.", ephemeral=True
            )
            return

        category_id = giveaway["ticket_category_id"] or self.settings.ticket_category_id
        category = self.bot.get_channel(category_id) if category_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
        }

        safe_name = "".join(
            c for c in member.display_name.lower() if c.isalnum() or c in "-_"
        )[:20] or "winner"

        try:
            channel = await guild.create_text_channel(
                f"reward-{safe_name}",
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"Giveaway reward ticket for {member} ({giveaway_id})",
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                f"{CROSS} I could not create the private reward ticket. Check my Manage Channels permission.",
                ephemeral=True,
            )
            return

        await self.db.execute(
            """
            UPDATE winners
            SET claimed=1, ticket_channel_id=?, reward_status='ticket_open'
            WHERE giveaway_id=? AND user_id=? AND ticket_channel_id IS NULL
            """,
            (channel.id, giveaway_id, user_id),
        )

        ticket_view = TicketView(self, giveaway, user_id)
        self.bot.add_view(ticket_view)
        try:
            await channel.send(
                view=ticket_view,
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException:
            await self.db.execute(
                "UPDATE winners SET claimed=0, ticket_channel_id=NULL, reward_status='pending' WHERE giveaway_id=? AND user_id=?",
                (giveaway_id, user_id),
            )
            try:
                await channel.delete(reason="Failed to initialize giveaway reward ticket")
            except discord.HTTPException:
                pass
            await interaction.response.send_message(
                f"{CROSS} The reward ticket could not be initialized. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{CHECK} Your reward ticket has been created: {channel.mention}",
            ephemeral=True,
        )

    async def close_ticket(
        self, interaction: discord.Interaction, giveaway_id: int, user_id: int
    ) -> None:
        if not interaction.guild or not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                f"{CROSS} You need Manage Channels to close this ticket.",
                ephemeral=True,
            )
            return

        await self.db.execute(
            "UPDATE winners SET reward_status='closed' WHERE giveaway_id=? AND user_id=?",
            (giveaway_id, user_id),
        )
        await interaction.response.send_message(f"{CHECK} Ticket closed.", ephemeral=True)
        await asyncio.sleep(2)
        if interaction.channel:
            try:
                await interaction.channel.delete(reason="Giveaway reward ticket closed")
            except discord.HTTPException:
                pass
