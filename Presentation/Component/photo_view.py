from io import BytesIO
from tkinter import Label

from PIL import Image, ImageDraw, ImageTk

_BACKGROUND = "#e6e6e6"
_SILHOUETTE = "#b5b5b5"


class PhotoView(Label):
    """A square box that shows a profile photo, or a grey silhouette when
    there is no photo. Give it image bytes with set_photo()."""

    def __init__(self, master, size=150):
        super().__init__(master, relief="groove", borderwidth=1)

        self._size = size
        self._photo_image = None  # keep a reference - Tkinter drops images without one

        self.set_photo(None)

    def set_photo(self, photo_bytes):
        image = self._load(photo_bytes) if photo_bytes else self._placeholder()

        self._photo_image = ImageTk.PhotoImage(image)
        self.config(image=self._photo_image)

    def _load(self, photo_bytes):
        try:
            picture = Image.open(BytesIO(photo_bytes)).convert("RGB")
        except OSError:
            return self._placeholder()  # unreadable bytes in the database

        picture.thumbnail((self._size, self._size))

        box = Image.new("RGB", (self._size, self._size), _BACKGROUND)
        box.paste(picture, ((self._size - picture.width) // 2, (self._size - picture.height) // 2))
        return box

    def _placeholder(self):
        size = self._size
        box = Image.new("RGB", (size, size), _BACKGROUND)
        draw = ImageDraw.Draw(box)

        head = size * 0.22
        center_x = size / 2
        draw.ellipse(
            (center_x - head, size * 0.20, center_x + head, size * 0.20 + head * 2),
            fill=_SILHOUETTE,
        )
        draw.ellipse(
            (size * 0.18, size * 0.58, size * 0.82, size * 1.30),
            fill=_SILHOUETTE,
        )
        return box
