import os
import tempfile
import unittest
from unittest.mock import patch

from Presentation.API.Client.account_api_client import (
    AccountApiClient,
    AccountApiError,
)


class FakeResponse:
    def __init__(self, status_code=200, body=None, content=b"", ok=True):
        self.status_code = status_code
        self._body = body
        self.content = content
        self.ok = ok

    def json(self):
        if self._body is None:
            raise ValueError("No JSON body")
        return self._body

    def raise_for_status(self):
        if not self.ok:
            import requests

            raise requests.exceptions.HTTPError(response=self)


class AccountApiClientTests(unittest.TestCase):
    def setUp(self):
        self.client = AccountApiClient(base_url="http://test.local")
        self.client.set_employee(7)

    @patch("Presentation.API.Client.account_api_client.requests.request")
    def test_get_accounts_parses_the_api_response(self, mock_request):
        mock_request.return_value = FakeResponse(
            body=[
                {
                    "id": 1,
                    "account_number": "1001",
                    "opening_date": "2026-01-01T09:00:00",
                    "customer_id": 5,
                    "customer_name": "Negar Sadeghi",
                }
            ]
        )

        accounts = self.client.get_accounts("Negar")

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].account_number, "1001")
        self.assertEqual(accounts[0].owner_customer.get_fullname(), "Negar Sadeghi")
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["X-Employee-Id"], "7"
        )

    @patch("Presentation.API.Client.account_api_client.requests.request")
    def test_statement_decimal_values_are_preserved(self, mock_request):
        mock_request.return_value = FakeResponse(
            body={
                "account_id": 1,
                "account_number": "1001",
                "customer_id": 5,
                "customer_name": "Negar Sadeghi",
                "opening_date": "2026-01-01T09:00:00",
                "generated_at": "2026-01-05T10:00:00",
                "opening_balance": "0.00",
                "total_debits": "250.00",
                "total_credits": "1000.00",
                "closing_balance": "750.00",
                "rows": [
                    {
                        "sequence": 1,
                        "transaction_id": 10,
                        "created_at": "2026-01-02T09:00:00",
                        "transaction_type": "Deposit",
                        "description": "Transaction #10",
                        "debit": "0.00",
                        "credit": "1000.00",
                        "balance": "1000.00",
                    }
                ],
            }
        )

        statement = self.client.get_statement(1)

        self.assertEqual(str(statement.closing_balance), "750.00")
        self.assertEqual(str(statement.rows[0].credit), "1000.00")

    @patch("Presentation.API.Client.account_api_client.requests.request")
    def test_api_detail_is_shown_to_the_user(self, mock_request):
        mock_request.return_value = FakeResponse(
            status_code=403,
            body={"detail": "You do not have permission to view customer accounts."},
            ok=False,
        )

        with self.assertRaises(AccountApiError) as context:
            self.client.get_accounts()

        self.assertIn("permission", str(context.exception))

    @patch("Presentation.API.Client.account_api_client.requests.request")
    def test_connection_error_has_a_clear_message(self, mock_request):
        import requests

        mock_request.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(AccountApiError) as context:
            self.client.get_accounts()

        self.assertIn("Could not connect", str(context.exception))

    def test_client_requires_a_logged_in_employee(self):
        client = AccountApiClient(base_url="http://test.local")

        with self.assertRaises(AccountApiError):
            client.get_accounts()

    @patch("Presentation.API.Client.account_api_client.requests.request")
    def test_pdf_download_writes_the_bytes(self, mock_request):
        mock_request.return_value = FakeResponse(content=b"%PDF-1.4 test")

        file_descriptor, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(file_descriptor)
        self.addCleanup(lambda: os.path.exists(pdf_path) and os.remove(pdf_path))

        self.client.download_statement_pdf(1, pdf_path)

        with open(pdf_path, "rb") as pdf_file:
            self.assertEqual(pdf_file.read(), b"%PDF-1.4 test")


if __name__ == "__main__":
    unittest.main()
