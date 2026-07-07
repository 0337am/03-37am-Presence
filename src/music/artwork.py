import requests

from src.music.cache import ArtworkCache


class ArtworkManager:

    def __init__(self):
        self.cache = ArtworkCache()

    def get_artwork(self, artwork_url):

        if not artwork_url:
            return None

        # Already cached?
        if self.cache.exists(artwork_url):
            return self.cache.load(artwork_url)

        # Download it
        try:
            response = requests.get(artwork_url, timeout=10)

            if response.status_code == 200:
                self.cache.save(
                    artwork_url,
                    response.content
                )

                return self.cache.load(artwork_url)

        except Exception:
            pass

        return None