from __future__ import annotations

import asyncio

import discord

from githubwatcher.config import DiscordTarget


class DiscordDelivery:
    def __init__(self, token: str) -> None:
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        self._token = token
        self._ready = asyncio.Event()

        @self.client.event
        async def on_ready() -> None:
            self._ready.set()
            print(f"Discord connected as {self.client.user}")

    async def start(self) -> None:
        await self.client.start(self._token)

    async def close(self) -> None:
        await self.client.close()

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    async def send_commits(
        self,
        target: DiscordTarget,
        repo: str,
        branch: str,
        pusher: str,
        commits: list[dict],
        compare_url: str | None,
        repo_url: str | None,
    ) -> None:
        await self.wait_until_ready()
        destination = await self._resolve_destination(target)

        if not commits:
            await destination.send(embed=_github_embed(
                repo=repo,
                branch=branch,
                pusher=pusher,
                commits=[],
                compare_url=compare_url,
                repo_url=repo_url,
            ))
            return

        for batch in _github_commit_batches(commits):
            await destination.send(embed=_github_embed(
                repo=repo,
                branch=branch,
                pusher=pusher,
                commits=batch,
                compare_url=compare_url,
                repo_url=repo_url,
            ))

    async def _resolve_destination(self, target: DiscordTarget) -> discord.abc.Messageable:
        cached = self.client.get_channel(target.discord_id)
        if cached is not None:
            return cached

        fetched = await self.client.fetch_channel(target.discord_id)
        if not isinstance(fetched, discord.abc.Messageable):
            raise ValueError(f"Discord target {target.discord_id} cannot receive messages")
        return fetched


def _github_embed(
    repo: str,
    branch: str,
    pusher: str,
    commits: list[dict],
    compare_url: str | None,
    repo_url: str | None,
) -> discord.Embed:
    commit_count = len(commits)
    noun = "commit" if commit_count == 1 else "commits"
    embed = discord.Embed(
        title=f"[{repo}:{branch}] {commit_count} new {noun}",
        url=compare_url or repo_url,
        description="\n".join(_github_commit_line(commit) for commit in commits) or None,
        color=0x4078C0,
    )

    avatar_url = _first_avatar_url(commits)
    embed.set_author(name=pusher, icon_url=avatar_url)
    return embed


def _github_commit_line(commit: dict) -> str:
    commit_id = str(commit.get("id", ""))
    short_sha = commit_id[:7] or "unknown"
    message = _first_line(str(commit.get("message") or "(no commit message)"))
    url = commit.get("url")
    author = commit.get("author", {}).get("name") or "unknown"

    sha = f"[`{short_sha}`]({url})" if url else f"`{short_sha}`"
    return f"{sha} {message} - {author}"


def _github_commit_batches(commits: list[dict]) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_length = 0

    for commit in commits:
        line_length = len(_github_commit_line(commit)) + 1
        if current and current_length + line_length > 3900:
            batches.append(current)
            current = []
            current_length = 0

        current.append(commit)
        current_length += line_length

    if current:
        batches.append(current)

    return batches


def _first_line(value: str) -> str:
    return value.splitlines()[0][:240]


def _first_avatar_url(commits: list[dict]) -> str | None:
    for commit in commits:
        avatar_url = commit.get("author", {}).get("avatar_url")
        if avatar_url:
            return avatar_url
    return None
