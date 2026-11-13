from Presentation.window import Window
from Presentation.Frames.login import LoginFrame
from Presentation.Frames.register import RegisterFrame
from Presentation.Frames.otp import OtpFrame
from Presentation.Frames.home import HomeFrame
from Presentation.Frames.profile import ProfileFrame
from Presentation.Frames.account_management import AccountManagement
from Presentation.Frames.employee_management import EmployeeManagement
from Presentation.Frames.transactions import TransactionManagement
from tkinter import Frame




class MainView:
    def __init__(self, user_business, account_business):
        self.frames = {}
        self.user_business = user_business
        self.account_business = account_business

        self.window = Window("Core Banking")



        self.add_frame("home", HomeFrame(self.window, self), 400, 400)
        self.add_frame("profile", ProfileFrame(self.window, self, user_business), 680, 570)
        self.add_frame(
            "transactions",
            TransactionManagement(self.window, self, account_business),
            900,
            520,
        )
        self.add_frame(
            "account_management",
            AccountManagement(self.window, self, account_business),
            900,
            520,
        )
        self.add_frame(
            "employee_management",
            EmployeeManagement(self.window, self, user_business),
            900,
            520,
        )
        self.add_frame("register", RegisterFrame(self.window, self, user_business), 420, 420)
        self.add_frame("otp", OtpFrame(self.window, self, user_business), 380, 320)
        self.add_frame("login", LoginFrame(self.window, self,user_business), 400, 300)

        self.show_frame("login")

        self.window.show()

    def add_frame(self, frame_name: str, frame: Frame, width, height):
        self.frames[frame_name] = (frame, width, height)
        self.frames[frame_name][0].grid(row=0, column=0, sticky="nsew")

    def show_frame(self, frame_name: str):
        current_frame_value = self.frames[frame_name]
        current_frame_value[0].tkraise()

        width, height = current_frame_value[1], current_frame_value[2]

        self.window.resize(width, height)

        return current_frame_value[0]

    def get_frame(self, frame_name: str):
        return self.frames[frame_name][0]
