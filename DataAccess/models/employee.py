from DataAccess.models.base import Base
from DataAccess.models.employee_status import EmployeeStatusModel
from DataAccess.models.role import RoleModel
from sqlalchemy import ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EmployeeModel(Base):
    __tablename__ = "Employee"

    # mapped_column's first argument is the actual column name in the
    # table (PascalCase, matching the existing schema) - the attribute
    # name on the Python side (snake_case) is what the rest of the code
    # uses.
    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column("FirstName", String(100), nullable=False)
    last_name: Mapped[str] = mapped_column("LastName", String(100), nullable=False)
    username: Mapped[str] = mapped_column("Username", String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column("Password", String(100), nullable=False)
    mobile: Mapped[str] = mapped_column("Mobile", String(22), nullable=False)
    employee_status_id: Mapped[int] = mapped_column(
        "EmployeeStatusId", SmallInteger, ForeignKey("EmployeeStatus.Id"), nullable=False
    )

    # Foreign key: every employee points at a row of the Role table. The
    # column is nullable in the database, so the mapping allows None too.
    role_id: Mapped[int | None] = mapped_column(
        "RoleId", Integer, ForeignKey("Role.Id"), nullable=True
    )
    photo_path: Mapped[str | None] = mapped_column("PhotoPath", String(260), nullable=True)
    role: Mapped[RoleModel] = relationship(back_populates="employees")
    status: Mapped[EmployeeStatusModel] = relationship(back_populates="employees")
