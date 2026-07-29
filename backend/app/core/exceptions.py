class DomainError(Exception):
    """Base class for domain/service-layer errors mapped to HTTP responses by routers."""


class InsufficientFundsError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class BettingClosedError(DomainError):
    pass


class LicenseRequiredError(DomainError):
    pass
