from __future__ import annotations

import asyncio

from githubwatcher.config import load_settings
from githubwatcher.discord_delivery import DiscordDelivery
from githubwatcher.poller import run_poller


async def async_main() -> None:
    settings = load_settings()
    discord_delivery = DiscordDelivery(settings.discord_token)

    discord_task = asyncio.create_task(discord_delivery.start())
    try:
        await run_poller(settings, discord_delivery)
    finally:
        await discord_delivery.close()
        await discord_task


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
