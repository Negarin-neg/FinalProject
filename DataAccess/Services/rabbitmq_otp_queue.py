import json
import os
import time
import uuid

import pika

from Common.Repositories.iotpqueue import IotpQueue

# Defaults match a stock local RabbitMQ install; every value can be overridden
# from .env so no credentials are hardcoded.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5672
DEFAULT_USER = "guest"
DEFAULT_PASSWORD = "guest"
DEFAULT_VHOST = "/"
DEFAULT_OTP_QUEUE = "otp_sms_queue"

# How long the producer waits for the worker's confirmation before giving up.
DEFAULT_REPLY_TIMEOUT_SECONDS = 8

REPLY_OK = b"ok"
REPLY_FAIL = b"fail"


class RabbitMqOtpQueue(IotpQueue):
    """Publishes OTP jobs to RabbitMQ and waits briefly for the worker's result.

    The queue is the single path to the SMS gateway: because it is declared
    `durable`, it shows up in the RabbitMQ management UI (http://localhost:15672)
    with live message counts.

    A short RPC-style wait is used so the caller still learns whether the SMS
    was really accepted (and therefore never claims success on failure). If no
    confirmation arrives in time, it reports failure rather than guessing.
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        vhost: str = None,
        queue_name: str = None,
        reply_timeout: int = None,
    ):
        self.host = host or os.getenv("RABBITMQ_HOST", DEFAULT_HOST)
        self.port = int(port or os.getenv("RABBITMQ_PORT", DEFAULT_PORT))
        self.username = username or os.getenv("RABBITMQ_USER", DEFAULT_USER)
        self.password = password or os.getenv("RABBITMQ_PASSWORD", DEFAULT_PASSWORD)
        self.vhost = vhost or os.getenv("RABBITMQ_VHOST", DEFAULT_VHOST)
        self.queue_name = queue_name or os.getenv("RABBITMQ_OTP_QUEUE", DEFAULT_OTP_QUEUE)
        self.reply_timeout = int(reply_timeout or os.getenv("RABBITMQ_REPLY_TIMEOUT", DEFAULT_REPLY_TIMEOUT_SECONDS))

    def _parameters(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=10,
        )

    def enqueue(self, mobile: str, code: str) -> bool:
        connection = None
        try:
            connection = pika.BlockingConnection(self._parameters())
            channel = connection.channel()
            # Durable queue -> survives a broker restart and is listed in the UI.
            channel.queue_declare(queue=self.queue_name, durable=True)

            reply_queue = self._declare_reply_queue(channel)
            correlation_id = str(uuid.uuid4())
            replies = {}
            channel.basic_consume(
                queue=reply_queue,
                on_message_callback=self._reply_callback(replies, correlation_id),
                auto_ack=True,
            )

            body = json.dumps({"mobile": mobile, "code": str(code)})
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=body,
                properties=pika.BasicProperties(
                    reply_to=reply_queue,
                    correlation_id=correlation_id,
                    delivery_mode=2,  # persistent
                ),
            )

            return self._wait_for_reply(connection, replies, correlation_id)
        except pika.exceptions.AMQPError as ex:
            print(f"RabbitMQ error -> {ex}")
            return False
        finally:
            if connection is not None and connection.is_open:
                try:
                    connection.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _declare_reply_queue(channel) -> str:
        # Exclusive, auto-delete queue used only for this request's reply.
        result = channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        return result.method.queue

    @staticmethod
    def _reply_callback(replies: dict, correlation_id: str):
        def callback(channel, method, properties, body):
            if properties.correlation_id == correlation_id:
                replies["body"] = body
                channel.stop_consuming()
        return callback

    def _wait_for_reply(self, connection, replies: dict, correlation_id: str) -> bool:
        deadline = time.time() + self.reply_timeout
        while "body" not in replies and time.time() < deadline:
            # process the reply queue without blocking the whole timeout.
            connection.process_data_events(time_limit=0.5)

        if "body" not in replies:
            print("RabbitMQ: no delivery confirmation from the worker in time.")
            return False

        return replies["body"] == REPLY_OK
