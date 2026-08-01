from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.leaderboard import LeaderboardEntryOut
from app.services.wallet_service import credit_bracket, get_leaderboard

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
