from tkinter import Button, Frame, Label, messagebox
from tkinter.ttk import Combobox, Treeview

from BusinessLogic.user_business_logic import UserBusinessLogic
from Common.Enums.employee_status import EmployeeStatus
from Common.Enums.role import Roles
from Presentation.Component.form_dialog import FormDialog

STATUS_NAMES = [status.name for status in EmployeeStatus]
ROLE_NAMES = [role.name.title() for role in Roles]


class EmployeeManagement(Frame):
    """Employee list screen, available to administrators only.

    The Status column holds a dropdown per employee so the administrator can
    change a status directly in the list; the change is written to the
    database immediately.
    """

    def __init__(self, window, main_view, user_business: UserBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.user_business = user_business
        self.current_employee = None
        self.employees = {}
        self.status_combos = {}
        self.last_message = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

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

        self.actions_frame = Frame(self)
        self.actions_frame.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="ew")

        self.create_employee_button = Button(
            self.actions_frame,
            text="Create Account",
            command=self.create_employee_button_clicked,
        )
        self.create_employee_button.grid(row=0, column=0, padx=(0, 10))

        self.update_employee_button = Button(
            self.actions_frame,
            text="Update",
            command=self.update_employee_button_clicked,
        )
        self.update_employee_button.grid(row=0, column=1, padx=(0, 10))

        self.delete_employee_button = Button(
            self.actions_frame,
            text="Delete Account",
            command=self.delete_employee_button_clicked,
        )
        self.delete_employee_button.grid(row=0, column=2)

        self.employee_treeview = Treeview(
            self,
            columns=("first_name", "last_name", "username", "mobile", "role", "status"),
            selectmode="browse",
        )
        self.employee_treeview.grid(
            row=2, column=0, pady=(0, 10), padx=10, sticky="nsew"
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
        self.employee_treeview.column("#6", width=120, anchor="center")

        self.status_label = Label(self, text="", anchor="w")
        self.status_label.grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")

        # The dropdowns are placed on top of the Status cells, so they have to
        # follow every scroll and resize of the table.
        self.employee_treeview.bind("<Configure>", self._position_status_combos)
        self.employee_treeview.bind("<MouseWheel>", self._position_status_combos)
        self.employee_treeview.bind("<Button-4>", self._position_status_combos)
        self.employee_treeview.bind("<Button-5>", self._position_status_combos)
        self.employee_treeview.bind("<KeyRelease>", self._position_status_combos)

    def load(self, current_employee):
        self.current_employee = current_employee
        self.status_label.config(text="")

        self._clear_status_combos()

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
                    _display_role(employee.role),
                    employee.status.name,
                ),
            )

        self._create_status_combos()

        self.status_label.config(text=f"{len(employees)} employee(s) found.")

    def refresh_button_clicked(self):
        self.load(self.current_employee)

    def back_button_clicked(self):
        self.main_view.show_frame("home")

    # ------------------------------------------------------------------
    # Status dropdowns
    # ------------------------------------------------------------------

    def _create_status_combos(self):
        if (
            self.current_employee is None
            or self.current_employee.role != Roles.ADMINISTRATOR
        ):
            return

        for employee_id, employee in self.employees.items():
            iid = str(employee_id)

            combo = Combobox(
                self.employee_treeview,
                values=STATUS_NAMES,
                state="readonly",
                width=10,
            )
            combo.set(employee.status.name)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda event, employee_id=employee_id, combo=combo: self._status_changed(
                    employee_id, combo
                ),
            )
            self.status_combos[iid] = combo

        # Let Tk finish the layout before reading the cell coordinates.
        self.after(50, self._position_status_combos)

    def _clear_status_combos(self):
        for combo in self.status_combos.values():
            combo.destroy()
        self.status_combos = {}

    def _position_status_combos(self, event=None):
        for iid, combo in self.status_combos.items():
            bbox = self.employee_treeview.bbox(iid, "status")

            if bbox:
                x, y, width, height = bbox
                combo.place(x=x, y=y, width=width, height=height)
                combo.lift()
            else:
                combo.place_forget()

    def _status_changed(self, employee_id, combo):
        employee = self.employees.get(employee_id)
        new_status = combo.get()

        response = self.user_business.update_employee_status(
            self.current_employee, employee_id, new_status
        )

        if not response.success:
            # Put the previous value back so the list never shows a change
            # that was not saved.
            if employee is not None:
                combo.set(employee.status.name)
            messagebox.showerror("Employee Management", response.message)
            return

        if employee is not None:
            employee.status = response.data.status

        self.employee_treeview.set(str(employee_id), "status", response.data.status.name)
        self.status_label.config(text=response.message)

    # ------------------------------------------------------------------
    # Create / update / delete
    # ------------------------------------------------------------------

    def create_employee_button_clicked(self):
        dialog = FormDialog(
            self,
            "Create Account",
            self._employee_fields(),
            self._create_employee_submit,
            submit_text="Create",
        )

        if dialog.show() is not None:
            self.load(self.current_employee)
            messagebox.showinfo("Create Account", self.last_message)

    def _create_employee_submit(self, values):
        response = self.user_business.create_employee(
            self.current_employee,
            values["first_name"],
            values["last_name"],
            values["mobile"],
            values["username"],
            values["password"],
            values["role"],
            values["status"],
        )

        self.last_message = response.message
        return response.success, response.message

    def update_employee_button_clicked(self):
        employee = self.selected_employee()
        if employee is None:
            return

        initial = {
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "username": employee.username,
            "mobile": employee.mobile or "",
            "password": "",
            "role": _display_role(employee.role),
            "status": employee.status.name,
        }

        dialog = FormDialog(
            self,
            "Update Employee",
            self._employee_fields(password_label="Password (leave empty to keep)"),
            lambda values: self._update_employee_submit(employee.id, values),
            initial=initial,
            submit_text="Update",
        )

        if dialog.show() is not None:
            self.load(self.current_employee)
            messagebox.showinfo("Update Employee", self.last_message)

    def _update_employee_submit(self, employee_id, values):
        response = self.user_business.update_employee(
            self.current_employee,
            employee_id,
            values["first_name"],
            values["last_name"],
            values["mobile"],
            values["username"],
            values["role"],
            values["status"],
            values["password"],
        )

        self.last_message = response.message
        return response.success, response.message

    def delete_employee_button_clicked(self):
        employee = self.selected_employee()
        if employee is None:
            return

        if not messagebox.askyesno(
            "Delete Account",
            f'Are you sure you want to delete "{employee.get_fullname()}"?',
        ):
            return

        response = self.user_business.delete_employee(
            self.current_employee, employee.id
        )

        if not response.success:
            messagebox.showerror("Delete Account", response.message)
            return

        self.load(self.current_employee)
        messagebox.showinfo("Delete Account", response.message)

    def selected_employee(self):
        selection = self.employee_treeview.selection()
        if not selection:
            messagebox.showinfo(
                "Employee Management",
                "Please select an employee from the list first.",
            )
            return None

        employee = self.employees.get(int(selection[0]))
        if employee is None:
            messagebox.showinfo(
                "Employee Management",
                "The selected employee is no longer available. Please refresh the list.",
            )
        return employee

    @staticmethod
    def _employee_fields(password_label: str = "Password"):
        return [
            {"key": "first_name", "label": "First Name"},
            {"key": "last_name", "label": "Last Name"},
            {"key": "username", "label": "Username"},
            {"key": "mobile", "label": "Mobile"},
            {"key": "password", "label": password_label, "show": "*"},
            {"key": "role", "label": "Role", "values": ROLE_NAMES},
            {"key": "status", "label": "Status", "values": STATUS_NAMES},
        ]


def _display_role(role) -> str:
    return role.name.title() if role else "-"


def _format_mobile(mobile) -> str:
    # Tk stores a purely numeric cell value as an integer, which drops the
    # leading zero of an Iranian mobile number. Grouping the digits keeps it
    # a string and is easier to read.
    mobile = str(mobile or "")

    if len(mobile) == 11 and mobile.isdigit():
        return f"{mobile[:4]} {mobile[4:7]} {mobile[7:]}"

    return mobile
