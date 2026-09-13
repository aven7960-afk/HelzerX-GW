"""Centralised HelzerX Giveaway emoji configuration.

Use Discord custom emoji strings in .env if desired; unicode fallbacks keep the bot usable
before custom emojis are configured.
"""
import os

GIFT = os.getenv("EMOJI_GIFT", "<:ax_hosting:1541995889231532214>")
ARROW = os.getenv("EMOJI_ARROW", "<:emoji_15:1542004100974125086>")
USERS = os.getenv("EMOJI_USERS", "<:ax_hosting:1542004345095327764>")
HOST = os.getenv("EMOJI_HOST", "<:emoji_15:1542004100974125086>")
SPONSOR = os.getenv("EMOJI_SPONSOR", "<:ax_hosting:1542003775902847068>")
WINNER = os.getenv("EMOJI_WINNER", "<:ax_hosting:1541995735661285508>")
TICKET = os.getenv("EMOJI_TICKET", "<:ax_hosting:1542004286999765105>")
CLAIM = os.getenv("EMOJI_CLAIM", "<:ax_hosting:1541995889231532214>")
CHECK = os.getenv("EMOJI_CHECK", "<:ax_hosting:1542004047354134568>")
CROSS = os.getenv("EMOJI_CROSS", "<a:ax_hosting:1542003949563805856>")
CLOCK = os.getenv("EMOJI_CLOCK", "<:ax_hosting:1541995574117797960>")
