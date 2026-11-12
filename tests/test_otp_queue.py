import json
import unittest

from DataAccess.Services.queue_sms_sender import QueueSmsSender
from DataAccess.Services.rabbitmq_otp_queue import REPLY_FAIL, REPLY_OK
from Common.Repositories.iotpqueue import IotpQueue
from workers.otp_worker import OtpWorker


class FakeQueue(IotpQueue):
    def __init__(self, result=True):
        self.result = result
        self.enqueued = []

    def enqueue(self, mobile, code):
        self.enqueued.append((mobile, code))
        return self.result


class QueueSmsSenderTests(unittest.TestCase):
    def test_send_delegates_to_the_queue(self):
        queue = FakeQueue(result=True)
        sender = QueueSmsSender(queue)
        self.assertTrue(sender.send_otp("09121234567", "12345"))
        self.assertEqual(queue.enqueued, [("09121234567", "12345")])

    def test_send_reports_queue_failure(self):
        sender = QueueSmsSender(FakeQueue(result=False))
        self.assertFalse(sender.send_otp("09121234567", "12345"))

    def test_send_falls_back_when_nothing_was_published(self):
        # result=None means "no worker attached / broker unreachable".
        queue = FakeQueue(result=None)
        fallback = FakeSmsSender(result=True)
        sender = QueueSmsSender(queue, fallback_sender=fallback)

        self.assertTrue(sender.send_otp("09121234567", "12345"))
        self.assertEqual(fallback.sent, [("09121234567", "12345")])

    def test_worker_failure_is_not_retried_directly(self):
        # The job did reach a worker, so a second send could duplicate it.
        fallback = FakeSmsSender(result=True)
        sender = QueueSmsSender(FakeQueue(result=False), fallback_sender=fallback)

        self.assertFalse(sender.send_otp("09121234567", "12345"))
        self.assertEqual(fallback.sent, [])


class FakeSmsSender:
    def __init__(self, result=True):
        self.result = result
        self.sent = []

    def send_otp(self, mobile, code):
        self.sent.append((mobile, code))
        return self.result


class FakeChannel:
    def __init__(self):
        self.acks = []
        self.nacks = []
        self.published = []

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacks.append((delivery_tag, requeue))

    def basic_publish(self, exchange, routing_key, body, properties):
        self.published.append((routing_key, body, properties.correlation_id))


class FakeMethod:
    delivery_tag = 1


class FakeProperties:
    def __init__(self, reply_to="reply-q", correlation_id="cid-1"):
        self.reply_to = reply_to
        self.correlation_id = correlation_id


class OtpWorkerTests(unittest.TestCase):
    def test_worker_sends_and_acks_on_success(self):
        sms = FakeSmsSender(result=True)
        worker = OtpWorker(sms_sender=sms)
        channel = FakeChannel()
        body = json.dumps({"mobile": "09121234567", "code": "12345"}).encode()

        worker._handle(channel, FakeMethod(), FakeProperties(), body)

        self.assertEqual(sms.sent, [("09121234567", "12345")])
        self.assertEqual(channel.published, [("reply-q", REPLY_OK, "cid-1")])
        self.assertEqual(channel.acks, [1])

    def test_worker_reports_gateway_failure(self):
        sms = FakeSmsSender(result=False)
        worker = OtpWorker(sms_sender=sms)
        channel = FakeChannel()
        body = json.dumps({"mobile": "09121234567", "code": "12345"}).encode()

        worker._handle(channel, FakeMethod(), FakeProperties(), body)

        self.assertEqual(channel.published, [("reply-q", REPLY_FAIL, "cid-1")])
        # A hard gateway failure must not be requeued forever.
        self.assertEqual(channel.acks, [1])

    def test_worker_discards_malformed_job(self):
        worker = OtpWorker(sms_sender=FakeSmsSender())
        channel = FakeChannel()

        worker._handle(channel, FakeMethod(), FakeProperties(), b"not-json")

        self.assertEqual(channel.nacks, [(1, False)])
        self.assertEqual(channel.published, [])

    def test_missing_reply_to_is_tolerated(self):
        sms = FakeSmsSender(result=True)
        worker = OtpWorker(sms_sender=sms)
        channel = FakeChannel()
        body = json.dumps({"mobile": "09121234567", "code": "12345"}).encode()

        worker._handle(channel, FakeMethod(), FakeProperties(reply_to=None), body)

        # Nothing to reply to, but the job is still processed and acked.
        self.assertEqual(sms.sent, [("09121234567", "12345")])
        self.assertEqual(channel.published, [])
        self.assertEqual(channel.acks, [1])


if __name__ == "__main__":
    unittest.main()
