import os

import requests

from Common.Repositories.ismssender import ISmsSender

# sms.ir "Bulk" endpoint - the message is plain text, exactly like the class
# sample (NotificationMicroservice) sends it, so no panel template is needed.
# Docs: https://sms.ir/rest-api/
DEFAULT_BASE_URL = "https://api.sms.ir"
BULK_SEND_PATH = "/v1/send/bulk"

# Text of the OTP message. Override with SMS_OTP_MESSAGE_TEMPLATE in .env.
DEFAULT_OTP_MESSAGE_TEMPLATE = "Your verification code: {code}"

REQUEST_TIMEOUT_SECONDS = 15

# sms.ir body status 1 == success; the rest are documented error codes.
SUCCESS_STATUS = 1

# status -> short explanation, only for local logging (never shown to users
# and never containing secrets).
STATUS_MESSAGES = {
    0: "general error",
    10: "invalid web service key",
    11: "web service key disabled",
    12: "key restricted to specific IPs",
    13: "account disabled",
    14: "account suspended",
    20: "too many requests",
    101: "invalid line number",
    102: "insufficient credit",
    113: "template not found",
    114: "parameter value too long",
    116: "parameter name empty",
    119: "plan does not allow custom template",
}


class SmsIrSender(ISmsSender):
    """Sends the OTP as an ordinary text SMS through the sms.ir bulk endpoint.

    All account-specific values come from the environment (.env):
    SMS_API_KEY and SMS_LINE_NUMBER. Nothing is hardcoded here.
    """

    def __init__(
        self,
        api_key: str = None,
        line_number=None,
        base_url: str = None,
        message_template: str = None,
    ):
        self.api_key = api_key or os.getenv("SMS_API_KEY")
        self.line_number = line_number if line_number is not None else os.getenv("SMS_LINE_NUMBER")
        self.base_url = (base_url or os.getenv("SMS_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.message_template = (
            message_template or os.getenv("SMS_OTP_MESSAGE_TEMPLATE") or DEFAULT_OTP_MESSAGE_TEMPLATE
        )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.line_number)

    def send_otp(self, mobile: str, code: str) -> bool:
        if not self.is_configured():
            # Never pretend the SMS was sent when the gateway is not set up.
            print("SMS is not configured (SMS_API_KEY / SMS_LINE_NUMBER).")
            return False

        payload = {
            "lineNumber": self._as_line_number(),
            "MessageText": self._build_message(code),
            "Mobiles": [self._normalize_mobile(mobile)],
        }

        # sms.ir authenticates with the X-API-KEY header.
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }

        try:
            response = requests.post(
                f"{self.base_url}{BULK_SEND_PATH}",
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as ex:
            # Network/transport failure - the provider never accepted anything.
            print(f"SMS transport error -> {ex}")
            return False

        return self._is_success(response)

    def _build_message(self, code: str) -> str:
        try:
            return self.message_template.format(code=code)
        except (KeyError, IndexError, ValueError):
            # A mistyped template must never break the registration flow.
            return str(code)

    def _as_line_number(self):
        """sms.ir expects an integer lineNumber; tolerate a string from .env."""
        try:
            return int(str(self.line_number).strip())
        except (TypeError, ValueError):
            return self.line_number

    @staticmethod
    def _normalize_mobile(mobile: str) -> str:
        """sms.ir accepts the local 09xxxxxxxxx format; drop stray characters."""
        return "".join(ch for ch in str(mobile) if ch.isdigit())

    @staticmethod
    def _is_success(response) -> bool:
        """HTTP 2xx is not enough: the body must report status == 1."""
        if response.status_code == 401:
            print("SMS authentication failed (401): check SMS_API_KEY.")
            return False

        if not response.ok:
            print(f"SMS provider returned HTTP {response.status_code}.")
            return False

        try:
            body = response.json()
        except ValueError:
            print("SMS provider returned a non-JSON response.")
            return False

        status = body.get("status")
        if status != SUCCESS_STATUS:
            reason = STATUS_MESSAGES.get(status, body.get("message", "unknown"))
            print(f"SMS provider rejected the request (status={status}: {reason}).")
            return False

        return True
