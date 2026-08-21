# GithubWatcher

GithubWatcher is a Python 3.10 Discord bot that watches GitHub repos through the GitHub API and posts new commits into Discord channels or Discord threads/forum posts.

It is meant for GitHub-to-Discord commit updates when you need more control, especially:

- More than 5 commits per update.
- Posting repo commit updates directly into a Discord thread.
- Routing multiple repositories from one bot.

## Setup

1. Create a Discord application and bot at <https://discord.com/developers/applications>.
2. Invite the bot to your server with permission to view and send messages in the target channels/threads.
3. Copy `.env.example` to `.env`.
4. Fill in `DISCORD_TOKEN` and `GITHUBWATCHER_ROUTES`.
5. Install dependencies:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

6. Run it:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

## How It Works

The bot asks GitHub for the newest commits every `POLL_INTERVAL_SECONDS`, remembers the newest SHA per repo/branch in `.githubwatcher-state.json`, and only posts commits it has not seen before.

This only uses the GitHub API and does not require a public URL.

Use this in `.env`:

```env
POLL_INTERVAL_SECONDS=60
GITHUB_TOKEN=
GITHUBWATCHER_ROUTES={"YOUR_NAME/YOUR_REPO_NAME":{"thread_id":"YOUR_DISCORD_THREAD_ID","branch":"main"},"YOUR_NAME/YOUR_OTHER_REPO":{"channel_id":"YOUR_DISCORD_CHANNEL_ID","branches":["main","release"]}}
```

`GITHUB_TOKEN` is optional for public repos, but recommended. It is required for private repos.

For multiple repos, a routes file is easier to read. Copy `routes.example.json` to `routes.json`, set this in `.env`, and put your repo mappings in that file:

```env
ROUTES_FILE=routes.json
GITHUBWATCHER_ROUTES=
```

On the first run, GithubWatcher seeds the current newest commit without posting old history. Set `POLL_POST_ON_STARTUP=true` if you want it to post the latest fetched commits on startup.

## Multi-Repo Routing

`GITHUBWATCHER_ROUTES` is a JSON object. Each key is `owner/repo`.

Route one repo to a normal Discord channel:

```env
GITHUBWATCHER_ROUTES={"YOUR_NAME/YOUR_REPO_NAME":{"channel_id":"YOUR_DISCORD_CHANNEL_ID","branch":"main"}}
```

Route one repo to a Discord thread or forum post:

```env
GITHUBWATCHER_ROUTES={"YOUR_NAME/YOUR_REPO_NAME":{"thread_id":"YOUR_DISCORD_THREAD_ID","branch":"main"}}
```

Route multiple repos:

```env
GITHUBWATCHER_ROUTES={"YOUR_NAME/YOUR_REPO_NAME":{"thread_id":"YOUR_DISCORD_THREAD_ID","branch":"main"},"YOUR_NAME/YOUR_OTHER_REPO":{"channel_id":"YOUR_DISCORD_CHANNEL_ID","branches":["main","release"]}}
```

You can also set `DEFAULT_CHANNEL_ID` or `DEFAULT_THREAD_ID` if unlisted repos should go to one fallback place.

## Notes

- Discord allows up to 10 embeds per message, so GithubWatcher sends commits in batches of 10.
- The bot must already have access to the destination channel or thread.
- If a private thread is used, add the bot to that thread.
