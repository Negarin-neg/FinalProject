"""RabbitMQ worker for OTP SMS delivery.

Run it in a separate terminal while the app is running:

    python -m workers.otp_worker

It consumes jobs from the OTP queue, calls the sms.ir gateway, and replies to
the producer with the real result. Keeping the gateway call here is why the
queue is meaningful: the desktop app enqueues, the worker delivers.
"""
import json
import os
import time

import pika
from dotenv import load_dotenv

from DataAccess.Services.sms_ir_sender import SmsIrSender
from DataAccess.Services.rabbitmq_otp_queue import (
    DEFAULT_HOST,
    DEFAULT_OTP_QUEUE,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_USER,
    DEFAULT_VHOST,
    REPLY_FAIL,
    REPLY_OK,
)


def build_parameters():
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", DEFAULT_USER),
        os.getenv("RABBITMQ_PASSWORD", DEFAULT_PASSWORD),
    )
    return pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", DEFAULT_HOST),
        port=int(os.getenv("RABBITMQ_PORT", DEFAULT_PORT)),
        virtual_host=os.getenv("RABBITMQ_VHOST", DEFAULT_VHOST),
        credentials=credentials,
        heartbeat=30,
    )


class OtpWorker:
    def __init__(self, sms_sender=None, parameters=None):
        self.sms_sender = sms_sender or SmsIrSender()
        self.parameters = parameters or build_parameters()
        self.queue_name = os.getenv("RABBITMQ_OTP_QUEUE", DEFAULT_OTP_QUEUE)

    def run(self):
        while True:
            try:
                self._consume_forever()
            except pika.exceptions.AMQPConnectionError as ex:
                print(f"[otp-worker] broker unreachable ({ex}); retrying in 5s.")
                time.sleep(5)

    def _consume_forever(self):
        connection = pika.BlockingConnection(self.parameters)
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        # One job at a time keeps delivery predictable and easy to observe.
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self.queue_name, on_message_callback=self._handle)

        print(f"[otp-worker] waiting for OTP jobs on queue '{self.queue_name}'. Ctrl+C to stop.")
        channel.start_consuming()

    def _handle(self, channel, method, properties, body):
        try:
            job = json.loads(body)
            mobile = job["mobile"]
            code = job["code"]
        except (ValueError, KeyError) as ex:
            # A malformed job is unrecoverable: drop it and move on.
            print(f"[otp-worker] discarding malformed job ({ex}).")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        print(f"[otp-worker] delivering OTP to {mobile}.")
        sent = self.sms_sender.send_otp(mobile, code)
        self._reply(channel, properties, REPLY_OK if sent else REPLY_FAIL)

        # The job is finished either way - do not requeue a hard gateway
        # failure, otherwise it would loop forever.
        channel.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[otp-worker] job for {mobile} -> {'ok' if sent else 'failed'}.")

    @staticmethod
    def _reply(channel, properties, payload: bytes):
        reply_to = getattr(properties, "reply_to", None)
        if not reply_to:
            return

        channel.basic_publish(
            exchange="",
            routing_key=reply_to,
            body=payload,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )


if __name__ == "__main__":
    load_dotenv()
    OtpWorker().run()
