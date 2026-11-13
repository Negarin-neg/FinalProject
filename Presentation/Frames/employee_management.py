from tkinter import Button, Frame, Label, messagebox
from tkinter.ttk import Treeview

from BusinessLogic.user_business_logic import UserBusinessLogic


class EmployeeManagement(Frame):
    """Employee list screen, available to administrators only."""

    def __init__(self, window, main_view, user_business: UserBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.user_business = user_business
        self.current_employee = None
        self.employees = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header_frame = Frame(self)
        self.header_frame.grid(row=0, column=0, pady=10, padx=10, sticky="ew")

        self.back_button = Button(
            self.header_frame, text="Back", command=self.back_button_clicked
        )
        self.back_button.grid(row=0, column=0, padx=(0, 10))

        self.title_label = Label(self.header_frame, text="Employee Management")
        self.title_label.grid(row=0, column=1, sticky="w")

        self.refresh_button = Button(
            self.header_frame, text="Refresh", command=self.refresh_button_clicked
        )
        self.refresh_button.grid(row=0, column=2, padx=(10, 0), sticky="e")

        self.header_frame.grid_columnconfigure(1, weight=1)

        self.employee_treeview = Treeview(
            self,
            columns=("first_name", "last_name", "username", "mobile", "role", "status"),
            selectmode="browse",
        )
        self.employee_treeview.grid(
            row=1, column=0, pady=(0, 10), padx=10, sticky="nsew"
        )

        self.employee_treeview.heading("#0", text="NO")
        self.employee_treeview.heading("#1", text="First Name")
        self.employee_treeview.heading("#2", text="Last Name")
        self.employee_treeview.heading("#3", text="Username")
        self.employee_treeview.heading("#4", text="Mobile")
        self.employee_treeview.heading("#5", text="Role")
        self.employee_treeview.heading("#6", text="Status")

        self.employee_treeview.column("#0", width=50, anchor="center")
        self.employee_treeview.column("#1", width=130, anchor="w")
        self.employee_treeview.column("#2", width=130, anchor="w")
        self.employee_treeview.column("#3", width=130, anchor="w")
        self.employee_treeview.column("#4", width=120, anchor="center")
        self.employee_treeview.column("#5", width=110, anchor="center")
        self.employee_treeview.column("#6", width=100, anchor="center")

        self.status_label = Label(self, text="", anchor="w")
        self.status_label.grid(row=2, column=0, pady=(0, 10), padx=10, sticky="ew")

    def load(self, current_employee):
        self.current_employee = current_employee
        self.status_label.config(text="")

        for child in self.employee_treeview.get_children(""):
            self.employee_treeview.delete(child)

        self.employees = {}

        response = self.user_business.get_employee_list(current_employee)

        if not response.success:
            messagebox.showerror("Employee Management", response.message)
            return

        employees = response.data or []

        for index, employee in enumerate(employees, start=1):
            self.employees[employee.id] = employee
            self.employee_treeview.insert(
                "",
                "end",
                iid=str(employee.id),
                text=str(index),
                values=(
                    employee.first_name,
                    employee.last_name,
                    employee.username,
                    _format_mobile(employee.mobile),
                    employee.role.name if employee.role else "-",
                    employee.status.name,
                ),
            )

        self.status_label.config(text=f"{len(employees)} employee(s) found.")

    def refresh_button_clicked(self):
        self.load(self.current_employee)

    def back_button_clicked(self):
        self.main_view.show_frame("home")


def _format_mobile(mobile) -> str:
    # Tk stores a purely numeric cell value as an integer, which drops the
    # leading zero of an Iranian mobile number. Grouping the digits keeps it
    # a string and is easier to read.
    mobile = str(mobile or "")

    if len(mobile) == 11 and mobile.isdigit():
        return f"{mobile[:4]} {mobile[4:7]} {mobile[7:]}"

    return mobile
