from DataAccess.models.base import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TransactionTypeModel(Base):
    __tablename__ = "TransactionType"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column("Title", String(50), nullable=False)

    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="transaction_type")
