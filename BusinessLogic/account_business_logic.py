import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from Common.DTOs.response import Response
from Common.DTOs.statement import AccountStatement, StatementRow
from Common.Enums.transaction_type import TransactionType
from Common.Repositories.iaccount_repository import IAccountRepository

_FONT_NAME, _FONT_BOLD = "Helvetica", "Helvetica-Bold"


def _register_unicode_fonts():
    """Use a Unicode-capable font when the platform provides one.

    The reference report uses Helvetica. Arial is used when available so
    customer data is not limited to the WinAnsi character set, while the
    report structure and the PDF library stay the same.
    """
    global _FONT_NAME, _FONT_BOLD

    fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    regular_path = os.path.join(fonts_dir, "arial.ttf")
    bold_path = os.path.join(fonts_dir, "arialbd.ttf")

    if not (os.path.isfile(regular_path) and os.path.isfile(bold_path)):
        return

    try:
        pdfmetrics.registerFont(TTFont("BankSans", regular_path))
        pdfmetrics.registerFont(TTFont("BankSans-Bold", bold_path))
    except Exception:
        return

    _FONT_NAME, _FONT_BOLD = "BankSans", "BankSans-Bold"


_register_unicode_fonts()


class AccountBusinessLogic:
    def __init__(self, account_repository: IAccountRepository):
        self.account_repository = account_repository

    def get_account_list(self, search: str = "", page_number: int = 1, page_size: int = 20):
        try:
            page_number = max(1, int(page_number))
            page_size = min(max(1, int(page_size)), 100)
            account_list = self.account_repository.get_account_list(
                search, page_number, page_size
            )
            return Response(True, None, account_list)
        except Exception:
            return Response(False, "Customer accounts could not be loaded.")

    def get_transactions(self, account_id: int):
        try:
            account = self.account_repository.get_account_by_id(account_id)
            if account is None:
                return Response(False, "Account not found.")

            transactions = self.account_repository.get_transaction_by_account_id(account_id)
            return Response(True, None, transactions)
        except Exception:
            return Response(False, "Transactions could not be loaded.")

    def get_statement(self, account_id: int):
        try:
            account = self.account_repository.get_account_by_id(account_id)
            if account is None:
                return Response(False, "Account not found.")

            transactions = self.account_repository.get_transaction_by_account_id(account_id)
            statement = self._build_statement(account, transactions)
            return Response(True, None, statement)
        except Exception:
            return Response(False, "The account statement could not be prepared.")

    def insert_transaction(self, account_id: int, amount, transaction_type):
        try:
            account = self.account_repository.get_account_by_id(account_id)
            if account is None:
                return Response(False, "Account not found.")

            try:
                amount = Decimal(str(amount))
            except (InvalidOperation, ValueError):
                return Response(False, "Amount must be a valid number.")

            if not amount.is_finite() or amount <= 0:
                return Response(False, "Amount must be greater than zero.")

            # The Amount column is decimal(18, 0), so a fractional amount
            # would be silently rounded by the database.
            if amount != amount.to_integral_value():
                return Response(False, "Amount must be a whole number.")

            try:
                transaction_type = (
                    transaction_type
                    if isinstance(transaction_type, TransactionType)
                    else TransactionType(transaction_type)
                )
            except ValueError:
                return Response(False, "Unknown transaction type.")

            self.account_repository.insert_transaction(account_id, amount, transaction_type)
            return Response(True, "Transaction completed successfully.", None)
        except Exception:
            return Response(False, "The transaction could not be completed.")

    def generate_statement_pdf(self, account_id: int, file_path: str):
        response = self.get_statement(account_id)
        if not response.success:
            return response

        statement = response.data
        directory = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(directory, exist_ok=True)

        try:
            self._build_pdf(statement, file_path)
        except Exception:
            return Response(False, "The statement PDF could not be generated.")

        return Response(True, "Statement generated successfully.", file_path)

    def _build_statement(self, account, transactions) -> AccountStatement:
        # The schema has no opening-balance column. The statement therefore
        # starts from zero and reflects only the transactions that exist for
        # the account; it does not invent a balance that is not stored.
        opening_balance = Decimal("0.00")
        running_balance = opening_balance
        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")
        rows = []

        for index, transaction in enumerate(
            sorted(transactions, key=lambda item: (item.created_at, item.id)), start=1
        ):
            amount = Decimal(str(transaction.amount))

            if transaction.transaction_type.is_credit:
                debit = Decimal("0.00")
                credit = amount
                running_balance += amount
                total_credits += amount
            else:
                debit = amount
                credit = Decimal("0.00")
                running_balance -= amount
                total_debits += amount

            rows.append(
                StatementRow(
                    sequence=index,
                    transaction_id=transaction.id,
                    created_at=transaction.created_at,
                    transaction_type=transaction.transaction_type.title,
                    description=f"Transaction #{transaction.id}",
                    debit=debit,
                    credit=credit,
                    balance=running_balance,
                )
            )

        return AccountStatement(
            account_id=account.id,
            account_number=account.account_number,
            customer_id=account.owner_customer.id,
            customer_name=account.owner_customer.get_fullname(),
            opening_date=account.opening_date,
            generated_at=datetime.now(),
            opening_balance=opening_balance,
            total_debits=total_debits,
            total_credits=total_credits,
            closing_balance=running_balance,
            rows=rows,
        )

    @staticmethod
    def _build_pdf(statement: AccountStatement, file_path: str):
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        title_style.alignment = 0  # left
        title_style.fontName = _FONT_BOLD
        normal_style = styles["Normal"]
        normal_style.alignment = 0
        normal_style.fontName = _FONT_NAME
        small_style = styles["BodyText"]
        small_style.fontSize = 8
        small_style.leading = 10
        small_style.alignment = 0
        small_style.fontName = _FONT_NAME

        document = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        elements = [
            Paragraph("Account Statement", title_style),
            Paragraph(
                f"Generated: {statement.generated_at:%Y-%m-%d %H:%M}", normal_style
            ),
            Spacer(1, 8),
        ]

        account_data = [
            ["Customer", statement.customer_name],
            ["Account Number", statement.account_number],
            ["Opening Date", statement.opening_date.strftime("%Y-%m-%d")],
        ]
        account_table = Table(account_data, colWidths=[38 * mm, 120 * mm])
        account_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
                    ("FONTNAME", (1, 0), (1, -1), _FONT_NAME),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.extend([account_table, Spacer(1, 10)])

        summary_data = [
            ["Opening Balance", _money(statement.opening_balance),
             "Total Credits", _money(statement.total_credits)],
            ["Total Debits", _money(statement.total_debits),
             "Closing Balance", _money(statement.closing_balance)],
        ]
        summary_table = Table(
            summary_data,
            colWidths=[35 * mm, 35 * mm, 35 * mm, 35 * mm],
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F5FA")),
                    ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
                    ("FONTNAME", (2, 0), (2, -1), _FONT_BOLD),
                    ("FONTNAME", (1, 0), (1, -1), _FONT_NAME),
                    ("FONTNAME", (3, 0), (3, -1), _FONT_NAME),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (2, 0), (2, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.extend(
            [
                summary_table,
                Spacer(1, 4),
                Paragraph(
                    "Opening balance is based only on the transactions recorded "
                    "for this account.",
                    small_style,
                ),
                Spacer(1, 8),
            ]
        )

        table_data = [
            ["#", "Date", "Type", "Description", "Debit", "Credit", "Balance"]
        ]

        if statement.rows:
            for row in statement.rows:
                table_data.append(
                    [
                        str(row.sequence),
                        row.created_at.strftime("%Y-%m-%d %H:%M"),
                        Paragraph(escape(row.transaction_type), small_style),
                        Paragraph(escape(row.description), small_style),
                        _money(row.debit),
                        _money(row.credit),
                        _money(row.balance),
                    ]
                )
        else:
            table_data.append(
                ["", "", "", "No transactions recorded for this account.", "", "", ""]
            )

        report_table = Table(
            table_data,
            colWidths=[8 * mm, 28 * mm, 30 * mm, 32 * mm, 22 * mm, 22 * mm, 26 * mm],
            repeatRows=1,
        )

        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D91")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), _FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (1, 0), (3, -1), "LEFT"),
            ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]

        if not statement.rows:
            table_style.append(("SPAN", (0, 1), (-1, 1)))

        report_table.setStyle(TableStyle(table_style))
        elements.append(report_table)

        document.build(
            elements,
            onFirstPage=_draw_page_number,
            onLaterPages=_draw_page_number,
        )


def _money(value: Decimal) -> str:
    return f"{value:,.2f}"


def _draw_page_number(canvas, document):
    canvas.saveState()
    canvas.setFont(_FONT_NAME, 8)
    canvas.drawRightString(
        A4[0] - 18 * mm,
        10 * mm,
        f"Page {document.page}",
    )
    canvas.restoreState()
