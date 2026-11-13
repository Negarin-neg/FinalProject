from tkinter import Button, Frame, Label, messagebox
from tkinter.ttk import Treeview

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Presentation.Component.statement_export import export_statement


class TransactionManagement(Frame):
    """Statement screen for one selected account."""

    def __init__(self, window, main_view, account_business: AccountBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.account_business = account_business
        self.account = None
        self.statement = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.account_label = Label(self, text="No account selected", anchor="w")
        self.account_label.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="ew")

        self.buttons_frame = Frame(self)
        self.buttons_frame.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="ew")

        self.export_button = Button(
            self.buttons_frame,
            text="Export Statement",
            command=self.export_button_clicked,
        )
        self.export_button.grid(row=0, column=0, padx=(0, 10))

        self.back_button = Button(
            self.buttons_frame,
            text="Back to Accounts",
            command=self.back_button_clicked,
        )
        self.back_button.grid(row=0, column=1)

        self.transaction_treeview = Treeview(
            self,
            columns=("date", "type", "description", "debit", "credit", "balance"),
            selectmode="browse",
        )
        self.transaction_treeview.grid(
            row=2, column=0, pady=(0, 10), padx=10, sticky="nsew"
        )

        self.transaction_treeview.heading("#0", text="NO")
        self.transaction_treeview.heading("#1", text="Date")
        self.transaction_treeview.heading("#2", text="Type")
        self.transaction_treeview.heading("#3", text="Description")
        self.transaction_treeview.heading("#4", text="Debit")
        self.transaction_treeview.heading("#5", text="Credit")
        self.transaction_treeview.heading("#6", text="Balance")

        self.transaction_treeview.column("#0", width=50, anchor="center")
        self.transaction_treeview.column("#1", width=130, anchor="center")
        self.transaction_treeview.column("#2", width=140, anchor="w")
        self.transaction_treeview.column("#3", width=150, anchor="w")
        self.transaction_treeview.column("#4", width=90, anchor="e")
        self.transaction_treeview.column("#5", width=90, anchor="e")
        self.transaction_treeview.column("#6", width=100, anchor="e")

        self.status_label = Label(self, text="", anchor="w")
        self.status_label.grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")

    def load(self, account):
        self.account = account
        self.statement = None
        self.account_label.config(
            text=(
                f"Account {account.account_number} - "
                f"{account.owner_customer.get_fullname()}"
            )
        )

        for child in self.transaction_treeview.get_children(""):
            self.transaction_treeview.delete(child)

        self.status_label.config(text="")

        response = self.account_business.get_statement(account.id)

        if not response.success:
            messagebox.showerror("Account Statement", response.message)
            return

        statement = response.data
        self.statement = statement

        for row in statement.rows:
            self.transaction_treeview.insert(
                "",
                "end",
                text=str(row.sequence),
                values=(
                    row.created_at.strftime("%Y-%m-%d %H:%M"),
                    row.transaction_type,
                    row.description,
                    f"{row.debit:,.2f}",
                    f"{row.credit:,.2f}",
                    f"{row.balance:,.2f}",
                ),
            )

        self.status_label.config(
            text=(
                f"Opening balance: {statement.opening_balance:,.2f}    "
                f"Total debits: {statement.total_debits:,.2f}    "
                f"Total credits: {statement.total_credits:,.2f}    "
                f"Closing balance: {statement.closing_balance:,.2f}"
            )
        )

        if not statement.rows:
            self.status_label.config(
                text=(
                    f"No transactions recorded for this account. "
                    f"Closing balance: {statement.closing_balance:,.2f}"
                )
            )

    def export_button_clicked(self):
        if self.account is None:
            messagebox.showinfo("Export Statement", "Please select an account first.")
            return

        export_statement(self.account, self.account_business)

    def back_button_clicked(self):
        account_management = self.main_view.show_frame("account_management")
        account_management.load_account_list()
