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
Browser  --HTTPS/JSON, JWT-->  FastAPI (serves API + built React SPA)  --\
                                          |                                >  Postgres
                                          `--OAuth2, bbox polling-->  OpenSky Network
```

In production this is **one process**: FastAPI serves the JSON API, mounts
the built SPA as static files (with an SPA fallback for client-side
routing), and runs the OpenSky poller as an in-process background task --
see `app/main.py`. Locally, the poller and frontend instead run as
separate processes (see Local setup below) since that's more convenient
for development; the poller logic itself (`app/worker/poller.py`) is
shared code either way, so there's no live-data path that's ever mocked.

- `backend/app/` -- FastAPI app (routers, services, models)
- `backend/app/worker/` -- the OpenSky poller (`run_forever`, shared by the
  standalone worker process and the API's in-process background task)
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
(`POLLER_INTERVAL_SECONDS`, default 60s) and writing tracked flights, state
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

`render.yaml` at the repo root is a [Render Blueprint](https://render.com/docs/blueprint-spec)
defining a **single** service, `flydaro`. Its build step builds the
frontend (`frontend/dist`) before installing the Python package; at
runtime, `app/main.py` mounts that build as static files (with an SPA
fallback for client-side routing) alongside the JSON API, and runs the
OpenSky poller as an in-process background task. Postgres itself is
**not** provisioned by Render -- it lives in Neon.

Why one service: Render's free plan has no Background Worker type and no
`preDeployCommand`, and a separate free Static Site added nothing (it's
free either way) while splitting the frontend build into its own service
turned out to be the thing repeatedly breaking (see the npm/Vite notes in
`render.yaml`'s buildCommand comment) -- one service is simpler and every
part of it fits the free tier.

Trade-off: a free web service spins down after 15 minutes idle and
cold-starts (~1 min) on the next request -- that now affects the
frontend's first load too, not just the API, and the poller pauses while
asleep. Ping `/health` periodically from a free external uptime service if
you want it to stay warmer.

### 1. Neon

Create one Postgres project. Neon gives you two connection strings:

- **Pooled** (has `-pooler` in the hostname) -> `DATABASE_URL`, used by the
  API's request-scoped sessions.
- **Direct/unpooled** -> `DATABASE_URL_DIRECT`, used by Alembic migrations
  and by the poller (see below), both of which hold long-lived connections
  that shouldn't go through Neon's pooler.

Neon's dashboard copies these with `?sslmode=require&channel_binding=require`,
neither of which asyncpg (our driver) understands -- strip both and use
`?ssl=require` instead before pasting either string in, or the connection
will fail outright.

### 2. Render

In the Render dashboard, **New > Blueprint**, point it at this repo. It
prompts for every `sync: false` env var on `flydaro`: `DATABASE_URL`,
`DATABASE_URL_DIRECT`, `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET`. No
mocked/synthetic flight data anywhere in this codebase -- without valid
OpenSky credentials the service still runs, but every poll fails and the
board just stays empty. `JWT_SECRET` is auto-generated by Render
(`generateValue: true`) -- no need to set it yourself. `CORS_ALLOWED_ORIGINS`
and `VITE_API_BASE_URL` are fixed defaults in `render.yaml` and don't need
touching -- same-origin serving means CORS is basically moot in production.

### 3. Paid upgrade path (always-on poller, split services)

Once on a paid plan, you can split the poller back out into a dedicated,
always-on Background Worker instead of the in-process one: uncomment the
`flydaro-poller` block in `render.yaml`, remove `RUN_POLLER_IN_API` from
`flydaro`, and replace `RUN_MIGRATIONS_ON_STARTUP` with
`preDeployCommand: alembic upgrade head` on `flydaro` (this is the
*only* service that should run migrations, to avoid it racing the worker).
The worker needs its own
`DATABASE_URL_DIRECT`/`OPENSKY_CLIENT_ID`/`OPENSKY_CLIENT_SECRET` filled in.
You could similarly split the frontend back out to its own Static Site if
you want CDN-level serving/no cold-start on the frontend specifically --
just revert the SPA mount in `app/main.py` and give the static site its own
`buildCommand`/`staticPublishPath` as before.

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
