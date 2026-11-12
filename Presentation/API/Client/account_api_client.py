import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests

from Common.DTOs.statement import AccountStatement, StatementRow
from Common.Entities.account import Account
from Common.Entities.customer import Customer
from Common.Enums.transaction_type import TransactionType


class AccountApiError(Exception):
    """A user-facing error returned by the banking API client."""


class AccountApiClient:
    """HTTP client for the account, statement and transaction endpoints.

    The desktop UI talks only to this client; it never opens a database
    connection or runs SQL. The API server owns the business logic and the
    data-access layer.
    """

    def __init__(self, base_url: str = None, timeout: float = 10.0):
        self.base_url = (
            base_url or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000"
        ).rstrip("/")
        self.timeout = timeout
        self.employee_id = None

    def set_employee(self, employee_id: int):
        self.employee_id = employee_id

    def clear_employee(self):
        self.employee_id = None

    def get_accounts(self, search: str = "", page: int = 1, page_size: int = 20):
        data = self._get(
            "/api/v1/accounts",
            params={"search": search, "page": page, "page_size": page_size},
        )

        try:
            return [self._to_account(item) for item in data]
        except (KeyError, TypeError, ValueError, InvalidOperation) as ex:
            raise AccountApiError(
                "The banking API returned an invalid response."
            ) from ex

    def get_statement(self, account_id: int) -> AccountStatement:
        data = self._get(f"/api/v1/accounts/{account_id}/statement")

        try:
            return self._to_statement(data)
        except (KeyError, TypeError, ValueError, InvalidOperation) as ex:
            raise AccountApiError(
                "The banking API returned an invalid response."
            ) from ex

    def download_statement_pdf(self, account_id: int, file_path: str):
        content = self._get_bytes(f"/api/v1/accounts/{account_id}/statement/pdf")

        with open(file_path, "wb") as pdf_file:
            pdf_file.write(content)

    def create_transaction(
        self, account_id: int, amount, transaction_type: TransactionType
    ):
        return self._post(
            "/api/v1/transactions",
            {
                "account_id": account_id,
                "amount": str(amount),
                "transaction_type": transaction_type.value,
            },
        )

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _get(self, path: str, params=None):
        response = self._request("GET", path, params=params)

        try:
            return response.json()
        except ValueError as ex:
            raise AccountApiError(
                "The banking API returned an invalid response."
            ) from ex

    def _get_bytes(self, path: str):
        return self._request("GET", path).content

    def _post(self, path: str, payload):
        response = self._request(
            "POST",
            path,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            return response.json()
        except ValueError as ex:
            raise AccountApiError(
                "The banking API returned an invalid response."
            ) from ex

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        headers = self._headers()
        headers.update(kwargs.pop("headers", {}))

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as ex:
            raise AccountApiError(
                "The banking API did not respond in time. Please try again."
            ) from ex
        except requests.exceptions.ConnectionError as ex:
            raise AccountApiError(
                "Could not connect to the banking API. "
                "Make sure the API server is running."
            ) from ex
        except requests.exceptions.HTTPError as ex:
            raise AccountApiError(self._error_detail(ex.response)) from ex

    def _headers(self):
        if self.employee_id is None:
            raise AccountApiError(
                "You must log in before viewing customer accounts."
            )

        return {
            "Accept": "application/json",
            "X-Employee-Id": str(self.employee_id),
        }

    @staticmethod
    def _error_detail(response) -> str:
        if response is None:
            return "The banking API rejected the request."

        try:
            body = response.json()
        except ValueError:
            body = None

        detail = body.get("detail") if isinstance(body, dict) else None
        if isinstance(detail, str) and detail:
            return detail

        if response.status_code in (401, 403):
            return "You are not authorized to perform this action."

        if response.status_code == 404:
            return "The requested record was not found."

        return "The banking API could not complete the request."

    @staticmethod
    def _to_account(item: dict) -> Account:
        customer = Customer(
            item["customer_id"],
            item.get("customer_name", ""),
            "",
        )
        return Account(
            item["id"],
            item["account_number"],
            _parse_datetime(item["opening_date"]),
            customer,
        )

    @staticmethod
    def _to_statement(item: dict) -> AccountStatement:
        rows = [
            StatementRow(
                sequence=row["sequence"],
                transaction_id=row["transaction_id"],
                created_at=_parse_datetime(row["created_at"]),
                transaction_type=row["transaction_type"],
                description=row["description"],
                debit=Decimal(str(row["debit"])),
                credit=Decimal(str(row["credit"])),
                balance=Decimal(str(row["balance"])),
            )
            for row in item.get("rows", [])
        ]

        return AccountStatement(
            account_id=item["account_id"],
            account_number=item["account_number"],
            customer_id=item["customer_id"],
            customer_name=item["customer_name"],
            opening_date=_parse_datetime(item["opening_date"]),
            generated_at=_parse_datetime(item["generated_at"]),
            opening_balance=Decimal(str(item["opening_balance"])),
            total_debits=Decimal(str(item["total_debits"])),
            total_credits=Decimal(str(item["total_credits"])),
            closing_balance=Decimal(str(item["closing_balance"])),
            rows=rows,
        )


def _parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value

    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
