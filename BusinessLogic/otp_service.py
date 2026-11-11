import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from Common.Entities.pending_registration import PendingRegistration
from Common.Enums.otp_status import OtpStatus

# Security parameters. The 2-minute lifetime is a hard server-side rule -
# the UI countdown is only a courtesy.
OTP_TTL_SECONDS = 120
OTP_LENGTH = 5

RESEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_WINDOW = 4
SEND_WINDOW_SECONDS = 600
MAX_VERIFY_ATTEMPTS = 5


class OtpTicket:
    """Everything the server remembers about one pending registration."""

    def __init__(self, mobile, pending: PendingRegistration, code_hash, salt, now):
        self.mobile = mobile
        self.pending = pending
        self.code_hash = code_hash
        self.salt = salt
        self.created_at = now
        self.expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)
        self.failed_attempts = 0
        self.sends = [now]


class OtpService:
    """Generates, stores (hashed) and verifies registration OTPs.

    The service is transport-agnostic: it never talks to the SMS provider
    directly. The caller sends the returned code and reports success, so the
    OTP logic and the SMS delivery stay separate (single responsibility).

    Pending registrations live only in this in-memory store and are keyed by
    mobile number, so the database is untouched until verification passes.
    A single process (the desktop app) owns the store, which is sufficient
    for this project; swapping it for a shared cache later needs no change
    to the callers.
    """

    def __init__(self, now_provider=None):
        # `now_provider` is injectable so tests can control the clock and
        # prove expiration/resend behaviour without sleeping.
        self._now = now_provider or datetime.now
        self._tickets: dict[str, OtpTicket] = {}

    # ------------------------------------------------------------------
    # Creating a code
    # ------------------------------------------------------------------

    def start_registration(self, pending: PendingRegistration, force_resend: bool = False):
        """Stores `pending` and returns a freshly issued code.

        Returns (code, None) on success, or (None, reason) when the request
        is refused by the resend cooldown or the send limit.
        """
        now = self._now()
        existing = self._tickets.get(pending.mobile)

        if existing is not None and not force_resend:
            # First call for this submission: reuse the live ticket instead of
            # burning a new one, but still refuse if it is still on cooldown.
            cooldown = self._remaining_cooldown(existing, now)
            if cooldown > 0:
                return None, ("cooldown", cooldown)

        if existing is not None:
            recent_sends = [t for t in existing.sends if (now - t).total_seconds() < SEND_WINDOW_SECONDS]
        else:
            recent_sends = []

        if existing is not None and len(recent_sends) >= MAX_SENDS_PER_WINDOW:
            return None, ("send_limit", 0)

        code = self._generate_code()
        salt = secrets.token_hex(16)
        # A new code always wins: the previous one becomes unusable because
        # the ticket is replaced wholesale.
        ticket = OtpTicket(pending.mobile, pending, self._hash(code, salt), salt, now)
        ticket.sends = recent_sends + [now]
        self._tickets[pending.mobile] = ticket

        return code, None

    def resend(self, mobile: str):
        """Issues a new code for an existing ticket, honouring the guards."""
        now = self._now()
        existing = self._tickets.get(mobile)

        if existing is None:
            return None, ("not_found", 0)

        cooldown = self._remaining_cooldown(existing, now)
        if cooldown > 0:
            return None, ("cooldown", cooldown)

        recent_sends = [t for t in existing.sends if (now - t).total_seconds() < SEND_WINDOW_SECONDS]
        if len(recent_sends) >= MAX_SENDS_PER_WINDOW:
            return None, ("send_limit", 0)

        code = self._generate_code()
        salt = secrets.token_hex(16)

        existing.code_hash = self._hash(code, salt)
        existing.salt = salt
        existing.created_at = now
        existing.expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)
        existing.failed_attempts = 0
        existing.sends = recent_sends + [now]

        return code, None

    # ------------------------------------------------------------------
    # Checking a code
    # ------------------------------------------------------------------

    def verify(self, mobile: str, code: str):
        """Returns an OtpStatus. On VERIFIED the caller reads take_pending()."""
        now = self._now()
        ticket = self._tickets.get(mobile)

        if ticket is None:
            return OtpStatus.NOT_FOUND

        if now >= ticket.expires_at:
            return OtpStatus.EXPIRED

        if ticket.failed_attempts >= MAX_VERIFY_ATTEMPTS:
            return OtpStatus.TOO_MANY_ATTEMPTS

        if not hmac.compare_digest(self._hash(code or "", ticket.salt), ticket.code_hash):
            ticket.failed_attempts += 1
            if ticket.failed_attempts >= MAX_VERIFY_ATTEMPTS:
                return OtpStatus.TOO_MANY_ATTEMPTS
            return OtpStatus.INVALID

        return OtpStatus.VERIFIED

    def take_pending(self, mobile: str):
        """Pops the verified ticket so a code can never be replayed."""
        ticket = self._tickets.pop(mobile, None)
        return ticket.pending if ticket is not None else None

    def remaining_seconds(self, mobile: str) -> int:
        ticket = self._tickets.get(mobile)
        if ticket is None:
            return 0
        remaining = (ticket.expires_at - self._now()).total_seconds()
        return max(0, int(remaining))

    def discard(self, mobile: str):
        self._tickets.pop(mobile, None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_code() -> str:
        # secrets, not random: the code must be unpredictable.
        return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))

    @staticmethod
    def _hash(code: str, salt: str) -> str:
        # Plaintext codes are never stored - only a salted hash.
        return hashlib.sha256(f"{salt}{code}".encode()).hexdigest()

    @staticmethod
    def _remaining_cooldown(ticket: OtpTicket, now) -> int:
        elapsed = (now - ticket.sends[-1]).total_seconds()
        remaining = RESEND_COOLDOWN_SECONDS - elapsed
        return max(0, int(remaining))
