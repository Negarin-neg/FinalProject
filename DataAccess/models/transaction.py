from datetime import datetime
from decimal import Decimal

from DataAccess.models.account import AccountModel
from DataAccess.models.base import Base
from DataAccess.models.transaction_type import TransactionTypeModel
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TransactionModel(Base):
    __tablename__ = "Transactions"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        "AccountId", Integer, ForeignKey("Account.Id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column("Amount", Numeric(18, 0), nullable=False)
    transaction_type_id: Mapped[int] = mapped_column(
        "TransactionTypeId", Integer, ForeignKey("TransactionType.Id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime, nullable=False)

    account: Mapped[AccountModel] = relationship(back_populates="transactions")
    transaction_type: Mapped[TransactionTypeModel] = relationship(back_populates="transactions")
