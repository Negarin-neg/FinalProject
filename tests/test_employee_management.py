import unittest

from BusinessLogic.user_business_logic import UserBusinessLogic
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
from tests.fakes import InMemoryEmployeeRepository


class EmployeeListTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryEmployeeRepository()
        self.admin_id = self.repository.seed(
            first_name="Admin",
            last_name="User",
            username="admin",
            mobile="09120000001",
            role=Roles.ADMINISTRATOR,
        )
        self.banker_id = self.repository.seed(
            first_name="Bank",
            last_name="User",
            username="banker",
            mobile="09120000002",
            role=Roles.BANKER,
            status=EmployeeStatus.Pending,
        )
        self.business = UserBusinessLogic(self.repository)

    def test_administrator_receives_every_employee_with_status(self):
        admin = self.repository.get_by_id(self.admin_id)

        response = self.business.get_employee_list(admin)

        self.assertTrue(response.success)
        employees = {employee.username: employee for employee in response.data}
        self.assertEqual(set(employees), {"admin", "banker"})
        self.assertEqual(employees["banker"].status, EmployeeStatus.Pending)

    def test_banker_cannot_view_the_employee_list(self):
        banker = self.repository.get_by_id(self.banker_id)

        response = self.business.get_employee_list(banker)

        self.assertFalse(response.success)
        self.assertIn("administrators", response.message)

    def test_anonymous_request_is_rejected(self):
        response = self.business.get_employee_list(None)
        self.assertFalse(response.success)


if __name__ == "__main__":
    unittest.main()
