import os

import requests

from Common.Repositories.ismssender import ISmsSender

# sms.ir "Verify" (pattern) endpoint - used for OTP / verification codes.
# Docs: https://sms.ir/rest-api/  (section: ارسال VERIFY)
DEFAULT_BASE_URL = "https://api.sms.ir"
VERIFY_SEND_PATH = "/v1/send/verify"

# Template placeholder name (inside the panel template, written as #CODE#).
DEFAULT_OTP_ATTRIBUTE = "Code"

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
    """Sends OTP SMS through the sms.ir (app.sms.ir) web service.

    All secrets and account-specific values come from the environment
    (.env): SMS_API_KEY, SMS_PATTERN_CODE. Nothing is hardcoded here.
    """

    def __init__(
        self,
        api_key: str = None,
        template_id=None,
        base_url: str = None,
        otp_attribute: str = None,
    ):
        self.api_key = api_key or os.getenv("SMS_API_KEY")
        # In sms.ir this is the numeric template id, not a pattern code string.
        self.template_id = template_id if template_id is not None else os.getenv("SMS_PATTERN_CODE")
        self.base_url = (base_url or os.getenv("SMS_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.otp_attribute = otp_attribute or os.getenv("SMS_OTP_ATTRIBUTE") or DEFAULT_OTP_ATTRIBUTE

    def is_configured(self) -> bool:
        return bool(self.api_key and self.template_id)

    def send_otp(self, mobile: str, code: str) -> bool:
        if not self.is_configured():
            # Never pretend the SMS was sent when the gateway is not set up.
            print("SMS is not configured (SMS_API_KEY / SMS_PATTERN_CODE).")
            return False

        payload = {
            "mobile": self._normalize_mobile(mobile),
            "templateId": self._as_template_id(),
            "parameters": [
                {"name": self.otp_attribute, "value": str(code)},
            ],
        }

        # sms.ir authenticates with the x-api-key header.
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            response = requests.post(
                f"{self.base_url}{VERIFY_SEND_PATH}",
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as ex:
            # Network/transport failure - the provider never accepted anything.
            print(f"SMS transport error -> {ex}")
            return False

        return self._is_success(response)

    def _as_template_id(self):
        """sms.ir expects an integer templateId; tolerate a string from .env."""
        try:
            return int(str(self.template_id).strip())
        except (TypeError, ValueError):
            return self.template_id

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
