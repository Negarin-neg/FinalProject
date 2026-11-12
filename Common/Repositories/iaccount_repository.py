from abc import ABC, abstractmethod

from Common.Entities.account import Account


class IAccountRepository(ABC):
    @abstractmethod
    def get_account_list(self, search: str = "", page_number: int = 1, page_size: int = 20):
        pass

    @abstractmethod
    def get_account_by_id(self, account_id: int) -> Account:
        pass

    @abstractmethod
    def get_transaction_by_account_id(self, account_id: int):
        pass

    @abstractmethod
    def insert_transaction(self, account_id: int, amount, transaction_type):
        pass
