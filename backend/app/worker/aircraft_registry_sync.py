"""One-shot sync job: downloads OpenSky's free bulk aircraft metadata CSV and
upserts only the rows that match one of our curated aircraft_types into
aircraft_registry. Intended to run as a periodic job (e.g. a weekly Render
Cron Job), separate from worker/main.py's live poll loop -- run directly via
`python -m app.worker.aircraft_registry_sync`.

The source CSV is explicitly unversioned/"as-is" (OpenSky gives no stability
guarantee on its URL, columns, or update cadence) -- this script logs
rows_seen/rows_matched/rows_upserted every run so a rows_matched == 0 result
is an obvious, alertable sign something upstream broke, not a silent no-op.
Column names (icao24, typecode, registration) are per OpenSky's documented
schema; verify against a live sample before relying on this in production,
since the exact file couldn't be fetched during development (403/503 from
this environment).
"""

import csv
import logging
from io import StringIO

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import DirectSessionLocal
from app.models.aircraft import AircraftRegistry, AircraftType

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

BATCH_SIZE = 500


async def _load_curated_type_codes(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(AircraftType.icao_type_code, AircraftType.id).where(
            AircraftType.is_active.is_(True)
        )
    )
    return {code.upper(): type_id for code, type_id in rows}


async def _upsert_batch(db: AsyncSession, batch: list[dict]) -> None:
    stmt = pg_insert(AircraftRegistry).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=["icao24"],
        set_={
            "aircraft_type_id": stmt.excluded.aircraft_type_id,
            "registration": stmt.excluded.registration,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await db.execute(stmt)


async def sync_aircraft_registry(db: AsyncSession, csv_url: str) -> dict[str, int]:
    type_code_to_id = await _load_curated_type_codes(db)
    rows_seen = 0
    rows_matched = 0
    rows_upserted = 0
    header: list[str] | None = None
    batch: list[dict] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("GET", csv_url) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                row = next(csv.reader(StringIO(line)))
                if header is None:
                    header = [column.strip().lower() for column in row]
                    continue

                record = dict(zip(header, row))
                rows_seen += 1

                typecode = (record.get("typecode") or "").strip().upper()
                icao24 = (record.get("icao24") or "").strip().lower()
                if not icao24 or typecode not in type_code_to_id:
                    continue

                rows_matched += 1
                batch.append(
                    {
                        "icao24": icao24,
                        "aircraft_type_id": type_code_to_id[typecode],
                        "registration": (record.get("registration") or "").strip() or None,
                    }
                )
                if len(batch) >= BATCH_SIZE:
                    await _upsert_batch(db, batch)
                    rows_upserted += len(batch)
                    batch.clear()

    if batch:
        await _upsert_batch(db, batch)
        rows_upserted += len(batch)

    await db.commit()

    result = {"rows_seen": rows_seen, "rows_matched": rows_matched, "rows_upserted": rows_upserted}
    if rows_matched == 0:
        logger.warning("Aircraft registry sync matched 0 rows -- likely a broken URL/schema: %s", result)
    else:
        logger.info("Aircraft registry sync complete: %s", result)
    return result


async def main() -> None:
    async with DirectSessionLocal() as db:
        await sync_aircraft_registry(db, settings.aircraft_registry_csv_url)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
