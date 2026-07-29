# Flydaro

A game about renting capacity on real flights. Players spend in-game credits
to rent a small portion of a real aircraft's shared capacity -- to transport
an item (Cargo or Passenger, e.g. pineapples, fragile goods, a VIP
passenger...) -- on a real aircraft that has just taken off, sourced live
from the [OpenSky Network](https://opensky-network.org). The rental settles
based on what actually happens to that flight (does it land cleanly, how
long does it take), and pays out in credits.

Phase 1 (this repo, right now): auth, 5 fixed starter airports, live
takeoff/landing detection, a basic rental-and-settle loop, and a working
React UI. See the roadmap at the bottom for what's next (licensing/unlocks,
aircraft types, richer item economy, delay/diversion detection).

## Architecture

```
React SPA (Vite)  --HTTPS/JSON, JWT-->  FastAPI API  --\
                                                          >  Postgres
OpenSky Network  <--OAuth2, bbox polling--  Worker  -----/
```

The worker is the **only** thing that talks to OpenSky. The API and SPA only
ever read/write Postgres, which is why this scales to any number of players
on OpenSky's free tier -- polling is centralized and shared, not per-request.

- `backend/app/` -- FastAPI app (routers, services, models)
- `backend/app/worker/` -- the OpenSky poller (separate process from the API)
- `backend/alembic/` -- DB migrations, including seed data for starter
  airports and item types
- `frontend/` -- React (Vite) SPA

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for local Postgres) -- or any local Postgres 16 instance
- An [OpenSky Network](https://opensky-network.org/my-opensky) OAuth2 client
  (client ID + secret) if you want the worker to fetch real flights. Without
  it, everything else (auth, wallet, rental placement/resolution logic) still
  works -- the flight board will just stay empty since nothing populates it.

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
cp .env.example .env   # adjust JWT_SECRET, OpenSky creds, etc.

alembic upgrade head    # creates schema + seeds starter airports/item types

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### 3. Poller worker (optional without OpenSky credentials)

```bash
cd backend
source .venv/bin/activate
python -m app.worker.main
```

Runs forever, polling each active airport's bounding box on an interval
(`POLLER_INTERVAL_SECONDS`, default 45s) and writing tracked flights, state
samples, and rental settlements to Postgres.

### 4. Frontend

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

Backend tests run against an in-memory SQLite database (no live OpenSky or
Postgres needed) and cover the wallet ledger, rental lifecycle/settlement
formula, takeoff/landing detection thresholds, and the resolver's
timeout/lost-signal/landing-confirmation sweeps.

## Deployment (Neon + Render)

- **Neon**: one Postgres project. Use the *pooled* connection string for
  `DATABASE_URL` (the API's request-scoped sessions) and the *direct/unpooled*
  one for `DATABASE_URL_DIRECT` (used by the worker's long-lived process and
  by Alembic migrations).
- **Render**: one Web Service (`uvicorn app.main:app`), one Background Worker
  (`python -m app.worker.main`), one Static Site (the Vite build output).
  Run `alembic upgrade head` as a release/pre-deploy step on the web service
  only -- never from the worker, to avoid two processes racing to migrate.

## Roadmap beyond Phase 1

- **Licensing**: unlock airports beyond the 5 starters and aircraft types
  with credits/achievements.
- **Aircraft types**: join tracked flights against OpenSky's static aircraft
  metadata database for a plane-type unlock mechanic.
- **Item variety & economy tuning**: real Cargo/Passenger item roster (the
  3 items seeded today are placeholders recategorized from the original
  single-list model), differentiated risk profiles per resolution reason,
  win-streak bonuses, tunable config instead of hardcoded constants.
- **Richer resolution**: delay/diversion detection using OpenSky's historical
  batch data to build expected-duration baselines.
- **Admin/ops tooling**: poller health dashboard, manual force-resolve for
  stuck flights.

Landing/takeoff detection thresholds (`backend/app/worker/thresholds.py`) are
starting guesses -- expect to tune them from real poller logs once traffic
against the actual starter airports has been observed.
