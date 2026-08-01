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


class CapacityClosedError(DomainError):
    pass


class LicenseRequiredError(DomainError):
    pass


class RentalNotResolvedError(DomainError):
    pass


class CrewUnavailableError(DomainError):
    pass
