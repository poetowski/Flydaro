# Flydaro

A game about renting capacity on real flights. Players spend in-game credits
to rent a small portion of a real aircraft's shared capacity -- to transport
an item (Cargo or Passenger, e.g. fruit and vegetables, electronics, a VIP
passenger...) -- on a real aircraft that has just taken off, sourced live
from [adsb.fi](https://adsb.fi), a free, unauthenticated community ADS-B
feed. The rental settles based on what actually happens to that flight (does
it land cleanly, how long does it take), and pays out in credits, which the
player then explicitly claims.

Airports and aircraft families (grouped real aircraft types, e.g. "Airbus
A320 Family") are licensed progressively: everyone starts with 5 free
airports and 2 free aircraft families, and unlocks more with credits via the
Licenses page.

## Architecture

```
Browser  --HTTPS/JSON, JWT-->  FastAPI (serves API + built React SPA)  --\
                                          |                                >  Postgres
                                          `--ad hoc, no auth-->  adsb.fi
```

**No background worker or poller of any kind.** adsb.fi is only ever called
ad hoc, from within a real user request: loading the flight board
(`GET /flights/board`) discovers new takeoffs and advances/resolves existing
tracked flights near the airports being viewed; checking rentals
(`GET /rentals/mine`, `GET /rentals/{id}`) asks adsb.fi to confirm whether
that specific flight has landed. See `app/services/flight_discovery_service.py`
and `flight_status_service.py`. In production this is **one process**:
FastAPI serves the JSON API and mounts the built SPA as static files (with an
SPA fallback for client-side routing) -- see `app/main.py`.

- `backend/app/` -- FastAPI app (routers, services, models)
- `backend/app/worker/` -- pure logic modules used by the ad-hoc services
  above: `adsb_client.py` (the only module that talks to adsb.fi),
  `tracker.py` (takeoff/landing detection, aircraft-type resolution),
  `thresholds.py` (tunable constants)
- `backend/alembic/` -- DB migrations, including seed data for starter
  airports, aircraft families, and item types
- `frontend/` -- React (Vite) SPA

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for local Postgres) -- or any local Postgres 16 instance

No API credentials needed anywhere -- adsb.fi is free and unauthenticated.

## Local setup

### 1. Database

```bash
docker compose up -d
```

This starts Postgres on `localhost:5432` with user/password/db all set to
`flydaro` (matching the backend's `.env.example` defaults).

### 2. Backend API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # adjust JWT_SECRET, etc.

alembic upgrade head    # creates schema + seeds starter airports/aircraft families/item types

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_API_BASE_URL, defaults to localhost:8000
npm run dev
```

Open `http://localhost:5173`, sign up, and you'll land on the dashboard with
a starting balance.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Backend tests run against an in-memory SQLite database (no live network or
Postgres needed) and cover the wallet ledger, rental lifecycle/settlement
formula, takeoff/landing detection thresholds, and the ad-hoc discovery/
status services' timeout/lost-signal/landing-confirmation logic.

## Deployment (Neon + Render)

`render.yaml` at the repo root is a [Render Blueprint](https://render.com/docs/blueprint-spec)
defining a **single** service, `flydaro`. Its build step builds the
frontend (`frontend/dist`) before installing the Python package; at
runtime, `app/main.py` mounts that build as static files (with an SPA
fallback for client-side routing) alongside the JSON API. Postgres itself is
**not** provisioned by Render -- it lives in Neon.

Why one service: Render's free plan has no Background Worker type and no
`preDeployCommand`, and a separate free Static Site added nothing (it's
free either way) while splitting the frontend build into its own service
turned out to be the thing repeatedly breaking (see the npm/Vite notes in
`render.yaml`'s buildCommand comment) -- one service is simpler and every
part of it fits the free tier.

Trade-off: a free web service spins down after 15 minutes idle and
cold-starts (~1 min) on the next request -- but since there's no background
task of any kind, a cold start just adds latency to whichever request wakes
the service; it never causes missed flights or stuck rentals the way a
background poller would have.

### 1. Neon

Create one Postgres project. Neon gives you two connection strings:

- **Pooled** (has `-pooler` in the hostname) -> `DATABASE_URL`, used by the
  API's request-scoped sessions.
- **Direct/unpooled** -> `DATABASE_URL_DIRECT`, used by Alembic migrations,
  which hold long-lived connections that shouldn't go through Neon's pooler.

Neon's dashboard copies these with `?sslmode=require&channel_binding=require`,
neither of which asyncpg (our driver) understands -- strip both and use
`?ssl=require` instead before pasting either string in, or the connection
will fail outright.

### 2. Render

In the Render dashboard, **New > Blueprint**, point it at this repo. It
prompts for every `sync: false` env var on `flydaro`: `DATABASE_URL`,
`DATABASE_URL_DIRECT`. `JWT_SECRET` is auto-generated by Render
(`generateValue: true`) -- no need to set it yourself. `CORS_ALLOWED_ORIGINS`
and `VITE_API_BASE_URL` are fixed defaults in `render.yaml` and don't need
touching -- same-origin serving means CORS is basically moot in production.

## Roadmap

- **Item variety & economy tuning**: differentiated risk profiles per
  resolution reason, win-streak bonuses, tunable config instead of
  hardcoded constants.
- **Richer resolution**: delay/diversion detection, if a suitable free data
  source is ever identified (adsb.fi, like OpenSky before it, only exposes
  live position -- no historical/scheduled-time data).
- **Admin/ops tooling**: none currently exists -- was built against the old
  poller architecture and removed when the poller was; would need to be
  redesigned around the ad-hoc call model if revisited.

Landing/takeoff detection thresholds (`backend/app/worker/thresholds.py`) are
starting guesses -- expect to tune them from real traffic against the actual
starter airports.
