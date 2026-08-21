from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import aiohttp

from githubwatcher.config import Settings
from githubwatcher.discord_delivery import DiscordDelivery


GITHUB_API = "https://api.github.com"


async def run_poller(settings: Settings, discord_delivery: DiscordDelivery) -> None:
    state = _load_state(settings.state_file)

    async with aiohttp.ClientSession(headers=_github_headers(settings)) as session:
        await discord_delivery.wait_until_ready()
        print(f"GithubWatcher polling {len(settings.routes)} repo(s)")

        while True:
            for repo, target in settings.routes.items():
                for branch in target.branches:
                    try:
                        await _poll_repo_branch(
                            session=session,
                            settings=settings,
                            discord_delivery=discord_delivery,
                            state=state,
                            repo=repo,
                            branch=branch,
                        )
                    except Exception as exc:
                        print(f"Polling failed for {repo}@{branch}: {exc}")

            _save_state(settings.state_file, state)
            await asyncio.sleep(settings.poll_interval_seconds)


async def _poll_repo_branch(
    session: aiohttp.ClientSession,
    settings: Settings,
    discord_delivery: DiscordDelivery,
    state: dict[str, str],
    repo: str,
    branch: str,
) -> None:
    commits = await _fetch_commits(session, repo, branch)
    if not commits:
        return

    key = f"{repo}:{branch}"
    newest_sha = commits[0]["sha"]
    last_seen_sha = state.get(key)

    if last_seen_sha is None:
        state[key] = newest_sha
        if not settings.poll_post_on_startup:
            print(f"Seeded {repo}@{branch} at {newest_sha[:7]}")
            return

    new_commits = _commits_since_last_seen(commits, last_seen_sha)
    if not new_commits:
        return

    target = settings.routes[repo]
    normalized = [_normalize_commit(item) for item in reversed(new_commits)]
    compare_url = _compare_url(repo, last_seen_sha, newest_sha)
    pusher = _pusher_name(new_commits)

    await discord_delivery.send_commits(
        target=target,
        repo=repo,
        branch=branch,
        pusher=pusher,
        commits=normalized,
        compare_url=compare_url,
        repo_url=f"https://github.com/{repo}",
    )
    state[key] = newest_sha
    print(f"Posted {len(normalized)} commit(s) for {repo}@{branch}")


async def _fetch_commits(
    session: aiohttp.ClientSession,
    repo: str,
    branch: str,
) -> list[dict[str, Any]]:
    url = f"{GITHUB_API}/repos/{repo}/commits"
    params = {"sha": branch, "per_page": "50"}
    async with session.get(url, params=params) as response:
        if response.status == 404:
            raise ValueError("repo or branch was not found")
        if response.status == 403:
            raise ValueError("GitHub rate limited this bot; set GITHUB_TOKEN")
        response.raise_for_status()
        data = await response.json()
        if not isinstance(data, list):
            raise ValueError("GitHub returned an unexpected commits response")
        return data


def _commits_since_last_seen(
    commits: list[dict[str, Any]],
    last_seen_sha: str | None,
) -> list[dict[str, Any]]:
    if last_seen_sha is None:
        return commits

    unseen: list[dict[str, Any]] = []
    for item in commits:
        if item["sha"] == last_seen_sha:
            break
        unseen.append(item)
    return unseen


def _normalize_commit(item: dict[str, Any]) -> dict[str, Any]:
    commit = item.get("commit") or {}
    author = commit.get("author") or {}
    github_author = item.get("author") or {}
    return {
        "id": item.get("sha", ""),
        "message": commit.get("message") or "(no commit message)",
        "url": item.get("html_url"),
        "timestamp": author.get("date"),
        "author": {
            "name": author.get("name") or github_author.get("login") or "unknown",
            "avatar_url": github_author.get("avatar_url"),
        },
        "added": [],
        "modified": [],
        "removed": [],
    }


def _pusher_name(commits: list[dict[str, Any]]) -> str:
    names = {
        ((item.get("commit") or {}).get("author") or {}).get("name")
        for item in commits
    }
    cleaned = sorted(name for name in names if name)
    if len(cleaned) == 1:
        return cleaned[0]
    if cleaned:
        return f"{len(cleaned)} authors"
    return "GitHub"


def _compare_url(repo: str, old_sha: str | None, new_sha: str) -> str | None:
    if not old_sha:
        return f"https://github.com/{repo}/commit/{new_sha}"
    return f"https://github.com/{repo}/compare/{old_sha}...{new_sha}"


def _github_headers(settings: Settings) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GithubWatcher",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _load_state(path: str) -> dict[str, str]:
    state_path = Path(path)
    if not state_path.exists():
        return {}
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def _save_state(path: str, state: dict[str, str]) -> None:
    Path(path).write_text(
        json.dumps(state, indent=2, sort_keys=True),
        encoding="utf-8",
    )
