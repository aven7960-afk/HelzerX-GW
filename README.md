# HelzerX Giveaway

A Discord giveaway bot built with **discord.py 2.6.4** and the official **Discord Components V2** API.

The giveaway card uses real `LayoutView`, `Container`, `TextDisplay`, `Separator`, `MediaGallery`, and `ActionRow` components. The separator is Discord's official V2 `Separator` component — there are no fake `━━━━` text lines.

## Features

- Official Discord Components V2 giveaway UI.
- Real V2 `Separator` components.
- Sponsor row is omitted completely when no sponsor is selected.
- Configurable global giveaway/winner images.
- Per-giveaway image override.
- Live entry count updates.
- Required role support.
- Automatic end processing every few seconds.
- Random winner selection.
- Beautiful V2 winner announcement with actual Discord mentions.
- Winner DMs with a persistent Claim Reward button.
- Configurable reward delay.
- Configurable claim window.
- Private reward ticket channels.
- Staff-only Close Ticket action.
- Persistent SQLite database.
- Persistent giveaway/claim/ticket interactions across bot restarts.
- `/giveaway create`
- `/giveaway end`
- `/giveaway reroll`
- `/giveaway info`
- Docker deployment.
- Central emoji configuration in `emoji.py`.

## 1. Create the Discord application

In the Discord Developer Portal:

1. Create/open your bot application.
2. Go to **Bot** and copy the bot token.
3. Enable **Server Members Intent** under Privileged Gateway Intents.
4. Keep the token private. Never commit `.env`.

The bot needs at least these server permissions:

- View Channels
- Send Messages
- Read Message History
- Manage Channels
- Use Application Commands

`Manage Channels` is required for private reward tickets.

## 2. Invite the bot

Use an OAuth2 bot invite with these scopes:

- `bot`
- `applications.commands`

Select the permissions listed above.

If you use a restricted category/channel, make sure the bot can view and send messages there too.

## 3. Local installation

Requires Python 3.11+; Python 3.12 is recommended.

```bash
git clone https://github.com/aven7960-afk/HelzerX-Giveaway.git
cd HelzerX-Giveaway

python -m venv .venv
```

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually if `cp` is unavailable.

Open `.env` and set:

```env
DISCORD_TOKEN=YOUR_BOT_TOKEN
```

Optional image:

```env
GIVEAWAY_IMAGE_URL=https://your-public-image-url.example/giveaway.png
WINNER_IMAGE_URL=https://your-public-image-url.example/winner.png
```

Run:

```bash
python main.py
```

Keep the process running.

## 4. Docker / VPS installation

Upload or clone the project onto the VPS:

```bash
git clone https://github.com/aven7960-afk/HelzerX-Giveaway.git
cd HelzerX-Giveaway
```

Create the environment file:

```bash
cp .env.example .env
nano .env
```

Set at minimum:

```env
DISCORD_TOKEN=YOUR_BOT_TOKEN
```

Build and start:

```bash
docker compose up -d --build
```

Check logs:

```bash
docker compose logs -f
```

Check status:

```bash
docker compose ps
```

Restart after changes:

```bash
docker compose up -d --build
```

Stop:

```bash
docker compose down
```

The SQLite database is stored in the Docker volume `giveaway-data`, so it survives container recreation.

## 5. First slash-command sync

For normal production use, leave:

```env
SYNC_GUILD_ID=
```

Commands are then synced globally. Discord can take some time to propagate global application commands.

For a test server, set its ID:

```env
SYNC_GUILD_ID=123456789012345678
```

Restart the bot. The commands will sync directly to that guild and normally appear much faster.

After testing, remove the value and restart if you want global registration.

## 6. Create a giveaway

Example:

```text
/giveaway create
name: Nitro Drop
prize: Discord Nitro
duration: 2h
winners: 2
```

Optional:

```text
sponsor: @Sponsor
image_url: https://example.com/giveaway.png
reward: Staff will deliver the Nitro code in the ticket.
reward_delay: 30m
ticket_category: Giveaway Tickets
required_role: @Members
```

### Duration examples

```text
30s
30m
2h
3d
1d12h
1w
```

## 7. How the reward flow works

1. Giveaway reaches its end time.
2. The scheduler selects the winners.
3. The original giveaway button is disabled.
4. A V2 winner announcement is posted.
5. Each winner receives a DM.
6. If a reward delay is configured, Claim Reward remains locked until that time.
7. Once available, the winner presses Claim Reward.
8. The bot creates a private reward ticket.
9. The winner and bot can see the ticket.
10. Staff with Manage Channels can close the ticket.

Winner claim records and active giveaway data are stored in SQLite, so the bot can recover after a restart.

## 8. Important image requirement

`MediaGallery` accepts a public HTTP/HTTPS URL. Use a direct image URL that Discord can retrieve.

Good examples are direct `.png`, `.jpg`, `.jpeg`, `.webp`, or CDN image URLs.

Do not use a private/local phone path such as:

```text
C:\Users\...
/storage/emulated/0/...
```

## 9. Troubleshooting

### Slash commands are missing

- Confirm the bot was invited with `applications.commands`.
- If using `SYNC_GUILD_ID`, confirm it is the correct server ID.
- Restart the bot.
- Check:

```bash
docker compose logs -f
```

### Giveaway message cannot be sent

Make sure the bot can:

- View the channel
- Send Messages
- Read Message History
- Use Application Commands

### Reward ticket cannot be created

The bot needs:

- Manage Channels
- View Channel
- Send Messages
- Read Message History

Also make sure the selected ticket category is accessible to the bot.

### Required role does not work

Make sure Server Members Intent is enabled in the Developer Portal and that the bot can see members in the server.

### Bot restarts and giveaways still exist

Do not delete `data/giveaway.db` locally or the Docker `giveaway-data` volume.

## 10. Security

Never put the bot token in:

- GitHub
- screenshots
- public `.env` files
- Discord messages
- Dockerfiles
- README files

If the token is exposed, regenerate it immediately in the Discord Developer Portal.

## Project structure

```text
HelzerX-Giveaway/
├── main.py
├── commands.py
├── manager.py
├── ui.py
├── db.py
├── config.py
├── utils.py
├── emoji.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```
