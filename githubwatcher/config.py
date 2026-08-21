from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class DiscordTarget:
    channel_id: int | None = None
    thread_id: int | None = None
    branches: tuple[str, ...] = field(default_factory=lambda: ("main",))

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "DiscordTarget":
        channel_id = _optional_int(value.get("channel_id"))
        thread_id = _optional_int(value.get("thread_id"))
        if channel_id is None and thread_id is None:
            raise ValueError("route must include channel_id or thread_id")
        return cls(
            channel_id=channel_id,
            thread_id=thread_id,
            branches=_branches_from_mapping(value),
        )

    @property
    def discord_id(self) -> int:
        if self.thread_id is not None:
            return self.thread_id
        if self.channel_id is not None:
            return self.channel_id
        raise ValueError("target has no channel_id or thread_id")


@dataclass(frozen=True)
class Settings:
    discord_token: str
    github_token: str | None
    poll_interval_seconds: int
    poll_post_on_startup: bool
    state_file: str
    routes: dict[str, DiscordTarget]
    default_target: DiscordTarget | None


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError("DISCORD_TOKEN is required")

    routes = _load_routes()

    default_target = None
    default_thread_id = _optional_int(os.getenv("DEFAULT_THREAD_ID"))
    default_channel_id = _optional_int(os.getenv("DEFAULT_CHANNEL_ID"))
    if default_thread_id is not None or default_channel_id is not None:
        default_target = DiscordTarget(
            channel_id=default_channel_id,
            thread_id=default_thread_id,
        )

    return Settings(
        discord_token=token,
        github_token=_optional_str(os.getenv("GITHUB_TOKEN")),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        poll_post_on_startup=_truthy(os.getenv("POLL_POST_ON_STARTUP")),
        state_file=os.getenv("STATE_FILE", ".githubwatcher-state.json"),
        routes=routes,
        default_target=default_target,
    )


def _load_routes() -> dict[str, DiscordTarget]:
    routes_file = _optional_str(os.getenv("ROUTES_FILE"))
    if routes_file:
        raw = Path(routes_file).read_text(encoding="utf-8")
        source = routes_file
    else:
        raw = os.getenv("GITHUBWATCHER_ROUTES", "{}")
        source = "GITHUBWATCHER_ROUTES"

    try:
        decoded = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{source} must be valid JSON: {exc.msg} at character {exc.pos}"
        ) from exc

    if not isinstance(decoded, dict):
        raise ValueError(f"{source} must be a JSON object")

    routes: dict[str, DiscordTarget] = {}
    for repo_name, target in decoded.items():
        if not isinstance(repo_name, str):
            raise ValueError("route repo names must be strings")
        if not isinstance(target, dict):
            raise ValueError(f"route for {repo_name!r} must be an object")
        routes[repo_name.lower()] = DiscordTarget.from_mapping(target)
    return routes


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return int(text)


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _branches_from_mapping(value: dict[str, Any]) -> tuple[str, ...]:
    branches = value.get("branches")
    branch = value.get("branch")

    if branches is None and branch is None:
        return ("main",)

    if isinstance(branches, list):
        cleaned = tuple(str(item).strip() for item in branches if str(item).strip())
    elif branches is not None:
        cleaned = (str(branches).strip(),)
    else:
        cleaned = (str(branch).strip(),)

    return tuple(item for item in cleaned if item) or ("main",)


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
