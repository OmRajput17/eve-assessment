
class AppError(Exception):
    """Base class for every error we raise deliberately."""
    
    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "Something went wrong"


    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class DomainValidationError(AppError):
    status_code = 422
    code = "validation_error"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    default_message = "You are not allowed to do this"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class InvalidStateTransition(ConflictError):
    code = "invalid_state_transition"