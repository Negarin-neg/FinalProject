from __future__ import annotations

from tkinter import Frame, Label, Entry, Button, messagebox
from typing import TYPE_CHECKING

from Common.Enums.error_code import ErrorCode
from BusinessLogic.user_business_logic import UserBusinessLogic

if TYPE_CHECKING:
    from Presentation.main_view import MainView

# How often the on-screen countdown ticks. The real expiry is enforced on the
# server (OtpService), this is only for the user's convenience.
COUNTDOWN_TICK_MS = 1000


class OtpFrame(Frame):
    """Confirms the one-time code that protects first-time registration."""

    def __init__(self, window, main_view: MainView, user_business: UserBusinessLogic):
        super().__init__(window)

        self.main_view = main_view
        self.user_business = user_business

        self.mobile = None
        self.seconds_left = 0
        self._tick_job = None

        self.grid_columnconfigure(1, weight=1)

        self.title_label = Label(self, text="OTP Verification")
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(15, 5), padx=10)

        self.info_label = Label(self, text="", fg="gray", wraplength=280, justify="center")
        self.info_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), padx=10)

        self.code_label = Label(self, text="Verification Code")
        self.code_label.grid(row=2, column=0, pady=(0, 10), padx=10, sticky="e")

        self.code_entry = Entry(self, justify="center")
        self.code_entry.grid(row=2, column=1, pady=(0, 10), padx=(0, 10), sticky="ew")
        self.code_entry.bind("<Return>", lambda event: self.verify_button_clicked())

        self.countdown_label = Label(self, text="", fg="gray")
        self.countdown_label.grid(row=3, column=0, columnspan=2, pady=(0, 10), padx=10)

        self.verify_button = Button(self, text="Verify", command=self.verify_button_clicked)
        self.verify_button.grid(row=4, column=1, pady=(0, 10), padx=(0, 10), sticky="w")

        self.resend_button = Button(self, text="Resend Code", command=self.resend_button_clicked)
        self.resend_button.grid(row=5, column=1, pady=(0, 10), padx=(0, 10), sticky="w")

        self.back_button = Button(self, text="Back to Registration", command=self.back_button_clicked)
        self.back_button.grid(row=6, column=1, pady=(0, 15), padx=(0, 10), sticky="w")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, mobile: str):
        """Called by RegisterFrame right after the first code was sent."""
        self.mobile = mobile
        self.info_label.config(text=f"کد تأیید به شماره {mobile} ارسال شد.")
        self.code_entry.delete(0, "end")
        self._restart_countdown()
        self.code_entry.focus_set()

    def _stop_countdown(self):
        if self._tick_job is not None:
            self.after_cancel(self._tick_job)
            self._tick_job = None

    def _restart_countdown(self):
        self._stop_countdown()
        remaining = self.user_business.otp_service.remaining_seconds(self.mobile)
        self.seconds_left = remaining if remaining > 0 else 120
        self._update_countdown_label()
        self._tick()

    def _tick(self):
        if self.seconds_left <= 0:
            self.countdown_label.config(text="زمان کد به پایان رسید. کد جدید بگیرید.", fg="#b00020")
            self._tick_job = None
            return

        self.seconds_left -= 1
        self._update_countdown_label()
        self._tick_job = self.after(COUNTDOWN_TICK_MS, self._tick)

    def _update_countdown_label(self):
        minutes, seconds = divmod(max(0, self.seconds_left), 60)
        self.countdown_label.config(
            text=f"اعتبار کد: {minutes:02d}:{seconds:02d}",
            fg="gray",
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def verify_button_clicked(self):
        code = self.code_entry.get().strip()

        if not code:
            messagebox.showerror("OTP", "کد تأیید را وارد کنید.")
            return

        response = self.user_business.verify_registration_otp(self.mobile, code)

        if response.success:
            self._stop_countdown()
            messagebox.showinfo("OTP", response.message)
            # Clear the registration form now that the account really exists.
            self.main_view.get_frame("register").clear_fields()
            self.main_view.show_frame("login")
            return

        messagebox.showerror("OTP", response.message)
        self.code_entry.delete(0, "end")

        if response.error_code in (
            ErrorCode.OTP_EXPIRED,
            ErrorCode.OTP_TOO_MANY_ATTEMPTS,
            ErrorCode.OTP_NOT_FOUND,
        ):
            # These need a brand new code, so stop pretending the old one is
            # still counting down.
            self._stop_countdown()
            self.countdown_label.config(text="کد جدید بگیرید.", fg="#b00020")

    def resend_button_clicked(self):
        response = self.user_business.resend_registration_otp(self.mobile)

        if response.success:
            messagebox.showinfo("OTP", response.message)
            self.code_entry.delete(0, "end")
            self._restart_countdown()
        else:
            messagebox.showerror("OTP", response.message)

    def back_button_clicked(self):
        self._stop_countdown()
        self.main_view.show_frame("register")
