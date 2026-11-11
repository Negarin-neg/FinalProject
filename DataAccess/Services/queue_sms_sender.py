from Common.Repositories.ismssender import ISmsSender
from Common.Repositories.iotpqueue import IotpQueue


class QueueSmsSender(ISmsSender):
    """An ISmsSender that publishes the job to RabbitMQ instead of talking to
    the gateway. BusinessLogic keeps depending only on ISmsSender, so nothing
    above this class changed when the queue was introduced."""

    def __init__(self, otp_queue: IotpQueue):
        self.otp_queue = otp_queue

    def send_otp(self, mobile: str, code: str) -> bool:
        return self.otp_queue.enqueue(mobile, code)
