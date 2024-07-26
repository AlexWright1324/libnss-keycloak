import os
import asyncio

from .env import Config, getConfig
from .client import ClientContext


async def startServer(config: Config):
    ctx = ClientContext(config)
    asyncio.create_task(ctx.updater())

    service = await asyncio.start_unix_server(ctx.handler, config.service.socketPath)

    print(f"Listening at {config.service.socketPath}")

    try:
        await service.serve_forever()
    except asyncio.CancelledError:
        print("Service shutting down...")
        os.unlink(config.service.socketPath)


def main():
    config = getConfig()

    try:
        os.unlink(config.service.socketPath)
    except OSError:
        if os.path.exists(config.service.socketPath):
            raise Exception(
                f"Failed to unlink {config.service.socketPath}, socket already running?"
            )

    asyncio.run(startServer(config))


# Debugging: python -m app.service
if __name__ == "__main__":
    main()
