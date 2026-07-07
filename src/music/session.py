from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)


class MediaSession:

    def __init__(self):
        self.manager = None

    async def connect(self):
        """
        Connect to the Windows Global Media Session Manager.
        """
        self.manager = (
            await GlobalSystemMediaTransportControlsSessionManager.request_async()
        )

    def current(self):
        """
        Returns the currently active media session.
        """

        if self.manager is None:
            return None

        return self.manager.get_current_session()