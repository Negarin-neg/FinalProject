from enum import Enum


class OtpStatus(Enum):
    """Outcome of checking a submitted one-time code."""

    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"
    TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS"
    NOT_FOUND = "NOT_FOUND"
