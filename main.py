import os

from dotenv import load_dotenv

from Presentation.main_view import MainView
from BusinessLogic.otp_service import OtpService
from BusinessLogic.photo_service import PhotoService
from BusinessLogic.user_business_logic import UserBusinessLogic
from DataAccess.Repositories.SQLAlchemy.employee_repository import SQLAlchemyEmployeeRepository
from DataAccess.Services.queue_sms_sender import QueueSmsSender
from DataAccess.Services.rabbitmq_otp_queue import RabbitMqOtpQueue
from DataAccess.Services.sms_ir_sender import SmsIrSender

load_dotenv()

# Composition root: repositories, external services and business logic are
# wired here only, so no layer reaches out for its own dependencies.
repository = SQLAlchemyEmployeeRepository()

# OTP delivery can go straight to sms.ir or (default) through RabbitMQ so the
# queue is visible in the management dashboard. Set SMS_USE_QUEUE=false in
# .env to bypass the broker.
if os.getenv("SMS_USE_QUEUE", "true").lower() == "true":
    # The worker is a separate process (python -m workers.otp_worker). If it is
    # not running, the queue sender falls back to SmsIrSender so registration
    # still delivers the code.
    sms_sender = QueueSmsSender(RabbitMqOtpQueue(), fallback_sender=SmsIrSender())
else:
    sms_sender = SmsIrSender()

# Photos are stored next to the project in a dedicated folder whose location
# comes from configuration (defaults to ./storage/profile_photos).
photo_storage_dir = os.getenv("PROFILE_PHOTO_DIR", os.path.join("storage", "profile_photos"))
photo_service = PhotoService(photo_storage_dir)

user_business = UserBusinessLogic(
    repository,
    sms_sender=sms_sender,
    otp_service=OtpService(),
    photo_service=photo_service,
)

MainView(user_business)
