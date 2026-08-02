from app.core.exceptions import DomainError


def error_detail(exc: DomainError) -> dict[str, object]:
    """Builds the `detail=` payload for HTTPException from a DomainError.

    Carries both the legacy English message (`error`) and the frontend's
    localization lookup fields (`code`, `params`) so the client can render
    a translated sentence instead of the raw English text.
    """
    return {"error": str(exc), "code": exc.code, "params": exc.params}
