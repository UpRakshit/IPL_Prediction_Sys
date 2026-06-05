class AppError(Exception):
    """Base application error that can be mapped to an HTTP response."""

    status_code = 500
    message = "Internal server error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class ProviderNotConfiguredError(AppError):
    status_code = 503
    message = "Live cricket provider is not configured"


class ProviderError(AppError):
    status_code = 502
    message = "Live cricket provider request failed"


class NotFoundError(AppError):
    status_code = 404
    message = "Resource not found"
