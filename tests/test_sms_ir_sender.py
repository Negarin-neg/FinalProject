import unittest
from unittest.mock import patch

from DataAccess.Services.sms_ir_sender import BULK_SEND_PATH, SmsIrSender


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
            line_number="30002108030258",
            base_url="https://api.sms.ir",
            message_template="کد تأیید شما: {code}",
        )

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_sends_plain_text_message_through_bulk_endpoint(self, mock_post):
        mock_post.return_value = FakeResponse(body={"status": 1, "message": "موفق"})

        self.assertTrue(self.sender.send_otp("09121234567", "54321"))

        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith(BULK_SEND_PATH))
        self.assertEqual(kwargs["headers"]["X-API-KEY"], "dummy-key")

        payload = kwargs["json"]
        self.assertEqual(payload["lineNumber"], 30002108030258)
        self.assertEqual(payload["Mobiles"], ["09121234567"])
        self.assertIn("54321", payload["MessageText"])
        # The panel-template fields are gone - the message is plain text.
        self.assertNotIn("templateId", payload)
        self.assertNotIn("parameters", payload)

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_401_is_a_failure(self, mock_post):
        mock_post.return_value = FakeResponse(status_code=401, ok=False, body={"status": 10})
        self.assertFalse(self.sender.send_otp("09121234567", "54321"))

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_non_success_status_is_a_failure(self, mock_post):
        mock_post.return_value = FakeResponse(body={"status": 102, "message": "insufficient credit"})
        self.assertFalse(self.sender.send_otp("09121234567", "54321"))

    def test_not_configured_never_sends(self):
        sender = SmsIrSender(api_key="", line_number="")
        self.assertFalse(sender.is_configured())
        self.assertFalse(sender.send_otp("09121234567", "54321"))

    @patch("DataAccess.Services.sms_ir_sender.requests.post")
    def test_broken_template_still_delivers_the_code(self, mock_post):
        mock_post.return_value = FakeResponse(body={"status": 1})
        sender = SmsIrSender(
            api_key="dummy-key",
            line_number="30002108030258",
            message_template="no placeholder here",
        )

        self.assertTrue(sender.send_otp("09121234567", "54321"))
        self.assertEqual(mock_post.call_args.kwargs["json"]["MessageText"], "no placeholder here")


if __name__ == "__main__":
    unittest.main()
