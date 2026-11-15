from tkinter import Button, Entry, Frame, Label, Toplevel, messagebox
from tkinter.ttk import Combobox


class FormDialog(Toplevel):
    """Small modal form shared by the management screens.

    `fields` is a list of dictionaries describing one input per row:

        {"key": "first_name", "label": "First Name"}
        {"key": "role", "label": "Role", "values": ["Administrator", "Banker"]}
        {"key": "password", "label": "Password", "show": "*"}

    `on_submit(values)` must return `(True, message)` to close the dialog, or
    `(False, message)` to show the error and keep the dialog open.
    """

    def __init__(
        self,
        parent,
        title: str,
        fields,
        on_submit,
        initial=None,
        submit_text: str = "Save",
    ):
        super().__init__(parent)

        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())

        self.on_submit = on_submit
        self.result = None
        self.widgets = {}

        initial = initial or {}

        for row, field in enumerate(fields):
            top_padding = 14 if row == 0 else 8

            Label(self, text=field["label"]).grid(
                row=row, column=0, pady=(top_padding, 0), padx=(15, 10), sticky="e"
            )

            if field.get("values"):
                widget = Combobox(self, values=field["values"], state="readonly", width=28)
                widget.set(initial.get(field["key"]) or field["values"][0])
            else:
                widget = Entry(self, width=30, show=field.get("show", ""))
                value = initial.get(field["key"])
                if value is not None:
                    widget.insert(0, str(value))

            widget.grid(
                row=row, column=1, pady=(top_padding, 0), padx=(0, 15), sticky="ew"
            )
            self.widgets[field["key"]] = widget

        buttons_frame = Frame(self)
        buttons_frame.grid(
            row=len(fields), column=0, columnspan=2, pady=(16, 12), padx=15, sticky="e"
        )

        Button(buttons_frame, text=submit_text, command=self.submit).grid(
            row=0, column=0, padx=(0, 8)
        )
        Button(buttons_frame, text="Cancel", command=self.destroy).grid(row=0, column=1)

        self.bind("<Return>", lambda event: self.submit())
        self.bind("<Escape>", lambda event: self.destroy())

        self.grab_set()
        self._center(parent)

        first_widget = next(iter(self.widgets.values()), None)
        if first_widget is not None:
            first_widget.focus_set()

    def submit(self):
        values = {key: widget.get() for key, widget in self.widgets.items()}
        success, message = self.on_submit(values)

        if success:
            self.result = values
            self.destroy()
        else:
            messagebox.showerror(self.title(), message)

    def show(self):
        """Blocks until the dialog is closed; returns the values or None."""
        self.wait_window()
        return self.result

    def _center(self, parent):
        self.update_idletasks()

        root = parent.winfo_toplevel()
        x = root.winfo_rootx() + (root.winfo_width() - self.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - self.winfo_height()) // 3

        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
