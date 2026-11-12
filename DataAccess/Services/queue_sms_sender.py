from Common.Repositories.ismssender import ISmsSender
from Common.Repositories.iotpqueue import IotpQueue


class QueueSmsSender(ISmsSender):
    """An ISmsSender that publishes the job to RabbitMQ instead of talking to
    the gateway. BusinessLogic keeps depending only on ISmsSender, so nothing
    above this class changed when the queue was introduced.

    When no worker is attached to the queue (or the broker is unreachable)
    nothing is published, so it falls back to sending the SMS directly. That
    keeps registration working without a second process, and cannot duplicate
    a message because the fallback only runs when nothing was queued.
    """

    def __init__(self, otp_queue: IotpQueue, fallback_sender: ISmsSender = None):
        self.otp_queue = otp_queue
        self.fallback_sender = fallback_sender

    def send_otp(self, mobile: str, code: str) -> bool:
        result = self.otp_queue.enqueue(mobile, code)

        if result is None and self.fallback_sender is not None:
            print("No OTP worker available - sending the SMS directly.")
            return self.fallback_sender.send_otp(mobile, code)

        return bool(result)
