from fastapi import Depends, Header, HTTPException

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Common.Entities.employee import Employee
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
from Common.Repositories.iaccount_repository import IAccountRepository
from Common.Repositories.iemployee_repository import IEmployeeRepository
from DataAccess.Repositories.SQLAlchemy.account_repository import SQLAlchemyAccountRepository
from DataAccess.Repositories.SQLAlchemy.employee_repository import SQLAlchemyEmployeeRepository


def get_account_repository() -> IAccountRepository:
    return SQLAlchemyAccountRepository()


def get_account_business_logic(
    account_repository: IAccountRepository = Depends(get_account_repository),
) -> AccountBusinessLogic:
    return AccountBusinessLogic(account_repository)


def get_employee_repository() -> IEmployeeRepository:
    return SQLAlchemyEmployeeRepository()


def get_current_employee(
    employee_id: int | None = Header(default=None, alias="X-Employee-Id"),
    employee_repository: IEmployeeRepository = Depends(get_employee_repository),
) -> Employee:
    if employee_id is None:
        raise HTTPException(status_code=401, detail="Authentication is required.")

    employee = employee_repository.get_by_id(employee_id)

    if employee is None or employee.status != EmployeeStatus.Active:
        raise HTTPException(
            status_code=401,
            detail="Your session is not valid. Please log in again.",
        )

    if employee.role not in (Roles.ADMINISTRATOR, Roles.BANKER):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view customer accounts.",
        )

    return employee
