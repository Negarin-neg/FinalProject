from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles



class Employee:
    def __init__(self, id, firstname, lastname, username, password, mobile, employee_status_id, role_id):
        self.id = id
        self.first_name = firstname
        self.last_name = lastname
        self.username = username
        self.password = password
        self.mobile = mobile
        self.status = EmployeeStatus(employee_status_id)
        # RoleId is nullable in the database, so an employee may have no role.
        self.role = Roles(role_id) if role_id is not None else None

    def get_fullname(self):
        return f"{self.first_name} {self.last_name}"
