import os
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Common.Enums.transaction_type import TransactionType
from tests.fakes import InMemoryAccountRepository


class AccountStatementTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryAccountRepository()
        self.account = self.repository.add_account()
        self.business = AccountBusinessLogic(self.repository)

    def test_credit_and_debit_signs_are_applied(self):
        start = datetime(2026, 1, 2, 9, 0)
        transactions = [
            (1000, TransactionType.DEPOSIT),
            (250, TransactionType.WITHDRAW),
            (500, TransactionType.INCOMING_TRANSFER),
            (100, TransactionType.OUTGOING_TRANSFER),
            (50, TransactionType.BILL_PAYMENT),
            (20, TransactionType.FEE_CHARGE),
        ]

        for index, (amount, transaction_type) in enumerate(transactions):
            self.repository.add_transaction(
                self.account.id,
                amount,
                transaction_type,
                start + timedelta(minutes=index),
            )

        response = self.business.get_statement(self.account.id)
        self.assertTrue(response.success)

        statement = response.data
        self.assertEqual(statement.opening_balance, Decimal("0.00"))
        self.assertEqual(statement.total_credits, Decimal("1500"))
        self.assertEqual(statement.total_debits, Decimal("420"))
        self.assertEqual(statement.closing_balance, Decimal("1080"))

        self.assertEqual(statement.rows[0].credit, Decimal("1000"))
        self.assertEqual(statement.rows[0].debit, Decimal("0"))
        self.assertEqual(statement.rows[0].balance, Decimal("1000"))

        self.assertEqual(statement.rows[1].debit, Decimal("250"))
        self.assertEqual(statement.rows[1].credit, Decimal("0"))
        self.assertEqual(statement.rows[1].balance, Decimal("750"))

        self.assertEqual(statement.rows[-1].balance, Decimal("1080"))

    def test_transactions_are_ordered_by_date_then_id(self):
        later = datetime(2026, 1, 3, 9, 0)
        earlier = datetime(2026, 1, 2, 9, 0)

        self.repository.add_transaction(
            self.account.id, 300, TransactionType.DEPOSIT, later
        )
        self.repository.add_transaction(
            self.account.id, 100, TransactionType.DEPOSIT, earlier
        )
        self.repository.add_transaction(
            self.account.id, 200, TransactionType.DEPOSIT, earlier
        )

        statement = self.business.get_statement(self.account.id).data

        self.assertEqual(
            [row.transaction_id for row in statement.rows],
            [2, 3, 1],
        )
        self.assertEqual(
            [row.balance for row in statement.rows],
            [Decimal("100"), Decimal("300"), Decimal("600")],
        )

    def test_empty_account_has_zero_closing_balance(self):
        response = self.business.get_statement(self.account.id)

        self.assertTrue(response.success)
        self.assertEqual(response.data.rows, [])
        self.assertEqual(response.data.closing_balance, Decimal("0.00"))

    def test_missing_account_returns_an_error(self):
        response = self.business.get_statement(999)

        self.assertFalse(response.success)
        self.assertEqual(response.message, "Account not found.")

    def test_insert_transaction_is_reflected_in_the_statement(self):
        response = self.business.insert_transaction(
            self.account.id, Decimal("125"), TransactionType.DEPOSIT
        )

        self.assertTrue(response.success)
        statement = self.business.get_statement(self.account.id).data
        self.assertEqual(statement.closing_balance, Decimal("125"))

    def test_insert_transaction_rejects_invalid_amounts(self):
        for amount in (0, -5, Decimal("1.5"), "not-a-number"):
            response = self.business.insert_transaction(
                self.account.id, amount, TransactionType.DEPOSIT
            )
            self.assertFalse(response.success, amount)

    def test_insert_transaction_rejects_unknown_type(self):
        response = self.business.insert_transaction(self.account.id, 10, 99)
        self.assertFalse(response.success)

    def test_pdf_is_generated_for_a_normal_statement(self):
        self.repository.add_transaction(
            self.account.id, 1000, TransactionType.DEPOSIT
        )
        self.repository.add_transaction(
            self.account.id, 250, TransactionType.WITHDRAW
        )

        pdf_path = self._generate_pdf()
        content = _read(pdf_path)

        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)

    def test_pdf_handles_an_empty_statement(self):
        pdf_path = self._generate_pdf()
        content = _read(pdf_path)

        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 500)

    def test_pdf_is_multi_page_for_a_long_statement(self):
        start = datetime(2026, 1, 2, 9, 0)
        for index in range(150):
            self.repository.add_transaction(
                self.account.id,
                10,
                TransactionType.DEPOSIT,
                start + timedelta(minutes=index),
            )

        pdf_path = self._generate_pdf()
        content = _read(pdf_path)

        # ReportLab writes one /Type /Page object per page plus a /Type /Pages
        # node, so more than two markers means the table really paginated.
        self.assertGreater(content.count(b"/Type /Page"), 2)

    def _generate_pdf(self):
        file_descriptor, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(file_descriptor)
        self.addCleanup(lambda: os.path.exists(pdf_path) and os.remove(pdf_path))

        response = self.business.generate_statement_pdf(self.account.id, pdf_path)
        self.assertTrue(response.success, response.message)
        return pdf_path


def _read(path):
    with open(path, "rb") as pdf_file:
        return pdf_file.read()


if __name__ == "__main__":
    unittest.main()
