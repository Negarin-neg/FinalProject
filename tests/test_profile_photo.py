import os
import tempfile
import unittest
from io import BytesIO

from PIL import Image

from BusinessLogic.photo_service import PhotoService
from BusinessLogic.user_business_logic import UserBusinessLogic
from tests.fakes import InMemoryEmployeeRepository


def make_image_bytes(fmt="PNG", size=(64, 64)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(buffer, format=fmt)
    return buffer.getvalue()


class PhotoValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.service = PhotoService(self.temp_dir)

    def test_accepts_valid_png(self):
        self.assertEqual(self.service.validate(make_image_bytes("PNG")), "PNG")

    def test_rejects_non_image_content(self):
        # A text file renamed to .png must be rejected by content, not extension.
        with self.assertRaises(Exception):
            self.service.validate(b"this is not an image", "avatar.png")

    def test_rejects_empty_file(self):
        with self.assertRaises(Exception):
            self.service.validate(b"", "avatar.png")

    def test_rejects_oversized_file(self):
        big = b"\x00" * (3 * 1024 * 1024)
        with self.assertRaises(Exception):
            self.service.validate(big, "big.png")

    def test_saved_file_uses_generated_safe_name(self):
        path = self.service.save(7, make_image_bytes("PNG"), "../../etc/passwd")
        name = os.path.basename(path)
        self.assertTrue(name.startswith("employee_7_"))
        self.assertTrue(path.startswith(self.temp_dir))
        self.assertTrue(os.path.isfile(path))


class PhotoAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repository = InMemoryEmployeeRepository()
        self.alice_id = self.repository.seed(username="alice", mobile="09120000001")
        self.bob_id = self.repository.seed(username="bob", mobile="09120000002")
        self.business = UserBusinessLogic(
            self.repository, photo_service=PhotoService(self.temp_dir)
        )

    def test_upload_sets_only_the_owners_photo_path(self):
        response = self.business.upload_profile_photo(self.alice_id, make_image_bytes(), "a.png")
        self.assertTrue(response.success)

        alice = self.repository.get_by_id(self.alice_id)
        bob = self.repository.get_by_id(self.bob_id)
        self.assertIsNotNone(alice.photo_path)
        self.assertIsNone(bob.photo_path)

    def test_photo_reads_back_for_the_owner(self):
        self.business.upload_profile_photo(self.alice_id, make_image_bytes(), "a.png")
        photo_bytes = self.business.get_profile_photo(self.alice_id)
        self.assertIsNotNone(photo_bytes)
        self.assertGreater(len(photo_bytes), 0)

    def test_other_user_has_no_photo(self):
        self.business.upload_profile_photo(self.alice_id, make_image_bytes(), "a.png")
        self.assertIsNone(self.business.get_profile_photo(self.bob_id))

    def test_remove_clears_photo_and_path(self):
        self.business.upload_profile_photo(self.alice_id, make_image_bytes(), "a.png")
        response = self.business.remove_profile_photo(self.alice_id)
        self.assertTrue(response.success)
        self.assertIsNone(self.repository.get_by_id(self.alice_id).photo_path)
        self.assertIsNone(self.business.get_profile_photo(self.alice_id))


if __name__ == "__main__":
    unittest.main()
