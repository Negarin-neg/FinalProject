import re
from hashlib import md5

from Common.Entities.employee import Employee
from Common.Entities.pending_registration import PendingRegistration
from Common.Enums.error_code import ErrorCode
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.otp_status import OtpStatus
from Common.Enums.role import Roles
from Common.DTOs.response import Response
from Common.Repositories.iemployee_repository import IEmployeeRepository
from Common.Repositories.ismssender import ISmsSender
from BusinessLogic.otp_service import OtpService
from BusinessLogic.photo_service import PhotoService, PhotoValidationError

# Iranian mobile format: 11 digits, starting with 09 (e.g. 09121234567)
MOBILE_PATTERN = re.compile(r"^09\d{9}$")

PASSWORD_MIN_LENGTH = 8
PASSWORD_SPECIAL_CHARACTERS = "@./"


class UserBusinessLogic:
    def __init__(
        self,
        employee_repository: IEmployeeRepository,
        sms_sender: ISmsSender = None,
        otp_service: OtpService = None,
        photo_service: PhotoService = None,
    ):
        self.employee_repository = employee_repository
        # Optional so the existing SQLite/repository unit tests can keep
        # constructing the class with just a repository.
        self.sms_sender = sms_sender
        self.otp_service = otp_service or OtpService()
        self.photo_service = photo_service

    def login(self, username: str, password: str):
        if len(username) < 3 or len(password) < 6:
            return Response(False, "Invalid structure username or password.")

        password_hashed = md5(password.encode()).hexdigest()
        employee = self.employee_repository.get_by_username_password(username, password_hashed)

        if employee:
            match employee.status:
                case EmployeeStatus.Active:
                    return Response(True, f"Welcome {employee.get_fullname()}", employee)
                case EmployeeStatus.Pending:
                    return Response(False, "Your account is pending(call to administrator).", employee)
                case EmployeeStatus.Deactive:
                    return Response(False, "Your account was deactivated.", employee)

        # No row matched username+password. Tell the two cases apart:
        # a username that does not exist at all (the user may simply need to
        # register) vs. an existing username whose password was wrong.
        if self.employee_repository.get_by_username(username) is None:
            return Response(
                False,
                "حسابی با این نام کاربری وجود ندارد. برای ایجاد حساب به صفحهٔ ثبت‌نام منتقل می‌شوید.",
                error_code=ErrorCode.ACCOUNT_NOT_FOUND,
            )

        return Response(False, "Invalid username or password")

    def register(self, first_name: str, last_name: str, mobile: str, username: str, password: str):
        """Validates a new sign-up and starts OTP verification.

        Nothing is written to the database here. The validated details are
        held (with the password already hashed) until the one-time code is
        verified, so an unverified sign-up never creates an account.
        """
        first_name = first_name.strip()
        last_name = last_name.strip()
        mobile = mobile.strip()
        username = username.strip()

        # 1) Cheap checks first - nothing here touches the database.
        profile_error = self._get_profile_fields_error(first_name, last_name, mobile, username)
        if profile_error:
            return Response(False, profile_error)

        password_error = self._get_password_error(password)
        if password_error:
            return Response(False, password_error)

        # 2) Uniqueness checks - these need the repository.
        if self.employee_repository.get_by_mobile(mobile):
            return Response(False, "This mobile number is already registered.")

        if self.employee_repository.get_by_username(username):
            return Response(False, "This username is already taken.")

        # 3) Everything is valid - hash the password now (the plaintext copy
        # is dropped as soon as this method returns) and hold the pending
        # registration until the OTP is confirmed.
        password_hashed = md5(password.encode()).hexdigest()
        pending = PendingRegistration(
            first_name,
            last_name,
            mobile,
            username,
            password_hashed,
        )

        return self._issue_and_send_otp(pending, force_resend=False)

    def resend_registration_otp(self, mobile: str):
        """Issues and sends a new code for a pending registration."""
        mobile = (mobile or "").strip()
        # The send is guarded inside OtpService (cooldown + send limit).
        code, refusal = self.otp_service.resend(mobile)

        if refusal is not None:
            return self._otp_refusal_response(refusal)

        return self._send_otp_code(mobile, code)

    def verify_registration_otp(self, mobile: str, code: str):
        """Verifies the code and, only then, creates the account."""
        mobile = (mobile or "").strip()
        status = self.otp_service.verify(mobile, code)

        match status:
            case OtpStatus.NOT_FOUND:
                return Response(
                    False,
                    "کد تأیید یافت نشد. لطفاً دوباره ثبت‌نام کنید.",
                    error_code=ErrorCode.OTP_NOT_FOUND,
                )
            case OtpStatus.EXPIRED:
                return Response(
                    False,
                    "کد تأیید منقضی شده است. لطفاً کد جدید بگیرید.",
                    error_code=ErrorCode.OTP_EXPIRED,
                )
            case OtpStatus.TOO_MANY_ATTEMPTS:
                return Response(
                    False,
                    "تعداد تلاش‌های ناموفق بیش از حد مجاز است. لطفاً کد جدید بگیرید.",
                    error_code=ErrorCode.OTP_TOO_MANY_ATTEMPTS,
                )
            case OtpStatus.INVALID:
                return Response(
                    False,
                    "کد تأیید نادرست است.",
                    error_code=ErrorCode.OTP_INVALID,
                )

        # Verified - the code is single-use, so take (and drop) the ticket.
        pending = self.otp_service.take_pending(mobile)
        if pending is None:
            return Response(
                False,
                "کد تأیید یافت نشد. لطفاً دوباره ثبت‌نام کنید.",
                error_code=ErrorCode.OTP_NOT_FOUND,
            )

        # Re-check uniqueness: another sign-up may have taken the username or
        # mobile while this code was pending.
        if self.employee_repository.get_by_mobile(pending.mobile):
            return Response(False, "This mobile number is already registered.")

        if self.employee_repository.get_by_username(pending.username):
            return Response(False, "This username is already taken.")

        # Everybody who registers by themselves becomes a BANKER; an
        # ADMINISTRATOR has to be promoted by hand in the database.
        employee = Employee(
            None,
            pending.first_name,
            pending.last_name,
            pending.username,
            pending.password_hash,
            pending.mobile,
            EmployeeStatus.Active.value,
            Roles.BANKER.value,
        )
        self.employee_repository.insert(employee)

        return Response(True, "ثبت‌نام با موفقیت انجام شد. اکنون می‌توانید وارد شوید.", employee)

    # ------------------------------------------------------------------
    # OTP plumbing
    # ------------------------------------------------------------------

    def _issue_and_send_otp(self, pending: PendingRegistration, force_resend: bool):
        code, refusal = self.otp_service.start_registration(pending, force_resend=force_resend)

        if refusal is not None:
            return self._otp_refusal_response(refusal)

        return self._send_otp_code(pending.mobile, code)

    def _send_otp_code(self, mobile: str, code: str):
        if self.sms_sender is None or not self.sms_sender.send_otp(mobile, code):
            # Do not leave a live ticket behind for a message that never left.
            self.otp_service.discard(mobile)
            return Response(
                False,
                "ارسال پیامک ناموفق بود. لطفاً بعداً دوباره تلاش کنید.",
                error_code=ErrorCode.SMS_DELIVERY_FAILED,
            )

        return Response(True, f"کد تأیید به شماره {mobile} ارسال شد.", mobile)

    @staticmethod
    def _otp_refusal_response(refusal):
        reason, seconds = refusal

        if reason == "cooldown":
            return Response(
                False,
                f"برای ارسال دوباره {seconds} ثانیه صبر کنید.",
                error_code=ErrorCode.OTP_RESEND_COOLDOWN,
            )

        if reason == "send_limit":
            return Response(
                False,
                "تعداد درخواست‌های ارسال کد بیش از حد مجاز است. لطفاً بعداً تلاش کنید.",
                error_code=ErrorCode.OTP_SEND_LIMIT,
            )

        return Response(
            False,
            "کد تأیید یافت نشد. لطفاً دوباره ثبت‌نام کنید.",
            error_code=ErrorCode.OTP_NOT_FOUND,
        )

    # ------------------------------------------------------------------
    # My Profile
    # ------------------------------------------------------------------

    def get_profile(self, employee_id: int):
        """Loads the employee fresh from the database (the copy kept after
        login can be out of date once the profile has been edited)."""
        employee = self.employee_repository.get_by_id(employee_id)

        if employee is None:
            return Response(False, "Employee not found.")

        return Response(True, "", employee)

    def update_profile(
        self,
        employee_id: int,
        first_name: str,
        last_name: str,
        mobile: str,
        username: str,
        current_password: str,
        new_password: str,
    ):
        """
        Edits the fields an employee is allowed to change about themselves.
        - new_password empty  -> the password stays as it is
        Role and status are never touched here, so nobody can promote
        themselves from the profile page.
        """
        employee = self.employee_repository.get_by_id(employee_id)

        if employee is None:
            return Response(False, "Employee not found.")

        first_name = first_name.strip()
        last_name = last_name.strip()
        mobile = mobile.strip()
        username = username.strip()

        profile_error = self._get_profile_fields_error(first_name, last_name, mobile, username)
        if profile_error:
            return Response(False, profile_error)

        # Changing the password needs the current one (someone sitting at an
        # unlocked computer shouldn't be able to take over the account).
        changing_password = bool(new_password)
        if changing_password:
            if not current_password:
                return Response(False, "Enter your current password to set a new one.")

            if md5(current_password.encode()).hexdigest() != employee.password:
                return Response(False, "Current password is incorrect.")

            password_error = self._get_password_error(new_password)
            if password_error:
                return Response(False, password_error)

        # Uniqueness - but the employee's own row doesn't count as a duplicate.
        employee_with_same_mobile = self.employee_repository.get_by_mobile(mobile)
        if employee_with_same_mobile and employee_with_same_mobile.id != employee.id:
            return Response(False, "This mobile number is already registered.")

        employee_with_same_username = self.employee_repository.get_by_username(username)
        if employee_with_same_username and employee_with_same_username.id != employee.id:
            return Response(False, "This username is already taken.")

        employee.first_name = first_name
        employee.last_name = last_name
        employee.mobile = mobile
        employee.username = username

        if changing_password:
            employee.password = md5(new_password.encode()).hexdigest()

        self.employee_repository.update_profile(employee)

        return Response(True, "Your profile was updated.", employee)

    # ------------------------------------------------------------------
    # Profile photo
    # ------------------------------------------------------------------

    def get_profile_photo(self, employee_id: int):
        """Returns the raw bytes of the employee's photo, or None."""
        if self.photo_service is None:
            return None

        employee = self.employee_repository.get_by_id(employee_id)
        if employee is None:
            return None

        return self.photo_service.read(employee.photo_path)

    def upload_profile_photo(self, employee_id: int, file_bytes: bytes, filename: str = ""):
        """Validates and stores a photo for the *currently authenticated*
        employee. `employee_id` is the caller's own id - the profile page
        never passes another user's id, and the file name is derived from it,
        so one user cannot touch another's photo."""
        if self.photo_service is None:
            return Response(False, "قابلیت بارگذاری تصویر در دسترس نیست.")

        employee = self.employee_repository.get_by_id(employee_id)
        if employee is None:
            return Response(False, "Employee not found.")

        try:
            photo_path = self.photo_service.save(employee_id, file_bytes, filename)
        except PhotoValidationError as ex:
            return Response(False, str(ex))

        self.employee_repository.update_photo_path(employee_id, photo_path)
        employee.photo_path = photo_path

        return Response(True, "تصویر پروفایل با موفقیت ذخیره شد.", employee)

    def remove_profile_photo(self, employee_id: int):
        if self.photo_service is None:
            return Response(False, "قابلیت بارگذاری تصویر در دسترس نیست.")

        employee = self.employee_repository.get_by_id(employee_id)
        if employee is None:
            return Response(False, "Employee not found.")

        self.photo_service.remove(employee_id)
        self.employee_repository.update_photo_path(employee_id, None)
        employee.photo_path = None

        return Response(True, "تصویر پروفایل حذف شد.", employee)

    # ------------------------------------------------------------------
    # Validation helpers (shared by register and update_profile)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_profile_fields_error(first_name: str, last_name: str, mobile: str, username: str):
        """Expects already-stripped values. Returns a message, or None if all are valid."""
        if not first_name or not last_name:
            return "First name and last name are required."

        if not MOBILE_PATTERN.match(mobile):
            return "Mobile number must be 11 digits and start with 09 (e.g. 09121234567)."

        # login() rejects usernames shorter than 3, so such an account could never log in.
        if len(username) < 3:
            return "Username must be at least 3 characters."

        return None

    @staticmethod
    def _get_password_error(password: str):
        """Returns a message describing the first broken rule, or None if the password is valid."""
        if len(password) < PASSWORD_MIN_LENGTH:
            return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."

        if not any(char.islower() for char in password):
            return "Password must contain at least one lowercase letter."

        if not any(char.isupper() for char in password):
            return "Password must contain at least one uppercase letter."

        if not any(char in PASSWORD_SPECIAL_CHARACTERS for char in password):
            return "Password must contain at least one of these characters: @ . /"

        return None
