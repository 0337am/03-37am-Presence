import asyncio
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager
)


async def main():

    print("=" * 60)
    print("03:37am Presence - Windows Media Debugger")
    print("=" * 60)

    sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()

    current = sessions.get_current_session()

    if current is None:
        print("\nNo media session found.")
        return

    props = await current.try_get_media_properties_async()

    print("\nMedia Properties")
    print("-" * 60)

    for name in dir(props):

        if name.startswith("_"):
            continue

        try:
            value = getattr(props, name)

            if callable(value):
                continue

            print(f"{name}: {value}")

        except Exception:
            pass

    print("\nPlayback Info")
    print("-" * 60)

    try:
        timeline = current.get_timeline_properties()

        for name in dir(timeline):

            if name.startswith("_"):
                continue

            value = getattr(timeline, name)

            if callable(value):
                continue

            print(f"{name}: {value}")

    except Exception as e:
        print(e)


asyncio.run(main())