from sqlalchemy import select

from Common.Entities.employee import Employee
from Common.Repositories.iemployee_repository import IEmployeeRepository
from DataAccess.config.database import create_session
from DataAccess.models.employee import EmployeeModel


class SQLAlchemyEmployeeRepository(IEmployeeRepository):
    """
    Same contract as the old pymssql-based SQLServerEmployeeRepository
    (IEmployeeRepository), implemented with SQLAlchemy instead. Because
    BusinessLogic only ever depends on IEmployeeRepository, swapping this
    in for the old repository required no changes to BusinessLogic.
    """

    def get_by_username_password(self, username: str, password: str) -> Employee:
        return self._get_one(
            EmployeeModel.username == username,
            EmployeeModel.password == password,
        )

    def get_by_id(self, employee_id: int) -> Employee:
        return self._get_one(EmployeeModel.id == employee_id)

    def get_by_username(self, username: str) -> Employee:
        return self._get_one(EmployeeModel.username == username)

    def get_by_mobile(self, mobile: str) -> Employee:
        return self._get_one(EmployeeModel.mobile == mobile)

    def get_all(self):
        with create_session() as session:
            models = session.scalars(
                select(EmployeeModel).order_by(EmployeeModel.id)
            ).all()

            return [self._to_entity(model) for model in models]

    def insert(self, employee: Employee):
        with create_session() as session:
            model = EmployeeModel(
                first_name=employee.first_name,
                last_name=employee.last_name,
                username=employee.username,
                password=employee.password,
                mobile=employee.mobile,
                employee_status_id=employee.status.value,
                role_id=employee.role.value if employee.role else None,
                photo_path=employee.photo_path,
            )
            session.add(model)
            session.flush()
            return model.id

    def update_profile(self, employee: Employee):
        with create_session() as session:
            model = session.get(EmployeeModel, employee.id)

            if model is None:
                raise LookupError(f"Employee {employee.id} does not exist.")

            # Only the fields an employee may edit about themselves. Role and
            # status are deliberately NOT touched here.
            model.first_name = employee.first_name
            model.last_name = employee.last_name
            model.username = employee.username
            model.password = employee.password
            model.mobile = employee.mobile

    def update(self, employee: Employee):
        """Full update used by an administrator: every column can change,
        including the role and the status."""
        with create_session() as session:
            model = session.get(EmployeeModel, employee.id)

            if model is None:
                raise LookupError(f"Employee {employee.id} does not exist.")

            model.first_name = employee.first_name
            model.last_name = employee.last_name
            model.username = employee.username
            model.password = employee.password
            model.mobile = employee.mobile
            model.employee_status_id = employee.status.value
            model.role_id = employee.role.value if employee.role else None

    def update_status(self, employee_id: int, employee_status_id: int):
        with create_session() as session:
            model = session.get(EmployeeModel, employee_id)

            if model is None:
                raise LookupError(f"Employee {employee_id} does not exist.")

            model.employee_status_id = employee_status_id

    def delete(self, employee_id: int) -> bool:
        with create_session() as session:
            model = session.get(EmployeeModel, employee_id)

            if model is None:
                return False

            session.delete(model)
            return True

    def update_photo_path(self, employee_id: int, photo_path):
        with create_session() as session:
            model = session.get(EmployeeModel, employee_id)

            if model is None:
                raise LookupError(f"Employee {employee_id} does not exist.")

            model.photo_path = photo_path

    def _get_one(self, *conditions) -> Employee:
        with create_session() as session:
            model = session.scalars(select(EmployeeModel).where(*conditions)).first()

            if model is None:
                return None

            return self._to_entity(model)

    @staticmethod
    def _to_entity(model: EmployeeModel) -> Employee:
        # BusinessLogic works with the plain Employee entity, not the
        # SQLAlchemy model - keeps the ORM detail inside DataAccess only.
        return Employee(
            model.id,
            model.first_name,
            model.last_name,
            model.username,
            model.password,
            model.mobile,
            model.employee_status_id,
            model.role_id,
            model.photo_path,
        )
