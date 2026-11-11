from __future__ import annotations

from tkinter import Frame, Label, Entry, Button, messagebox, filedialog
from typing import TYPE_CHECKING

from BusinessLogic.user_business_logic import UserBusinessLogic
from Common.Entities.employee import Employee
from Presentation.Component.password_entry import PasswordEntry
from Presentation.Component.photo_view import PhotoView

if TYPE_CHECKING:
    from Presentation.main_view import MainView


class ProfileFrame(Frame):
    def __init__(self, window, main_view: MainView, user_business: UserBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.user_business = user_business

        self.employee = None

        self.grid_columnconfigure(2, weight=1)

        # ---- left column: the photo ----
        self.photo_view = PhotoView(self, size=150)
        self.photo_view.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="n")

        self.photo_buttons_frame = Frame(self)
        self.photo_buttons_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="n")

        self.upload_photo_button = Button(
            self.photo_buttons_frame, text="Upload Photo", command=self.upload_photo_button_clicked
        )
        self.upload_photo_button.grid(row=0, column=0, pady=(0, 5), sticky="ew")

        self.remove_photo_button = Button(
            self.photo_buttons_frame, text="Remove Photo", command=self.remove_photo_button_clicked
        )
        self.remove_photo_button.grid(row=1, column=0, sticky="ew")

        # ---- right columns: the information ----
        self.firstname_entry = self._add_entry_row(0, "First Name", top_padding=15)
        self.lastname_entry = self._add_entry_row(1, "Last Name")
        self.mobile_entry = self._add_entry_row(2, "Mobile")
        self.username_entry = self._add_entry_row(3, "Username")

        self.role_label = Label(self, text="Role")
        self.role_label.grid(row=4, column=1, pady=(0, 10), padx=(0, 10), sticky="e")

        self.role_value_label = Label(self, text="", anchor="w")
        self.role_value_label.grid(row=4, column=2, pady=(0, 10), padx=(0, 15), sticky="ew")

        self.password_section_label = Label(self, text="Change password (leave empty to keep the current one)", fg="gray")
        self.password_section_label.grid(row=5, column=1, columnspan=2, pady=(5, 5), padx=(0, 15), sticky="w")

        self.current_password_label = Label(self, text="Current Password")
        self.current_password_label.grid(row=6, column=1, pady=(0, 10), padx=(0, 10), sticky="e")

        self.current_password_entry = PasswordEntry(self)
        self.current_password_entry.grid(row=6, column=2, pady=(0, 10), padx=(0, 15), sticky="ew")

        self.new_password_label = Label(self, text="New Password")
        self.new_password_label.grid(row=7, column=1, pady=(0, 10), padx=(0, 10), sticky="e")

        self.new_password_entry = PasswordEntry(self)
        self.new_password_entry.grid(row=7, column=2, pady=(0, 10), padx=(0, 15), sticky="ew")

        self.password_hint_label = Label(
            self,
            text="At least 8 characters, with upper and lower case letters and one of @ . /",
            fg="gray",
            wraplength=300,
            justify="left",
        )
        self.password_hint_label.grid(row=8, column=2, pady=(0, 10), padx=(0, 15), sticky="w")

        self.buttons_frame = Frame(self)
        self.buttons_frame.grid(row=9, column=1, columnspan=2, pady=(0, 15), padx=(0, 15), sticky="w")

        self.save_button = Button(self.buttons_frame, text="Save Changes", command=self.save_button_clicked)
        self.save_button.grid(row=0, column=0, padx=(0, 10))

        self.back_button = Button(self.buttons_frame, text="Back to Home", command=self.back_button_clicked)
        self.back_button.grid(row=0, column=1)

    def _add_entry_row(self, row: int, text: str, top_padding: int = 0):
        label = Label(self, text=text)
        label.grid(row=row, column=1, pady=(top_padding, 10), padx=(0, 10), sticky="e")

        entry = Entry(self)
        entry.grid(row=row, column=2, pady=(top_padding, 10), padx=(0, 15), sticky="ew")
        return entry

    def load(self, employee: Employee):
        """Called by HomeFrame when My Profile is clicked."""
        response = self.user_business.get_profile(employee.id)

        if not response.success:
            messagebox.showerror("My Profile", response.message)
            self.main_view.show_frame("home")
            return

        self.employee = response.data
        self._fill_fields()

    def _fill_fields(self):
        for entry, value in (
            (self.firstname_entry, self.employee.first_name),
            (self.lastname_entry, self.employee.last_name),
            (self.mobile_entry, self.employee.mobile or ""),
            (self.username_entry, self.employee.username),
        ):
            entry.delete(0, "end")
            entry.insert(0, value)

        self.role_value_label.config(text=self.employee.role.name if self.employee.role else "No role")

        self.current_password_entry.clear()
        self.new_password_entry.clear()

        self._refresh_photo()

    def _refresh_photo(self):
        photo_bytes = self.user_business.get_profile_photo(self.employee.id)
        self.photo_view.set_photo(photo_bytes)

    def save_button_clicked(self):
        response = self.user_business.update_profile(
            self.employee.id,
            self.firstname_entry.get(),
            self.lastname_entry.get(),
            self.mobile_entry.get(),
            self.username_entry.get(),
            self.current_password_entry.get_value(),
            self.new_password_entry.get_value(),
        )

        if response.success:
            self.employee = response.data
            self._fill_fields()

            # the Home page header/photo must show the new data too
            self.main_view.get_frame("home").set_current_employee(self.employee)

            messagebox.showinfo("My Profile", response.message)
        else:
            messagebox.showerror("My Profile", response.message)

    def back_button_clicked(self):
        self.main_view.show_frame("home")

    def upload_photo_button_clicked(self):
        file_path = filedialog.askopenfilename(
            title="Select a profile photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as photo_file:
                file_bytes = photo_file.read()
        except OSError:
            messagebox.showerror("My Profile", "خواندن فایل انتخاب‌شده ناموفق بود.")
            return

        response = self.user_business.upload_profile_photo(self.employee.id, file_bytes, file_path)

        if response.success:
            self.employee = response.data
            self._refresh_photo()
            # keep the Home page photo in sync
            self.main_view.get_frame("home").set_current_employee(self.employee)
            messagebox.showinfo("My Profile", response.message)
        else:
            messagebox.showerror("My Profile", response.message)

    def remove_photo_button_clicked(self):
        response = self.user_business.remove_profile_photo(self.employee.id)

        if response.success:
            self.employee = response.data
            self._refresh_photo()
            self.main_view.get_frame("home").set_current_employee(self.employee)
            messagebox.showinfo("My Profile", response.message)
        else:
            messagebox.showerror("My Profile", response.message)
