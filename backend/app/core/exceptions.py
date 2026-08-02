class DomainError(Exception):
    """Base class for domain/service-layer errors mapped to HTTP responses by routers.

    `code` is a stable, machine-readable identifier (SCREAMING_SNAKE_CASE)
    the frontend uses to look up a localized message -- independent of the
    English `str(exc)` text, which stays around for logs/anything that
    still wants the raw English message. `params` carries any dynamic
    values a localized message needs to interpolate (e.g. a credit amount).
    """

    def __init__(self, message: str, *, code: str, params: dict[str, str | int] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.params = params or {}


class InsufficientFundsError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class CapacityClosedError(DomainError):
    pass


class LicenseRequiredError(DomainError):
    pass


class RentalNotResolvedError(DomainError):
    pass


class CrewUnavailableError(DomainError):
    pass


class RentalFeeTooLowError(DomainError):
    pass
