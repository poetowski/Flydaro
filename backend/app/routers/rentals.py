from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CapacityClosedError,
    InsufficientFundsError,
    LicenseRequiredError,
    NotFoundError,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.rental import Rental, RentalStatus
from app.models.user import User
from app.schemas.rental import CreateRentalRequest, RentalOut
from app.services import rental_service

router = APIRouter(prefix="/rentals", tags=["rentals"])


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
) -> list[Rental]:
    parsed_status = None
    if status_filter is not None:
        try:
            parsed_status = RentalStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
            ) from exc
    return await rental_service.list_rentals_for_user(db, current_user.id, parsed_status)


@router.get("/{rental_id}", response_model=RentalOut)
async def get_rental(
    rental_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Rental:
    try:
        return await rental_service.get_rental_for_user(db, current_user.id, rental_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
