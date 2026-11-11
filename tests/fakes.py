"""In-memory doubles for the repository and SMS sender.

They let the business logic be tested without a database or network, and they
record what was stored/sent so the tests can assert on it.
"""

from hashlib import md5

from Common.Entities.employee import Employee
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
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
