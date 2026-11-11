from abc import ABC, abstractmethod


class IotpQueue(ABC):
    """Hands an OTP send-job to a message broker instead of calling the SMS
    gateway directly.

    Decoupling the request from the actual delivery lets a worker process the
    jobs and makes the queue observable (e.g. in the RabbitMQ dashboard), while
    the business logic keeps a simple synchronous contract.
    """

    @abstractmethod
    def enqueue(self, mobile: str, code: str) -> bool:
        """Publishes an OTP job and returns True only when the worker
        confirmed the SMS was actually accepted by the provider. It must
        return False when the broker is unreachable or the send failed."""
        pass
