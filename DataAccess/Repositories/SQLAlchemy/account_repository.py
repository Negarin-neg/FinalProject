from datetime import datetime

from sqlalchemy import or_, select

from Common.Entities.account import Account
from Common.Entities.customer import Customer
from Common.Entities.transaction import Transaction
from Common.Repositories.iaccount_repository import IAccountRepository
from DataAccess.config.database import create_session
from DataAccess.models.account import AccountModel
from DataAccess.models.customer import CustomerModel
from DataAccess.models.transaction import TransactionModel


class SQLAlchemyAccountRepository(IAccountRepository):
    def get_account_list(self, search: str = "", page_number: int = 1, page_size: int = 20):
        with create_session() as session:
            statement = (
                select(AccountModel)
                .join(AccountModel.customer)
                .order_by(AccountModel.id)
            )

            search = (search or "").strip()
            if search:
                pattern = f"%{search}%"
                statement = statement.where(
                    or_(
                        AccountModel.account_number.like(pattern),
                        CustomerModel.first_name.like(pattern),
                        CustomerModel.last_name.like(pattern),
                    )
                )

            statement = statement.offset((page_number - 1) * page_size).limit(page_size)
            models = session.scalars(statement).all()

            return [self._to_account(model) for model in models]

    def get_account_by_id(self, account_id: int) -> Account:
        with create_session() as session:
            model = session.get(AccountModel, account_id)
            return self._to_account(model) if model else None

    def get_transaction_by_account_id(self, account_id: int):
        with create_session() as session:
            account_model = session.get(AccountModel, account_id)
            if account_model is None:
                return []

            account = self._to_account(account_model)
            statement = (
                select(TransactionModel)
                .where(TransactionModel.account_id == account_id)
                .order_by(TransactionModel.created_at, TransactionModel.id)
            )
            models = session.scalars(statement).all()

            return [
                Transaction(
                    model.id,
                    model.amount,
                    model.transaction_type_id,
                    model.created_at,
                    account,
                )
                for model in models
            ]

    def insert_transaction(self, account_id: int, amount, transaction_type):
        with create_session() as session:
            account_model = session.get(AccountModel, account_id)
            if account_model is None:
                raise LookupError(f"Account {account_id} does not exist.")

            model = TransactionModel(
                account_id=account_id,
                amount=amount,
                transaction_type_id=transaction_type.value,
                created_at=datetime.now(),
            )
            session.add(model)
            session.flush()
            return model.id

    @staticmethod
    def _to_account(model: AccountModel) -> Account:
        customer = Customer(
            model.customer.id,
            model.customer.first_name,
            model.customer.last_name,
        )
        return Account(model.id, model.account_number, model.opening_date, customer)
