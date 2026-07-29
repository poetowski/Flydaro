from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BettingClosedError, InsufficientFundsError, NotFoundError
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.bet import Bet, BetStatus
from app.models.user import User
from app.schemas.bet import BetOut, PlaceBetRequest
from app.services import bet_service

router = APIRouter(prefix="/bets", tags=["bets"])


@router.post("", response_model=BetOut, status_code=status.HTTP_201_CREATED)
async def place_bet(
    body: PlaceBetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Bet:
    try:
        bet = await bet_service.place_bet(
            db,
            current_user.id,
            body.tracked_flight_id,
            body.cargo_type_id,
            body.stake_credits,
        )
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BettingClosedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return bet


@router.get("/mine", response_model=list[BetOut])
async def list_my_bets(
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Bet]:
    parsed_status = None
    if status_filter is not None:
        try:
            parsed_status = BetStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
            ) from exc
    return await bet_service.list_bets_for_user(db, current_user.id, parsed_status)


@router.get("/{bet_id}", response_model=BetOut)
async def get_bet(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Bet:
    try:
        return await bet_service.get_bet_for_user(db, current_user.id, bet_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
