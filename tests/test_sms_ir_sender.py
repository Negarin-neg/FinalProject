import unittest
from unittest.mock import patch

from DataAccess.Services.sms_ir_sender import SmsIrSender, VERIFY_SEND_PATH


class FakeResponse:
    def __init__(self, status_code=200, body=None, ok=True):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.ok = ok

    def json(self):
        return self._body


class SmsIrSenderTests(unittest.TestCase):
    def setUp(self):
        self.sender = SmsIrSender(
            api_key="dummy-key",
            template_id="123456",
            base_url="https://api.sms.ir",
            otp_attribute="Code",
        )

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_uses_x_api_key_header_and_verify_endpoint(self, mock_post):
        mock_post.return_value = FakeResponse(body={"status": 1, "message": "موفق"})

        self.assertTrue(self.sender.send_otp("09121234567", "54321"))

        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith(VERIFY_SEND_PATH))
        # The 401 came from the wrong header; sms.ir needs x-api-key.
        self.assertEqual(kwargs["headers"]["x-api-key"], "dummy-key")
        self.assertNotIn("Api-Key", kwargs["headers"])

        payload = kwargs["json"]
        self.assertEqual(payload["mobile"], "09121234567")
        self.assertEqual(payload["templateId"], 123456)
        self.assertEqual(payload["parameters"], [{"name": "Code", "value": "54321"}])

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_401_is_a_failure(self, mock_post):
        mock_post.return_value = FakeResponse(status_code=401, ok=False, body={"status": 10})
        self.assertFalse(self.sender.send_otp("09121234567", "54321"))

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_non_success_status_is_a_failure(self, mock_post):
        mock_post.return_value = FakeResponse(body={"status": 113, "message": "template not found"})
        self.assertFalse(self.sender.send_otp("09121234567", "54321"))

    def test_not_configured_never_sends(self):
        sender = SmsIrSender(api_key="", template_id="")
        self.assertFalse(sender.is_configured())
        self.assertFalse(sender.send_otp("09121234567", "54321"))


if __name__ == "__main__":
    unittest.main()
