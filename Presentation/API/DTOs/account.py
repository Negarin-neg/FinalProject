from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from Common.DTOs.statement import AccountStatement, StatementRow
from Common.Entities.account import Account
from Common.Enums.transaction_type import TransactionType


class CreateTransactionRequest(BaseModel):
    account_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    transaction_type: TransactionType


class AccountResponse(BaseModel):
    id: int
    account_number: str
    opening_date: datetime
    customer_id: int
    customer_name: str


class StatementRowResponse(BaseModel):
    sequence: int
    transaction_id: int
    created_at: datetime
    transaction_type: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class StatementResponse(BaseModel):
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
    rows: list[StatementRowResponse]


def account_to_response(account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        account_number=account.account_number,
        opening_date=account.opening_date,
        customer_id=account.owner_customer.id,
        customer_name=account.owner_customer.get_fullname(),
    )


def statement_to_response(statement: AccountStatement) -> StatementResponse:
    return StatementResponse(
        account_id=statement.account_id,
        account_number=statement.account_number,
        customer_id=statement.customer_id,
        customer_name=statement.customer_name,
        opening_date=statement.opening_date,
        generated_at=statement.generated_at,
        opening_balance=statement.opening_balance,
        total_debits=statement.total_debits,
        total_credits=statement.total_credits,
        closing_balance=statement.closing_balance,
        rows=[_row_to_response(row) for row in statement.rows],
    )


def _row_to_response(row: StatementRow) -> StatementRowResponse:
    return StatementRowResponse(
        sequence=row.sequence,
        transaction_id=row.transaction_id,
        created_at=row.created_at,
        transaction_type=row.transaction_type,
        description=row.description,
        debit=row.debit,
        credit=row.credit,
        balance=row.balance,
    )
