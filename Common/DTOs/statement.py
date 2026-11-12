from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class StatementRow:
    sequence: int
    transaction_id: int
    created_at: datetime
    transaction_type: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


@dataclass
class AccountStatement:
    account_id: int
    account_number: str
    customer_id: int
    customer_name: str
    opening_date: datetime
    generated_at: datetime
    opening_balance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    closing_balance: Decimal
    rows: list[StatementRow] = field(default_factory=list)
