from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import ConflictError, InvalidCredentialsError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.models.wallet import LedgerReason
from app.services.wallet_service import apply_ledger_entry

settings = get_settings()


async def _issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(user.id)
    raw_refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=expires_at,
        )
    )
    await db.flush()
    return access_token, raw_refresh_token


async def signup(db: AsyncSession, email: str, password: str, display_name: str) -> tuple[str, str]:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    user = User(email=email, password_hash=hash_password(password), display_name=display_name)
    db.add(user)
    await db.flush()

    await apply_ledger_entry(
        db, user.id, settings.signup_bonus_credits, LedgerReason.SIGNUP_BONUS
    )

    return await _issue_token_pair(db, user)


async def login(db: AsyncSession, email: str, password: str) -> tuple[str, str]:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    user.last_login_at = datetime.now(timezone.utc)
    return await _issue_token_pair(db, user)


async def refresh(db: AsyncSession, raw_refresh_token: str) -> tuple[str, str]:
    token_hash = hash_refresh_token(raw_refresh_token)
    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    now = datetime.now(timezone.utc)
    if (
        token_row is None
        or token_row.revoked_at is not None
        or token_row.expires_at < now
    ):
        raise InvalidCredentialsError("Refresh token is invalid or expired")

    # Rotation: revoke the used token immediately so replay is detectable.
    token_row.revoked_at = now

    user = await db.get(User, token_row.user_id)
    if user is None:
        raise InvalidCredentialsError("Refresh token is invalid or expired")

    access_token, new_raw_refresh_token = await _issue_token_pair(db, user)

    # Link rotation chain: find the just-issued token row and point the old one at it.
    new_token_hash = hash_refresh_token(new_raw_refresh_token)
    new_token_row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == new_token_hash)
    )
    if new_token_row is not None:
        token_row.replaced_by_token_id = new_token_row.id
    await db.flush()

    return access_token, new_raw_refresh_token


async def logout(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        await db.flush()
