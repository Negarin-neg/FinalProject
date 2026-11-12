import unittest

from fastapi.testclient import TestClient

import main_api
from Common.Entities.employee import Employee
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
from Common.Enums.transaction_type import TransactionType
from Presentation.API.DI.account_dependency_injection import (
    get_account_repository,
    get_employee_repository,
)
from tests.fakes import InMemoryAccountRepository, InMemoryEmployeeRepository


class AccountApiTests(unittest.TestCase):
    def setUp(self):
        self.account_repository = InMemoryAccountRepository()
        self.account = self.account_repository.add_account()
        self.account_repository.add_transaction(
            self.account.id, 1000, TransactionType.DEPOSIT
        )

        self.employee_repository = InMemoryEmployeeRepository()
        self.employee_id = self.employee_repository.seed(
            username="api.banker",
            mobile="09120000009",
            role=Roles.BANKER,
        )

        main_api.app.dependency_overrides[get_account_repository] = (
            lambda: self.account_repository
        )
        main_api.app.dependency_overrides[get_employee_repository] = (
            lambda: self.employee_repository
        )
        self.client = TestClient(main_api.app)

    def tearDown(self):
        main_api.app.dependency_overrides.clear()

    def headers(self, employee_id=None):
        return {"X-Employee-Id": str(employee_id or self.employee_id)}

    def test_account_list_requires_authentication(self):
        response = self.client.get("/api/v1/accounts")
        self.assertEqual(response.status_code, 401)

    def test_inactive_employee_is_rejected(self):
        inactive_id = self.employee_repository.seed(
            username="inactive",
            mobile="09120000008",
            status=EmployeeStatus.Deactive,
        )

        response = self.client.get(
            "/api/v1/accounts", headers=self.headers(inactive_id)
        )
        self.assertEqual(response.status_code, 401)

    def test_employee_without_a_role_is_rejected(self):
        employee = Employee(
            None,
            "No",
            "Role",
            "no.role",
            "hash",
            "09120000007",
            EmployeeStatus.Active.value,
            None,
        )
        employee_id = self.employee_repository.insert(employee)

        response = self.client.get(
            "/api/v1/accounts", headers=self.headers(employee_id)
        )
        self.assertEqual(response.status_code, 403)

    def test_account_list_returns_customer_rows(self):
        response = self.client.get(
            "/api/v1/accounts", headers=self.headers()
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["account_number"], "1001")
        self.assertEqual(body[0]["customer_name"], "Negar Sadeghi")

    def test_statement_returns_running_balance(self):
        response = self.client.get(
            f"/api/v1/accounts/{self.account.id}/statement",
            headers=self.headers(),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["rows"]), 1)
        self.assertEqual(float(body["closing_balance"]), 1000.0)

    def test_missing_account_returns_404(self):
        response = self.client.get(
            "/api/v1/accounts/999/statement", headers=self.headers()
        )
        self.assertEqual(response.status_code, 404)

    def test_pdf_endpoint_returns_a_pdf(self):
        response = self.client.get(
            f"/api/v1/accounts/{self.account.id}/statement/pdf",
            headers=self.headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_create_transaction_updates_the_statement(self):
        response = self.client.post(
            "/api/v1/transactions",
            headers=self.headers(),
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
            headers=self.headers(),
        ).json()
        self.assertEqual(float(statement["closing_balance"]), 750.0)


if __name__ == "__main__":
    unittest.main()
