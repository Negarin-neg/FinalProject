from tkinter import Frame, Label, Entry, Button, messagebox
from Presentation.Component.password_entry import PasswordEntry
from BusinessLogic.user_business_logic import UserBusinessLogic


class RegisterFrame(Frame):
    def __init__(self, window, main_view, user_business: UserBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.user_business = user_business

        self.grid_columnconfigure(1, weight=1)

        self.firstname_label = Label(self, text="First Name")
        self.firstname_label.grid(row=0, column=0, pady=10, padx=10, sticky="e")

        self.firstname_entry = Entry(self)
        self.firstname_entry.grid(row=0, column=1, pady=10, padx=(0, 10), sticky="ew")

        self.lastname_label = Label(self, text="Last Name")
        self.lastname_label.grid(row=1, column=0, pady=(0, 10), padx=(0, 10), sticky="e")

        self.lastname_entry = Entry(self)
        self.lastname_entry.grid(row=1, column=1, pady=(0, 10), padx=(0, 10), sticky="ew")

        self.mobile_label = Label(self, text="Mobile")
        self.mobile_label.grid(row=2, column=0, pady=(0, 10), padx=(0, 10), sticky="e")

        self.mobile_entry = Entry(self)
        self.mobile_entry.grid(row=2, column=1, pady=(0, 10), padx=(0, 10), sticky="ew")

        self.username_label = Label(self, text="Username")
        self.username_label.grid(row=3, column=0, pady=(0, 10), padx=(0, 10), sticky="e")

        self.username_entry = Entry(self)
        self.username_entry.grid(row=3, column=1, pady=(0, 10), padx=(0, 10), sticky="ew")

        self.password_label = Label(self, text="Password")
        self.password_label.grid(row=4, column=0, pady=(0, 10), padx=(0, 10), sticky="e")

        self.password_entry = PasswordEntry(self)
        self.password_entry.grid(row=4, column=1, pady=(0, 10), padx=(0, 10), sticky="ew")

        self.password_hint_label = Label(
            self,
            text="At least 8 characters, with upper and lower case letters and one of @ . /",
            fg="gray",
            wraplength=250,
            justify="left",
        )
        self.password_hint_label.grid(row=5, column=1, pady=(0, 10), padx=(0, 10), sticky="w")

        self.register_button = Button(self, text="Register", command=self.register_button_clicked)
        self.register_button.grid(row=6, column=1, pady=(0, 10), padx=(0, 10), sticky="w")

        self.back_button = Button(self, text="Back to Login Page", command=self.back_button_clicked)
        self.back_button.grid(row=7, column=1, pady=(0, 10), padx=(0, 10), sticky="w")

    def register_button_clicked(self):
        response = self.user_business.register(
            self.firstname_entry.get(),
            self.lastname_entry.get(),
            self.mobile_entry.get(),
            self.username_entry.get(),
            self.password_entry.get_value(),
        )

        if response.success:
            messagebox.showinfo("Register", response.message)
            self.clear_fields()
            self.main_view.show_frame("login")
        else:
            messagebox.showerror("Registration Failed", response.message)

    def back_button_clicked(self):
        self.main_view.show_frame("login")

    def clear_fields(self):
        self.firstname_entry.delete(0, "end")
        self.lastname_entry.delete(0, "end")
        self.mobile_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        self.password_entry.clear()
