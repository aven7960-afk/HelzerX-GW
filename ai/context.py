from __future__ import annotations

import discord


def conversation_scope(message: discord.Message) -> str:
    """Keep conversation context isolated per user and conversation surface."""
    if message.guild:
        return f"guild:{message.guild.id}:channel:{message.channel.id}:user:{message.author.id}"
    return f"dm:user:{message.author.id}"


def message_context(message: discord.Message) -> str:
    parts = [
        f"Requester ID: {message.author.id}",
        f"Current channel ID: {getattr(message.channel, 'id', 0)}",
        f"Mentioned user IDs: {[u.id for u in message.mentions]}",
        f"Mentioned channel IDs: {[c.id for c in message.channel_mentions]}",
    ]
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        replied = message.reference.resolved
        parts.append(f"Message being replied to: {replied.author.display_name}: {replied.content}")
    return "\n".join(parts)
