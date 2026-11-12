from enum import Enum


class TransactionType(Enum):
    """Transaction types stored in the TransactionType table.

    The values are the database ids, so the enum stays compatible with the
    existing data and with the API payloads.
    """

    DEPOSIT = 1
    WITHDRAW = 2
    INCOMING_TRANSFER = 3
    OUTGOING_TRANSFER = 4
    BILL_PAYMENT = 5
    FEE_CHARGE = 6

    @property
    def title(self) -> str:
        return _TITLES[self]

    @property
    def is_credit(self) -> bool:
        """True when the amount increases the account balance."""
        return self in _CREDIT_TYPES

    @property
    def direction(self) -> str:
        return "Credit" if self.is_credit else "Debit"


_TITLES = {
    TransactionType.DEPOSIT: "Deposit",
    TransactionType.WITHDRAW: "Withdraw",
    TransactionType.INCOMING_TRANSFER: "Incoming Transfer",
    TransactionType.OUTGOING_TRANSFER: "Outgoing Transfer",
    TransactionType.BILL_PAYMENT: "Bill Payment",
    TransactionType.FEE_CHARGE: "Fee Charge",
}

# Deposits and incoming transfers add money to the account. Every other
# type in the existing TransactionType table takes money out.
_CREDIT_TYPES = {
    TransactionType.DEPOSIT,
    TransactionType.INCOMING_TRANSFER,
}
