from fastapi import status


class DomainError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND


class ForbiddenError(DomainError):
    """403 — e.g. replay target blocked by SSRF policy."""

    status_code = status.HTTP_403_FORBIDDEN


class BadGatewayError(DomainError):
    """502 — replay target unreachable."""

    status_code = status.HTTP_502_BAD_GATEWAY
