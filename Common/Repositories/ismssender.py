from abc import ABC, abstractmethod


class ISmsSender(ABC):
    """Delivers a one-time code to a mobile number.

    BusinessLogic depends on this abstraction, not on a concrete provider,
    so the SMS gateway (FarazSMS/IranPayamak) can be swapped without touching
    the OTP or registration logic.
    """

    @abstractmethod
    def send_otp(self, mobile: str, code: str) -> bool:
        """Sends `code` to `mobile` (local format 09xxxxxxxxx).

        Returns True only when the provider accepted the message. It must
        return False on any failure - callers use this to avoid telling the
        user that an SMS went out when it did not.
        """
        pass
