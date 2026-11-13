import unittest

from fastapi.testclient import TestClient

import main_api
from Common.Enums.transaction_type import TransactionType
from Presentation.API.DI.account_dependency_injection import get_account_repository
from tests.fakes import InMemoryAccountRepository


class AccountApiTests(unittest.TestCase):
    def setUp(self):
        self.account_repository = InMemoryAccountRepository()
        self.account = self.account_repository.add_account()
        self.account_repository.add_transaction(
            self.account.id, 1000, TransactionType.DEPOSIT
        )

        main_api.app.dependency_overrides[get_account_repository] = (
            lambda: self.account_repository
        )
        self.client = TestClient(main_api.app)

    def tearDown(self):
        main_api.app.dependency_overrides.clear()

    def test_account_list_returns_customer_rows(self):
        response = self.client.get("/api/v1/accounts")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["account_number"], "1001")
        self.assertEqual(body[0]["customer_name"], "Negar Sadeghi")

    def test_statement_returns_running_balance(self):
        response = self.client.get(
            f"/api/v1/accounts/{self.account.id}/statement",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["rows"]), 1)
        self.assertEqual(float(body["closing_balance"]), 1000.0)

    def test_missing_account_returns_404(self):
        response = self.client.get("/api/v1/accounts/999/statement")
        self.assertEqual(response.status_code, 404)

    def test_pdf_endpoint_returns_a_pdf(self):
        response = self.client.get(
            f"/api/v1/accounts/{self.account.id}/statement/pdf",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_transactions_endpoint_lists_the_account_transactions(self):
        response = self.client.get(
            "/api/v1/transactions", params={"account_id": self.account.id}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["transaction_type"], "Deposit")

    def test_create_transaction_updates_the_statement(self):
        response = self.client.post(
            "/api/v1/transactions",
            json={
                "account_id": self.account.id,
                "amount": "250.00",
                "transaction_type": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        statement = self.client.get(
            f"/api/v1/accounts/{self.account.id}/statement",
        ).json()
        self.assertEqual(float(statement["closing_balance"]), 750.0)


if __name__ == "__main__":
    unittest.main()
