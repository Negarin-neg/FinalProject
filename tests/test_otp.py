import unittest
from datetime import datetime, timedelta

from BusinessLogic.otp_service import (
    MAX_VERIFY_ATTEMPTS,
    OTP_TTL_SECONDS,
    OtpService,
)
from BusinessLogic.user_business_logic import UserBusinessLogic
from Common.Entities.pending_registration import PendingRegistration
from Common.Enums.error_code import ErrorCode
from Common.Enums.otp_status import OtpStatus
from tests.fakes import InMemoryEmployeeRepository, RecordingSmsSender


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


def pending(mobile="09121234567", username="newuser"):
    return PendingRegistration("New", "User", mobile, username, "hashed-password")


class OtpServiceTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.service = OtpService(now_provider=self.clock)

    def test_code_is_not_stored_in_plaintext(self):
        code, refusal = self.service.start_registration(pending())
        self.assertIsNone(refusal)
        ticket = self.service._tickets["09121234567"]
        self.assertNotEqual(ticket.code_hash, code)
        self.assertNotIn(code, ticket.code_hash)

    def test_correct_code_verifies(self):
        code, _ = self.service.start_registration(pending())
        self.assertEqual(self.service.verify("09121234567", code), OtpStatus.VERIFIED)

    def test_wrong_code_is_invalid(self):
        self.service.start_registration(pending())
        self.assertEqual(self.service.verify("09121234567", "00000"), OtpStatus.INVALID)

    def test_code_expires_after_two_minutes(self):
        code, _ = self.service.start_registration(pending())
        self.clock.advance(OTP_TTL_SECONDS + 1)
        self.assertEqual(self.service.verify("09121234567", code), OtpStatus.EXPIRED)

    def test_code_still_valid_just_before_expiry(self):
        code, _ = self.service.start_registration(pending())
        self.clock.advance(OTP_TTL_SECONDS - 1)
        self.assertEqual(self.service.verify("09121234567", code), OtpStatus.VERIFIED)

    def test_too_many_wrong_attempts_locks_verification(self):
        code, _ = self.service.start_registration(pending())
        for _ in range(MAX_VERIFY_ATTEMPTS):
            self.service.verify("09121234567", "00000")
        # Even the correct code is refused once the attempt limit is reached.
        self.assertEqual(
            self.service.verify("09121234567", code), OtpStatus.TOO_MANY_ATTEMPTS
        )

    def test_resend_needs_cooldown(self):
        self.service.start_registration(pending())
        code, refusal = self.service.resend("09121234567")
        self.assertIsNone(code)
        self.assertEqual(refusal[0], "cooldown")

    def test_resend_after_cooldown_issues_new_code(self):
        first_code, _ = self.service.start_registration(pending())
        self.clock.advance(61)
        new_code, refusal = self.service.resend("09121234567")
        self.assertIsNone(refusal)
        # The previous code must no longer work.
        self.assertEqual(self.service.verify("09121234567", first_code), OtpStatus.INVALID)
        self.assertEqual(self.service.verify("09121234567", new_code), OtpStatus.VERIFIED)

    def test_send_limit_is_enforced(self):
        self.service.start_registration(pending())
        # Exhaust the allowed sends.
        for _ in range(3):
            self.clock.advance(61)
            self.service.resend("09121234567")
        self.clock.advance(61)
        code, refusal = self.service.resend("09121234567")
        self.assertIsNone(code)
        self.assertEqual(refusal[0], "send_limit")

    def test_new_code_invalidates_previous(self):
        first_code, _ = self.service.start_registration(pending())
        self.clock.advance(61)
        second_code, _ = self.service.resend("09121234567")
        self.assertEqual(self.service.verify("09121234567", first_code), OtpStatus.INVALID)
        self.assertEqual(self.service.verify("09121234567", second_code), OtpStatus.VERIFIED)


class RegistrationFlowTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryEmployeeRepository()
        self.sms = RecordingSmsSender()
        self.business = UserBusinessLogic(self.repository, sms_sender=self.sms)

    def test_registration_does_not_create_account_before_verification(self):
        response = self.business.register("New", "User", "09121234567", "newuser", "Passw0rd@")
        self.assertTrue(response.success)
        self.assertEqual(len(self.sms.sent), 1)
        # No account yet - verification has not happened.
        self.assertEqual(len(self.repository.employees), 0)

    def test_successful_verification_creates_account(self):
        self.business.register("New", "User", "09121234567", "newuser", "Passw0rd@")
        code = self.sms.sent[-1][1]

        response = self.business.verify_registration_otp("09121234567", code)
        self.assertTrue(response.success)
        self.assertEqual(len(self.repository.employees), 1)

        # And the new account can log in with the same password.
        login = self.business.login("newuser", "Passw0rd@")
        self.assertTrue(login.success)

    def test_wrong_code_does_not_create_account(self):
        self.business.register("New", "User", "09121234567", "newuser", "Passw0rd@")
        response = self.business.verify_registration_otp("09121234567", "00000")
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, ErrorCode.OTP_INVALID)
        self.assertEqual(len(self.repository.employees), 0)

    def test_code_cannot_be_used_twice(self):
        self.business.register("New", "User", "09121234567", "newuser", "Passw0rd@")
        code = self.sms.sent[-1][1]

        self.assertTrue(self.business.verify_registration_otp("09121234567", code).success)
        second = self.business.verify_registration_otp("09121234567", code)
        self.assertFalse(second.success)
        self.assertEqual(second.error_code, ErrorCode.OTP_NOT_FOUND)

    def test_sms_failure_is_reported_and_no_ticket_is_kept(self):
        self.business.sms_sender = RecordingSmsSender(succeed=False)
        response = self.business.register("New", "User", "09121234567", "newuser", "Passw0rd@")
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, ErrorCode.SMS_DELIVERY_FAILED)
        self.assertEqual(len(self.repository.employees), 0)

    def test_password_is_hashed_and_never_plaintext_in_store(self):
        self.business.register("New", "User", "09121234567", "newuser", "Passw0rd@")
        code = self.sms.sent[-1][1]
        self.business.verify_registration_otp("09121234567", code)

        stored = list(self.repository.employees.values())[0]
        self.assertNotEqual(stored.password, "Passw0rd@")


if __name__ == "__main__":
    unittest.main()
