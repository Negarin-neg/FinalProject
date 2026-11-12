from DataAccess.models.base import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CustomerModel(Base):
    __tablename__ = "Customer"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column("FirstName", String(50), nullable=False)
    last_name: Mapped[str | None] = mapped_column("LastName", String(50), nullable=True)

    accounts: Mapped[list["AccountModel"]] = relationship(back_populates="customer")
