import re
from hashlib import md5

from Common.Entities.employee import Employee
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
from Common.DTOs.response import Response
from Common.Repositories.iemployee_repository import IEmployeeRepository

# Iranian mobile format: 11 digits, starting with 09 (e.g. 09121234567)
MOBILE_PATTERN = re.compile(r"^09\d{9}$")

PASSWORD_MIN_LENGTH = 8
PASSWORD_SPECIAL_CHARACTERS = "@./"


class UserBusinessLogic:
    def __init__(self, employee_repository: IEmployeeRepository):
        self.employee_repository = employee_repository

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
        else:
            return Response(False, "Invalid username or password")

    def register(self, first_name: str, last_name: str, mobile: str, username: str, password: str):
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

        # 3) Everything is valid - build the entity and save it.
        # The password is hashed with MD5 exactly like login() does, otherwise
        # the user could never log in with the password they just chose.
        # Everybody who registers by themselves becomes a BANKER; an
        # ADMINISTRATOR has to be promoted by hand in the database.
        password_hashed = md5(password.encode()).hexdigest()
        employee = Employee(
            None,
            first_name,
            last_name,
            username,
            password_hashed,
            mobile,
            EmployeeStatus.Active.value,
            Roles.BANKER.value,
        )
        self.employee_repository.insert(employee)

        return Response(True, "Registration successful. You can now log in.", employee)

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
