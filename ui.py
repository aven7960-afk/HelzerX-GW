from __future__ import annotations

import discord

from emoji import ARROW, GIFT, USERS, HOST, SPONSOR, WINNER, TICKET, CLAIM, CHECK, CROSS
from utils import discord_timestamp


def _separator() -> discord.ui.Separator:
    """Discord Components V2 separator (not a text line)."""
    return discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)


def _gallery(url: str | None, description: str) -> discord.ui.MediaGallery | None:
    if not url:
        return None
    gallery = discord.ui.MediaGallery()
    gallery.add_item(media=url, description=description[:1024])
    return gallery


class GiveawayView(discord.ui.LayoutView):
    def __init__(self, manager, giveaway_id: int, *, disabled: bool = False):
        super().__init__(timeout=None)
        self.manager = manager
        self.giveaway_id = giveaway_id
        self.disabled = disabled
        self._build()

    def _build(self) -> None:
        data = self.manager.cache.get(self.giveaway_id)
        if not data:
            return

        entries = self.manager.entry_cache.get(self.giveaway_id, 0)
        sponsor = data.get("sponsor_id")

        children: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"# {GIFT} {data['name']}"),
            _separator(),
            discord.ui.TextDisplay(
                f"> {ARROW} **Prize**: {data['prize']}\n"
                f"> {ARROW} **Ends**: {discord_timestamp(data['end_at'])}\n"
                f"> {HOST} **Hosted By**: <@{data['host_id']}>"
            ),
            discord.ui.TextDisplay(f"> {USERS} **Entries**: `{entries}`"),
        ]

        if sponsor:
            children.append(discord.ui.TextDisplay(f"> {SPONSOR} **Sponsored by**: <@{sponsor}>"))

        children.append(_separator())
        children.append(
            discord.ui.TextDisplay("• Click **Enter Giveaway** below to participate.")
        )

        image = _gallery(data.get("image_url"), data["name"])
        if image:
            children.append(_separator())
            children.append(image)

        children.append(_separator())

        row = discord.ui.ActionRow()
        button = discord.ui.Button(
            label="Enter Giveaway",
            emoji=GIFT,
            style=discord.ButtonStyle.primary,
            custom_id=f"giveaway:enter:{self.giveaway_id}",
            disabled=self.disabled,
        )

        async def callback(interaction: discord.Interaction) -> None:
            await self.manager.enter_giveaway(interaction, self.giveaway_id)

        button.callback = callback
        row.add_item(button)
        children.append(row)

        self.add_item(
            discord.ui.Container(*children, accent_colour=discord.Colour.blurple())
        )


class WinnerView(discord.ui.LayoutView):
    def __init__(self, manager, giveaway: dict, winner_ids: list[int]):
        super().__init__(timeout=None)
        self.manager = manager
        self.giveaway = giveaway
        self.winner_ids = winner_ids
        self._build()

    def _build(self) -> None:
        if self.winner_ids:
            mentions = "\n".join(
                f"{['🥇', '🥈', '🥉'][i] if i < 3 else WINNER} <@{uid}>"
                for i, uid in enumerate(self.winner_ids)
            )
            winner_block = f"**Winners**\n{mentions}"
        else:
            winner_block = "**Winners**\nNo eligible entries were found."

        children: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"# {WINNER} Giveaway Winners"),
            _separator(),
            discord.ui.TextDisplay(
                f"{GIFT} **{self.giveaway['name']}**\n\n"
                f"{winner_block}\n\n"
                f"{ARROW} **Prize**: {self.giveaway['prize']}\n"
                f"{HOST} **Hosted By**: <@{self.giveaway['host_id']}>"
            ),
        ]

        sponsor = self.giveaway.get("sponsor_id")
        if sponsor:
            children.append(
                discord.ui.TextDisplay(f"{SPONSOR} **Sponsored by**: <@{sponsor}>")
            )

        children.append(_separator())
        children.append(
            discord.ui.TextDisplay(
                f"{TICKET} Winners can claim their reward from the DM sent by HelzerX."
            )
        )

        image = _gallery(
            self.giveaway.get("winner_image_url") or self.giveaway.get("image_url"),
            "Giveaway winners",
        )
        if image:
            children.append(image)

        self.add_item(
            discord.ui.Container(*children, accent_colour=discord.Colour.gold())
        )


class ClaimView(discord.ui.LayoutView):
    def __init__(self, manager, giveaway_id: int, user_id: int):
        super().__init__(timeout=None)
        self.manager = manager
        self.giveaway_id = giveaway_id
        self.user_id = user_id

        text = discord.ui.TextDisplay(
            f"# {CLAIM} You Won!\n"
            f"{_claim_details(manager, giveaway_id, user_id)}"
        )
        row = discord.ui.ActionRow()
        button = discord.ui.Button(
            label="Claim Reward",
            emoji=CLAIM,
            style=discord.ButtonStyle.success,
            custom_id=f"giveaway:claim:{giveaway_id}:{user_id}",
        )

        async def callback(interaction: discord.Interaction) -> None:
            await self.manager.claim_reward(interaction, self.giveaway_id, self.user_id)

        button.callback = callback
        row.add_item(button)
        self.add_item(
            discord.ui.Container(text, _separator(), row, accent_colour=discord.Colour.green())
        )


def _claim_details(manager, giveaway_id: int, user_id: int) -> str:
    data = manager.cache.get(giveaway_id)
    if data:
        return (
            f"Congratulations, <@{user_id}>!\n\n"
            f"{GIFT} **Giveaway:** {data['name']}\n"
            f"{ARROW} **Prize:** {data['prize']}\n\n"
            "Use **Claim Reward** to open your private reward ticket."
        )
    return (
        f"Congratulations, <@{user_id}>!\n\n"
        "Use **Claim Reward** to open your private reward ticket."
    )


class TicketView(discord.ui.LayoutView):
    def __init__(self, manager, giveaway: dict, winner_id: int):
        super().__init__(timeout=None)
        self.manager = manager
        self.giveaway = giveaway
        self.winner_id = winner_id

        text = discord.ui.TextDisplay(
            f"# {TICKET} Giveaway Reward Ticket\n"
            f"**Winner:** <@{winner_id}>\n"
            f"**Giveaway:** {giveaway['name']}\n"
            f"**Prize:** {giveaway['prize']}\n\n"
            "A staff member can now process the reward."
        )
        row = discord.ui.ActionRow()
        button = discord.ui.Button(
            label="Close Ticket",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id=f"giveaway:close-ticket:{giveaway['id']}:{winner_id}",
        )

        async def callback(interaction: discord.Interaction) -> None:
            await self.manager.close_ticket(interaction, giveaway["id"], winner_id)

        button.callback = callback
        row.add_item(button)
        self.add_item(
            discord.ui.Container(text, _separator(), row, accent_colour=discord.Colour.orange())
        )
