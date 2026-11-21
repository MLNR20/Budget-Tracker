class ServiceError(Exception):
    """Base class for errors raised by the service layer (mapped to HTTP in main.py)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    pass


class BusinessRuleError(ServiceError):
    """A request that is well-formed but breaks a rule, e.g. splitting more than the budget has."""


class AuthenticationError(ServiceError):
    """Bad credentials or an invalid/expired/revoked refresh token (HTTP 401)."""
