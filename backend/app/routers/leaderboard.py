from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.leaderboard import LeaderboardEntryOut, MyRankOut
from app.services.wallet_service import credit_bracket, get_balance, get_leaderboard, get_user_rank

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntryOut])
async def get_top_players(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardEntryOut]:
    entries = await get_leaderboard(db, limit=10)
    return [
        LeaderboardEntryOut(rank=rank, display_name=name, credit_bracket=credit_bracket(balance))
        for rank, (name, balance) in enumerate(entries, start=1)
    ]


@router.get("/me", response_model=MyRankOut)
async def get_my_rank(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MyRankOut:
    rank, total_players = await get_user_rank(db, current_user.id)
    balance = await get_balance(db, current_user.id)
    return MyRankOut(rank=rank, total_players=total_players, credit_bracket=credit_bracket(balance))
