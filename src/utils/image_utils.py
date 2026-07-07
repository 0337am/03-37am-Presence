from PyQt6.QtGui import QPixmap

from winsdk.windows.storage.streams import DataReader

import asyncio


async def _thumbnail_to_pixmap(thumbnail):

    if thumbnail is None:
        return None

    stream = await thumbnail.open_read_async()

    reader = DataReader(stream)

    await reader.load_async(stream.size)

    buffer = reader.read_buffer(stream.size)

    data = bytes(buffer)

    pixmap = QPixmap()

    pixmap.loadFromData(data)

    return pixmap


def thumbnail_to_pixmap(thumbnail):

    try:

        return asyncio.run(
            _thumbnail_to_pixmap(thumbnail)
        )

    except Exception as e:

        print("Thumbnail conversion failed:")
        print(e)

        return None