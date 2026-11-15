from tkinter import Button, Entry, Frame, Label, messagebox
from tkinter.ttk import Treeview

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Presentation.Component.form_dialog import FormDialog
from Presentation.Component.statement_export import export_statement


class AccountManagement(Frame):
    """Customer/account list screen matching the Core Banking reference.

    The layout intentionally follows the instructor's AccountManagement frame:
    search box, action buttons on one row, and a table with NO, Account Number,
    Opening Date and Owner. Administrators and employees can create, update and
    delete customer accounts from here; PDF statement export is also available.
    """

    def __init__(self, window, main_view, account_business: AccountBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.account_business = account_business
        self.current_employee = None
        self.accounts = {}
        self.last_message = ""

        for column in range(5):
            self.grid_columnconfigure(column, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.back_button = Button(self, text="Back", command=self.back_button_clicked)
        self.back_button.grid(row=0, column=0, pady=10, padx=10, sticky="ew")

        self.search_entry = Entry(self, justify="left")
        self.search_entry.grid(
            row=0, column=1, columnspan=3, pady=10, padx=10, sticky="ew"
        )
        self.search_entry.bind("<Return>", lambda event: self.search_button_clicked())

        self.search_button = Button(self, text="Search", command=self.search_button_clicked)
        self.search_button.grid(row=0, column=4, pady=10, padx=(0, 10), sticky="ew")

        self.create_account_button = Button(
            self, text="Create Account", command=self.create_account_button_clicked
        )
        self.create_account_button.grid(
            row=1, column=0, pady=(0, 10), padx=10, sticky="ew"
        )

        self.update_account_button = Button(
            self, text="Update Account", command=self.update_account_button_clicked
        )
        self.update_account_button.grid(
            row=1, column=1, pady=(0, 10), padx=10, sticky="ew"
        )

        self.delete_account_button = Button(
            self, text="Delete Account", command=self.delete_account_button_clicked
        )
        self.delete_account_button.grid(
            row=1, column=2, pady=(0, 10), padx=10, sticky="ew"
        )

        self.transaction_account_button = Button(
            self,
            text="Transaction Account",
            command=self.transaction_account_button_clicked,
        )
        self.transaction_account_button.grid(
            row=1, column=3, pady=(0, 10), padx=10, sticky="ew"
        )

        self.export_statement_button = Button(
            self,
            text="Export Statement",
            command=self.export_statement_button_clicked,
        )
        self.export_statement_button.grid(
            row=1, column=4, pady=(0, 10), padx=10, sticky="ew"
        )

        self.account_treeview = Treeview(
            self,
            columns=("account_number", "opening_date", "owner"),
        )
        self.account_treeview.grid(
            row=2, column=0, columnspan=5, pady=(0, 10), padx=10, sticky="nsew"
        )

        self.account_treeview.heading("#0", text="NO")
        self.account_treeview.heading("#1", text="Account Number")
        self.account_treeview.heading("#2", text="Opening Date")
        self.account_treeview.heading("#3", text="Owner")

        self.account_treeview.column("#0", width=60, anchor="center")
        self.account_treeview.column("#1", width=180, anchor="w")
        self.account_treeview.column("#2", width=150, anchor="center")
        self.account_treeview.column("#3", width=260, anchor="w")

        self.status_label = Label(self, text="", anchor="w")
        self.status_label.grid(
            row=3, column=0, columnspan=5, pady=(0, 10), padx=10, sticky="ew"
        )

        self.account_treeview.bind(
            "<Double-1>", lambda event: self.transaction_account_button_clicked()
        )

    def load(self, current_employee, search: str = ""):
        self.current_employee = current_employee
        self.load_account_list(search)

    def load_account_list(self, search: str = ""):
        for child in self.account_treeview.get_children(""):
            self.account_treeview.delete(child)

        self.accounts = {}
        self.status_label.config(text="")

        response = self.account_business.get_account_list(search)

        if not response.success:
            messagebox.showerror("Customer Accounts", response.message)
            return

        accounts = response.data or []

        for index, account in enumerate(accounts, start=1):
            self.accounts[account.id] = account
            self.account_treeview.insert(
                "",
                "end",
                iid=str(account.id),
                text=str(index),
                values=(
                    account.account_number,
                    account.opening_date.strftime("%Y-%m-%d"),
                    account.owner_customer.get_fullname(),
                ),
            )

        if not accounts:
            self.status_label.config(text="No customer accounts were found.")

    def search_button_clicked(self):
        self.load_account_list(self.search_entry.get().strip())

    # ------------------------------------------------------------------
    # Create / update / delete
    # ------------------------------------------------------------------

    def create_account_button_clicked(self):
        fields = [
            {"key": "first_name", "label": "First Name"},
            {"key": "last_name", "label": "Last Name"},
            {
                "key": "account_number",
                "label": "Account Number\n(leave empty to generate)",
            },
        ]

        dialog = FormDialog(
            self,
            "Create Account",
            fields,
            self._create_account_submit,
            submit_text="Create",
        )

        if dialog.show() is not None:
            self.load_account_list(self.search_entry.get().strip())
            messagebox.showinfo("Create Account", self.last_message)

    def _create_account_submit(self, values):
        response = self.account_business.create_account(
            self.current_employee,
            values["first_name"],
            values["last_name"],
            values["account_number"],
        )

        self.last_message = response.message
        return response.success, response.message

    def update_account_button_clicked(self):
        account = self.selected_account()
        if account is None:
            return

        initial = {
            "first_name": account.owner_customer.first_name,
            "last_name": account.owner_customer.last_name or "",
            "account_number": account.account_number,
        }

        fields = [
            {"key": "first_name", "label": "First Name"},
            {"key": "last_name", "label": "Last Name"},
            {"key": "account_number", "label": "Account Number"},
        ]

        dialog = FormDialog(
            self,
            "Update Account",
            fields,
            lambda values: self._update_account_submit(account.id, values),
            initial=initial,
            submit_text="Update",
        )

        if dialog.show() is not None:
            self.load_account_list(self.search_entry.get().strip())
            messagebox.showinfo("Update Account", self.last_message)

    def _update_account_submit(self, account_id, values):
        response = self.account_business.update_account(
            self.current_employee,
            account_id,
            values["first_name"],
            values["last_name"],
            values["account_number"],
        )

        self.last_message = response.message
        return response.success, response.message

    def delete_account_button_clicked(self):
        account = self.selected_account()
        if account is None:
            return

        owner_name = account.owner_customer.get_fullname()

        if not messagebox.askyesno(
            "Delete Account",
            f'Are you sure you want to delete "{owner_name}"?',
        ):
            return

        response = self.account_business.delete_account(
            self.current_employee, account.id
        )

        if not response.success:
            messagebox.showerror("Delete Account", response.message)
            return

        self.load_account_list(self.search_entry.get().strip())
        messagebox.showinfo("Delete Account", response.message)

    def transaction_account_button_clicked(self):
        account = self.selected_account()
        if account is None:
            return

        transactions_frame = self.main_view.show_frame("transactions")
        transactions_frame.load(account, self.current_employee)

    def export_statement_button_clicked(self):
        account = self.selected_account()
        if account is None:
            return

        export_statement(account, self.account_business)

    def back_button_clicked(self):
        self.main_view.show_frame("home")

    def selected_account(self):
        selection = self.account_treeview.selection()
        if not selection:
            messagebox.showinfo(
                "Customer Accounts",
                "Please select an account from the list first.",
            )
            return None

        account = self.accounts.get(int(selection[0]))
        if account is None:
            messagebox.showinfo(
                "Customer Accounts",
                "The selected account is no longer available. Please refresh the list.",
            )
        return account
