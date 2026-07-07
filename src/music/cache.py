from pathlib import Path
import hashlib


class ArtworkCache:
    """
    Handles saving and loading album artwork
    so it doesn't have to be downloaded every time.
    """

    def __init__(self):
        self.cache_folder = Path("cache/artwork")
        self.cache_folder.mkdir(parents=True, exist_ok=True)

    def get_path(self, artwork_url: str) -> Path:
        """
        Converts an artwork URL into a unique filename.
        """

        filename = hashlib.md5(
            artwork_url.encode("utf-8")
        ).hexdigest() + ".jpg"

        return self.cache_folder / filename

    def exists(self, artwork_url: str) -> bool:
        return self.get_path(artwork_url).exists()

    def save(self, artwork_url: str, image_bytes: bytes):
        with open(self.get_path(artwork_url), "wb") as file:
            file.write(image_bytes)

    def load(self, artwork_url: str):
        path = self.get_path(artwork_url)

        if path.exists():
            return path

        return None