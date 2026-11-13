from fastapi import Depends

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Common.Repositories.iaccount_repository import IAccountRepository
from DataAccess.Repositories.SQLAlchemy.account_repository import SQLAlchemyAccountRepository


def get_account_repository() -> IAccountRepository:
    return SQLAlchemyAccountRepository()


def get_account_business_logic(
    account_repository: IAccountRepository = Depends(get_account_repository),
) -> AccountBusinessLogic:
    return AccountBusinessLogic(account_repository)
