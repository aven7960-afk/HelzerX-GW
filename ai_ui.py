from __future__ import annotations
import discord

def sep():
    return discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)

def result_view(title: str, body: str, accent=None):
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.Container(
        discord.ui.TextDisplay("# 🤖 Helzer AI"),
        sep(),
        discord.ui.TextDisplay(f"## {title}\n\n{body}"),
        accent_colour=accent or discord.Colour.blurple(),
    ))
    return view

def error_view(body: str):
    return result_view("Action Failed", f"❌ {body}", discord.Colour.red())

class ConfirmationView(discord.ui.LayoutView):
    def __init__(self, agent, action_id: str, title: str, details: str):
        super().__init__(timeout=300)
        self.agent = agent
        self.action_id = action_id
        yes = discord.ui.Button(label="Confirm", emoji="✓", style=discord.ButtonStyle.danger,
                                custom_id=f"helzer-ai:confirm:{action_id}")
        no = discord.ui.Button(label="Cancel", emoji="✕", style=discord.ButtonStyle.secondary,
                               custom_id=f"helzer-ai:cancel:{action_id}")
        async def yes_cb(i): await agent.confirm_action(i, action_id)
        async def no_cb(i): await agent.cancel_action(i, action_id)
        yes.callback = yes_cb
        no.callback = no_cb
        row = discord.ui.ActionRow()
        row.add_item(yes); row.add_item(no)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay("# 🤖 Helzer AI"),
            sep(),
            discord.ui.TextDisplay(f"## ⚠️ {title}\n\n{details}\n\nThis action requires confirmation."),
            sep(),
            row,
            accent_colour=discord.Colour.orange(),
        ))
