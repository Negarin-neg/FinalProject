from __future__ import annotations

from tkinter import Frame, Label, Button, messagebox
from typing import TYPE_CHECKING

from Common.Entities.employee import Employee
from Common.Enums.role import Roles
from Presentation.Component.photo_view import PhotoView

if TYPE_CHECKING:
    from Presentation.main_view import MainView


class HomeFrame(Frame):
    def __init__(self, window, main_view: MainView):
        super().__init__(window)

        self.grid_columnconfigure(0, weight=1)

        self.main_view = main_view
        self.current_employee = None

        self.photo_view = PhotoView(self, size=72)
        self.photo_view.grid(row=0, column=0, pady=(15, 5))

        self.header_label = Label(self)
        self.header_label.grid(row=1, column=0, pady=(0, 10), padx=10)

        # Which of these two buttons is visible depends on the role
        # (see set_current_employee).
        self.employee_management = Button(self, text="Employee Management", command=self.not_implemented_clicked)

        self.account_management = Button(self, text="Account Management", command=self.account_management_clicked)

        self.profile_management = Button(self, text="My Profile", command=self.profile_button_clicked)
        self.profile_management.grid(row=4, column=0, pady=(0, 10), padx=10, sticky="ew")

        self.logout_button = Button(self, text="Logout", command=self.logout_button_clicked)
        self.logout_button.grid(row=5, column=0, pady=(0, 10), padx=10, sticky="ew")

    def set_current_employee(self, current_employee: Employee):
        self.current_employee = current_employee

        role_name = self.current_employee.role.name if self.current_employee.role else "No role"
        self.header_label.config(
            text=f"Welcome {self.current_employee.get_fullname()} ({role_name})")

        # Show the employee's stored photo (or the placeholder when absent).
        photo_bytes = self.main_view.user_business.get_profile_photo(self.current_employee.id)
        self.photo_view.set_photo(photo_bytes)
        self.main_view.account_api_client.set_employee(self.current_employee.id)

        match self.current_employee.role:
            case Roles.ADMINISTRATOR:
                self.employee_management.grid(row=2, column=0, pady=(0, 10), padx=10, sticky="ew")
                # Administrators also need the customer/account list, so the
                # reference layout is extended with the same account screen.
                self.account_management.grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")
            case Roles.BANKER:
                self.employee_management.grid_forget()
                self.account_management.grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")
            case _:
                self.employee_management.grid_forget()
                self.account_management.grid_forget()

    def profile_button_clicked(self):
        profile_frame = self.main_view.show_frame("profile")
        profile_frame.load(self.current_employee)

    def not_implemented_clicked(self):
        messagebox.showinfo("Coming soon", "This section is not implemented yet.")

    def account_management_clicked(self):
        account_management = self.main_view.show_frame("account_management")
        account_management.load_account_list()

    def logout_button_clicked(self):
        self.current_employee = None
        self.photo_view.set_photo(None)
        self.main_view.account_api_client.clear_employee()
        self.main_view.show_frame("login")
