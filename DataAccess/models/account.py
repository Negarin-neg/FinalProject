from datetime import datetime

from DataAccess.models.base import Base
from DataAccess.models.customer import CustomerModel
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AccountModel(Base):
    __tablename__ = "Account"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column("AccountNumber", String(50), nullable=False)
    customer_id: Mapped[int] = mapped_column(
        "CustomerId", Integer, ForeignKey("Customer.Id"), nullable=False
    )
    opening_date: Mapped[datetime] = mapped_column("OpeningDate", DateTime, nullable=False)

    customer: Mapped[CustomerModel] = relationship(back_populates="accounts")
    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="account")
