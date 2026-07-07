import asyncio
from pathlib import Path

from PyQt6.QtGui import QPixmap

from winsdk.windows.storage.streams import DataReader


class ArtworkManager:

    def __init__(self):

        self.cache_folder = Path("cache/artwork")
        self.cache_folder.mkdir(parents=True, exist_ok=True)

    def get_pixmap(self, song):

        if song is None:
            return None

        if song.thumbnail is None:
            return None

        try:

            image_path = asyncio.run(
                self._save_thumbnail(song)
            )

            if image_path.exists():

                pixmap = QPixmap(str(image_path))

                if not pixmap.isNull():
                    return pixmap

        except Exception as e:

            print("Artwork error:")
            print(e)

        return None

    async def _save_thumbnail(self, song):

        filename = (
            f"{song.artist}-{song.album}-{song.title}"
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )

        image_path = self.cache_folder / f"{filename}.jpg"

        if image_path.exists():
            return image_path

        stream = await song.thumbnail.open_read_async()

        size = stream.size

        reader = DataReader(stream)

        await reader.load_async(size)

        buffer = reader.read_buffer(size)

        data = bytes(buffer)

        with open(image_path, "wb") as image:

            image.write(data)

        return image_path