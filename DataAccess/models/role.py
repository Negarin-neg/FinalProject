from DataAccess.models.base import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class RoleModel(Base):
    __tablename__ = "Role"

    # Id is an IDENTITY column in the database, and the seeded values must
    # match Common/Enums/role.py (1 = ADMINISTRATOR, 2 = BANKER).
    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column("Title", String(100), nullable=False, unique=True)

    # One role -> many employees (the other side of Employee.role).
    employees: Mapped[list["EmployeeModel"]] = relationship(back_populates="role")
