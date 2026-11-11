from DataAccess.models.base import Base
from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EmployeeStatusModel(Base):
    __tablename__ = "EmployeeStatus"

    # Seeded with 1 = Pending, 2 = Active, 3 = Deactive (see
    # Common/Enums/employee_status.py).
    id: Mapped[int] = mapped_column("Id", SmallInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column("Title", String(100), nullable=False)

    employees: Mapped[list["EmployeeModel"]] = relationship(back_populates="status")
