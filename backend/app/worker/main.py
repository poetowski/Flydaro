import asyncio
import logging

from app.config import get_settings
from app.db.session import DirectSessionLocal
from app.worker.opensky_client import OpenSkyClient
from app.worker.poller import run_tick

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


async def main() -> None:
    if not settings.opensky_client_id or not settings.opensky_client_secret:
        logger.warning(
            "OPENSKY_CLIENT_ID/OPENSKY_CLIENT_SECRET are not set -- the poller "
            "will run but every request to OpenSky will fail."
        )

    client = OpenSkyClient()
    try:
        while True:
            try:
                async with DirectSessionLocal() as db:
                    await run_tick(db, client)
            except Exception:
                logger.exception("Poller tick failed")
            await asyncio.sleep(settings.poller_interval_seconds)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
