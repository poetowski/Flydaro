from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_adsb_client
from app.core.exceptions import (
    CapacityClosedError,
    ConflictError,
    InsufficientFundsError,
    LicenseRequiredError,
    NotFoundError,
    RentalNotResolvedError,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.airport import Airport
from app.models.flight import TrackedFlight
from app.models.rental import Rental, RentalStatus
from app.models.user import User
from app.schemas.rental import CreateRentalRequest, RentalOut
from app.services import flight_status_service, rental_service
from app.worker.adsb_client import AdsbClient

router = APIRouter(prefix="/rentals", tags=["rentals"])


async def _refresh_flights_for(db: AsyncSession, client: AdsbClient, rentals: list[Rental]) -> None:
    """The actual reward gate: before returning any non-resolved rental,
    explicitly ask adsb.fi (live state) whether its flight has landed,
    rather than trusting the background poller's own schedule to have
    already caught it. Triggered by the player checking back in, per the
    design call: landing must be explicitly confirmed by an API call, not
    just inferred from continuous polling that may have missed its window
    (e.g. the app was asleep).
    """
    for rental in rentals:
        if rental.status == RentalStatus.RESOLVED:
            continue
        flight = await db.get(TrackedFlight, rental.tracked_flight_id)
        if flight is None or flight.status.is_resolved:
            continue
        airport = await db.get(Airport, flight.origin_airport_id)
        await flight_status_service.refresh_flight_status(db, client, flight, airport)
    await db.commit()


@router.post("", response_model=RentalOut, status_code=status.HTTP_201_CREATED)
async def create_rental(
    body: CreateRentalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Rental:
    try:
        rental = await rental_service.create_rental(
            db,
            current_user.id,
            body.tracked_flight_id,
            body.item_type_id,
            body.rental_fee_credits,
        )
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CapacityClosedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LicenseRequiredError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return rental


@router.get("/mine", response_model=list[RentalOut])
async def list_my_rentals(
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: AdsbClient = Depends(get_adsb_client),
) -> list[Rental]:
    parsed_status = None
    if status_filter is not None:
        try:
            parsed_status = RentalStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
            ) from exc
    rentals = await rental_service.list_rentals_for_user(db, current_user.id, parsed_status)
    await _refresh_flights_for(db, client, rentals)
    return rentals


@router.get("/{rental_id}", response_model=RentalOut)
async def get_rental(
    rental_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: AdsbClient = Depends(get_adsb_client),
) -> Rental:
    try:
        rental = await rental_service.get_rental_for_user(db, current_user.id, rental_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await _refresh_flights_for(db, client, [rental])
    return rental


@router.post("/{rental_id}/claim", response_model=RentalOut)
async def claim_rental(
    rental_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Rental:
    try:
        rental = await rental_service.claim_rental(db, current_user.id, rental_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RentalNotResolvedError, ConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    return rental
