from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import aircraft_types, airports, auth, bets, cargo, flights, licenses, wallet

settings = get_settings()

app = FastAPI(title="Flydaro API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(airports.router)
app.include_router(cargo.router)
app.include_router(aircraft_types.router)
app.include_router(licenses.router)
app.include_router(flights.router)
app.include_router(bets.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
