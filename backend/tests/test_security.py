import pytest
from fastapi import HTTPException

from app.core.security import get_current_admin_user


async def test_get_current_admin_user_rejects_non_admin(user):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin_user(current_user=user)
    assert exc_info.value.status_code == 403


async def test_get_current_admin_user_allows_admin(db, user):
    user.is_admin = True
    await db.flush()
    result = await get_current_admin_user(current_user=user)
    assert result is user
