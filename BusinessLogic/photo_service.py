import os
import uuid
from io import BytesIO

from PIL import Image, UnidentifiedImageError

# Keep profile photos small and cheap: the DB column is nvarchar(260), so we
# store the file path, not the bytes.
MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_PHOTO_DIMENSION = 1024
PHOTO_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp", "BMP": ".bmp"}
ALLOWED_FORMATS = set(PHOTO_EXTENSIONS)


class PhotoValidationError(Exception):
    """Raised with a user-facing Persian message when an upload is rejected."""


class PhotoService:
    """Validates, normalizes and stores profile photos on disk.

    Images are stored as `employee_<id>.<ext>` under one folder, so a user can
    only ever address their own file and cannot traverse the filesystem.
    """

    def __init__(self, storage_dir: str):
        # storage_dir comes from config (.env) so no absolute path is hardcoded.
        self.storage_dir = storage_dir

    def validate(self, file_bytes: bytes, filename: str = "") -> str:
        """Returns the detected image format, or raises PhotoValidationError.

        The decision is based on the actual decoded content (not the file
        extension), so a renamed non-image cannot slip through.
        """
        if not file_bytes:
            raise PhotoValidationError("فایلی انتخاب نشده است.")

        if len(file_bytes) > MAX_PHOTO_BYTES:
            raise PhotoValidationError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.")

        try:
            with Image.open(BytesIO(file_bytes)) as probe:
                probe.verify()
            # verify() consumes the file object, so reopen to read format/size.
            with Image.open(BytesIO(file_bytes)) as image:
                image_format = image.format
                width, height = image.size
        except (UnidentifiedImageError, OSError, ValueError):
            raise PhotoValidationError("فایل انتخاب‌شده یک تصویر معتبر نیست.")

        if image_format not in ALLOWED_FORMATS:
            raise PhotoValidationError("فقط تصاویر JPG، PNG، GIF، WEBP یا BMP مجاز هستند.")

        if width > MAX_PHOTO_DIMENSION or height > MAX_PHOTO_DIMENSION:
            raise PhotoValidationError("ابعاد تصویر بیش از حد بزرگ است.")

        return image_format

    def save(self, employee_id: int, file_bytes: bytes, filename: str = "") -> str:
        """Validates then writes the file; returns its path for the database."""
        image_format = self.validate(file_bytes, filename)

        os.makedirs(self.storage_dir, exist_ok=True)

        self.remove(employee_id)

        extension = PHOTO_EXTENSIONS.get(image_format, ".img")
        # A random name means a replaced photo never overwrites another user's
        # file and an old URL stops working as soon as it is replaced.
        safe_name = f"employee_{int(employee_id)}_{uuid.uuid4().hex}{extension}"
        file_path = os.path.join(self.storage_dir, safe_name)

        with open(file_path, "wb") as photo_file:
            photo_file.write(file_bytes)

        return file_path

    def remove(self, employee_id: int) -> bool:
        """Deletes the employee's current photo file(s). Safe if absent."""
        if not os.path.isdir(self.storage_dir):
            return False

        prefix = f"employee_{int(employee_id)}_"
        removed = False

        for name in os.listdir(self.storage_dir):
            if name.startswith(prefix):
                try:
                    os.remove(os.path.join(self.storage_dir, name))
                    removed = True
                except OSError:
                    pass

        return removed

    @staticmethod
    def read(file_path: str):
        """Returns the file bytes, or None when the path is missing/unreadable."""
        if not file_path or not os.path.isfile(file_path):
            return None

        try:
            with open(file_path, "rb") as photo_file:
                return photo_file.read()
        except OSError:
            return None
