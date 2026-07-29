from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import *  # noqa: F401,F403 register all models on Base.metadata
from app.models.airport import Airport
from app.models.cargo import CargoType
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.user import User


@pytest_asyncio.fixture
async def db():
    # Isolated in-memory SQLite per test -- fast, no network, no real Postgres
    # needed for unit-level service/logic tests. Production-only constructs
    # (JSONB, the partial unique index's WHERE clause) degrade gracefully to
    # their portable equivalents under SQLite, which is fine for this purpose.
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def user(db) -> User:
    u = User(email="player@example.com", password_hash="x", display_name="Player")
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def airport(db) -> Airport:
    a = Airport(
        icao4="EHAM",
        iata="AMS",
        name="Amsterdam Schiphol",
        city="Amsterdam",
        country="Netherlands",
        lat=52.3086,
        lon=4.7639,
        bbox_lamin=51.9586,
        bbox_lomin=4.4139,
        bbox_lamax=52.6586,
        bbox_lomax=5.1139,
        is_starter=True,
        is_active=True,
    )
    db.add(a)
    await db.flush()
    return a


@pytest_asyncio.fixture
async def cargo_type(db) -> CargoType:
    c = CargoType(
        code="PINEAPPLES",
        name="Pineapples",
        flavor_text="A crate of pineapples.",
        payout_multiplier=1.10,
        base_cost_credits=0,
        is_active=True,
    )
    db.add(c)
    await db.flush()
    return c


@pytest_asyncio.fixture
async def open_flight(db, airport) -> TrackedFlight:
    now = datetime.now(timezone.utc)
    flight = TrackedFlight(
        icao24="abc123",
        callsign="TST123",
        origin_airport_id=airport.id,
        first_seen_at=now - timedelta(minutes=1),
        first_seen_lat=airport.lat,
        first_seen_lon=airport.lon,
        first_seen_alt=300.0,
        first_seen_velocity=100.0,
        first_seen_vertical_rate=5.0,
        last_seen_at=now,
        last_seen_lat=airport.lat,
        last_seen_lon=airport.lon,
        last_seen_alt=300.0,
        last_seen_velocity=100.0,
        last_seen_vertical_rate=5.0,
        last_seen_on_ground=False,
        status=TrackedFlightStatus.AIRBORNE_OPEN,
        bets_open=True,
    )
    db.add(flight)
    await db.flush()
    return flight
