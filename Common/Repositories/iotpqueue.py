from abc import ABC, abstractmethod


class IotpQueue(ABC):
    """Hands an OTP send-job to a message broker instead of calling the SMS
    gateway directly.

    Decoupling the request from the actual delivery lets a worker process the
    jobs and makes the queue observable (e.g. in the RabbitMQ dashboard), while
    the business logic keeps a simple synchronous contract.
    """

    @abstractmethod
    def enqueue(self, mobile: str, code: str):
        """Publishes an OTP job and reports what happened.

        True  -> the worker confirmed the provider accepted the SMS.
        False -> the job was published but the worker reported a failure
                 (or never confirmed in time).
        None  -> nothing was published at all (no worker consuming the queue,
                 or the broker is unreachable), so the caller may safely fall
                 back to sending the SMS directly.
        """
        pass
