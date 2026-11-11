import unittest

from BusinessLogic.user_business_logic import UserBusinessLogic
from Common.Enums.error_code import ErrorCode
from tests.fakes import InMemoryEmployeeRepository


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryEmployeeRepository()
        self.repository.seed(mobile="09121234567", username="existing", password="Passw0rd@")
        self.business = UserBusinessLogic(self.repository)

    def test_existing_username_correct_password_succeeds(self):
        response = self.business.login("existing", "Passw0rd@")
        self.assertTrue(response.success)

    def test_existing_username_wrong_password_does_not_go_to_registration(self):
        response = self.business.login("existing", "WrongPassw0rd@")
        self.assertFalse(response.success)
        # Crucially NOT the ACCOUNT_NOT_FOUND marker, so the UI stays on login.
        self.assertNotEqual(response.error_code, ErrorCode.ACCOUNT_NOT_FOUND)
        self.assertEqual(response.message, "Invalid username or password")

    def test_missing_username_reports_account_not_found(self):
        response = self.business.login("nobody", "Passw0rd@")
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, ErrorCode.ACCOUNT_NOT_FOUND)
        self.assertIn("ثبت‌نام", response.message)


if __name__ == "__main__":
    unittest.main()
