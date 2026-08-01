from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import *  # noqa: F401,F403 register all models on Base.metadata
from app.models.aircraft import AircraftType
from app.models.aircraft_family import AircraftFamily
from app.models.airport import Airport
from app.models.crew import UserAirportCrew
from app.models.item_type import ItemCategory, ItemType
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
async def airport(db, user) -> Airport:
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
    # Every rental-lifecycle test transitively depends on this fixture --
    # granting 1 crew member here (rather than editing each test) keeps
    # create_rental's crew gate from breaking every pre-existing test.
    db.add(UserAirportCrew(user_id=user.id, airport_id=a.id, crew_count=1))
    await db.flush()
    return a


@pytest_asyncio.fixture
async def aircraft_family(db) -> AircraftFamily:
    f = AircraftFamily(
        code="A320_FAMILY",
        name="Airbus A320 Family",
        is_starter=True,
        unlock_cost_credits=0,
        is_active=True,
    )
    db.add(f)
    await db.flush()
    return f


@pytest_asyncio.fixture
async def aircraft_type(db, aircraft_family) -> AircraftType:
    t = AircraftType(
        icao_type_code="A320",
        name="Airbus A320",
        manufacturer="Airbus",
        family_id=aircraft_family.id,
        is_active=True,
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def locked_airport(db) -> Airport:
    a = Airport(
        icao4="KJFK",
        iata="JFK",
        name="John F. Kennedy Intl",
        city="New York",
        country="United States",
        lat=40.6413,
        lon=-73.7781,
        bbox_lamin=40.2913,
        bbox_lomin=-74.1281,
        bbox_lamax=40.9913,
        bbox_lomax=-73.4281,
        is_starter=False,
        is_active=False,
        unlock_cost_credits=400,
    )
    db.add(a)
    await db.flush()
    return a


@pytest_asyncio.fixture
async def locked_aircraft_family(db) -> AircraftFamily:
    f = AircraftFamily(
        code="B777_FAMILY",
        name="Boeing 777 Family",
        is_starter=False,
        unlock_cost_credits=550,
        is_active=True,
    )
    db.add(f)
    await db.flush()
    return f


@pytest_asyncio.fixture
async def locked_aircraft_type(db, locked_aircraft_family) -> AircraftType:
    t = AircraftType(
        icao_type_code="B77W",
        name="Boeing 777-300ER",
        manufacturer="Boeing",
        family_id=locked_aircraft_family.id,
        is_active=True,
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def item_type(db) -> ItemType:
    c = ItemType(
        code="PINEAPPLES",
        name="Pineapples",
        category=ItemCategory.CARGO,
        flavor_text="A crate of pineapples.",
        settlement_multiplier=1.10,
        base_cost_credits=0,
        is_active=True,
    )
    db.add(c)
    await db.flush()
    return c


@pytest_asyncio.fixture
async def open_flight(db, airport, aircraft_type) -> TrackedFlight:
    now = datetime.now(timezone.utc)
    flight = TrackedFlight(
        icao24="abc123",
        callsign="TST123",
        origin_airport_id=airport.id,
        aircraft_type_id=aircraft_type.id,
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
        capacity_open=True,
    )
    db.add(flight)
    await db.flush()
    return flight
