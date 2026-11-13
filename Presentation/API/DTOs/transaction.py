from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from Common.Enums.transaction_type import TransactionType


class CreateTransaction(BaseModel):
    account_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    transaction_type: TransactionType


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    amount: Decimal
    transaction_type: str
    created_at: datetime
