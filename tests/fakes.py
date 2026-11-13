"""In-memory doubles for the repository and SMS sender.

They let the business logic be tested without a database or network, and they
record what was stored/sent so the tests can assert on it.
"""

from hashlib import md5
from datetime import datetime

from Common.Entities.account import Account
from Common.Entities.customer import Customer
from Common.Entities.employee import Employee
from Common.Entities.transaction import Transaction
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
from Common.Repositories.iaccount_repository import IAccountRepository
from Common.Repositories.iemployee_repository import IEmployeeRepository
from Common.Repositories.ismssender import ISmsSender


class InMemoryEmployeeRepository(IEmployeeRepository):
    def __init__(self):
        self.employees = {}
        self._next_id = 1

    def _copy(self, employee: Employee) -> Employee:
        return Employee(
            employee.id,
            employee.first_name,
            employee.last_name,
            employee.username,
            employee.password,
            employee.mobile,
            employee.status.value,
            employee.role.value if employee.role else None,
            employee.photo_path,
        )

    def get_by_username_password(self, username: str, password: str):
        for employee in self.employees.values():
            if employee.username == username and employee.password == password:
                return self._copy(employee)
        return None

    def get_by_id(self, employee_id: int):
        employee = self.employees.get(employee_id)
        return self._copy(employee) if employee else None

    def get_by_username(self, username: str):
        for employee in self.employees.values():
            if employee.username == username:
                return self._copy(employee)
        return None

    def get_by_mobile(self, mobile: str):
        for employee in self.employees.values():
            if employee.mobile == mobile:
                return self._copy(employee)
        return None

    def get_all(self):
        return [self._copy(employee) for employee in self.employees.values()]

    def insert(self, employee: Employee):
        employee.id = self._next_id
        self._next_id += 1
        self.employees[employee.id] = self._copy(employee)
        return employee.id

    def update_profile(self, employee: Employee):
        if employee.id not in self.employees:
            raise LookupError(f"Employee {employee.id} does not exist.")
        self.employees[employee.id] = self._copy(employee)

    def update_photo_path(self, employee_id: int, photo_path):
        employee = self.employees.get(employee_id)
        if employee is None:
            raise LookupError(f"Employee {employee_id} does not exist.")
        employee.photo_path = photo_path

    def seed(self, first_name="Ali", last_name="Ahmadi", mobile="09120000000",
             username="ali", password="Passw0rd@", status=EmployeeStatus.Active,
             role=Roles.BANKER):
        employee = Employee(
            None, first_name, last_name, username, md5(password.encode()).hexdigest(),
            mobile, status.value, role.value,
        )
        return self.insert(employee)


class RecordingSmsSender(ISmsSender):
    def __init__(self, succeed: bool = True):
        self.succeed = succeed
        self.sent = []  # list of (mobile, code)

    def send_otp(self, mobile: str, code: str) -> bool:
        self.sent.append((mobile, code))
        return self.succeed


class InMemoryAccountRepository(IAccountRepository):
    def __init__(self):
        self.accounts = {}
        self.transactions = {}
        self._next_account_id = 1
        self._next_transaction_id = 1

    def add_account(self, first_name="Negar", last_name="Sadeghi", account_number="1001"):
        customer = Customer(self._next_account_id, first_name, last_name)
        account = Account(
            self._next_account_id,
            account_number,
            datetime(2026, 1, 1, 9, 0),
            customer,
        )
        self.accounts[account.id] = account
        self.transactions[account.id] = []
        self._next_account_id += 1
        return account

    def add_transaction(
        self,
        account_id,
        amount,
        transaction_type,
        created_at=None,
    ):
        account = self.accounts[account_id]
        transaction = Transaction(
            self._next_transaction_id,
            amount,
            transaction_type.value,
            created_at or datetime(2026, 1, 2, 9, 0),
            account,
        )
        self.transactions[account_id].append(transaction)
        self._next_transaction_id += 1
        return transaction

    def get_account_list(self, search: str = "", page_number: int = 1, page_size: int = 20):
        accounts = list(self.accounts.values())
        search = (search or "").strip().lower()

        if search:
            accounts = [
                account
                for account in accounts
                if search in account.account_number.lower()
                or search in account.owner_customer.get_fullname().lower()
            ]

        start = (page_number - 1) * page_size
        return accounts[start:start + page_size]

    def get_account_by_id(self, account_id: int):
        return self.accounts.get(account_id)

    def get_transaction_by_account_id(self, account_id: int):
        return list(self.transactions.get(account_id, []))

    def insert_transaction(self, account_id: int, amount, transaction_type):
        if account_id not in self.accounts:
            raise LookupError(f"Account {account_id} does not exist.")

        return self.add_transaction(
            account_id,
            amount,
            transaction_type,
            datetime(2026, 2, 1, 12, 0),
        ).id


def make_banker(employee_id=1, role=Roles.BANKER, status=EmployeeStatus.Active):
    return Employee(
        employee_id,
        "Test",
        "Banker",
        "test.banker",
        md5(b"Passw0rd@").hexdigest(),
        "09120000000",
        status.value,
        role.value,
    )
