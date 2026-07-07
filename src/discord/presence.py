from pypresence import Presence


class DiscordPresence:

    def __init__(self):

        # Paste YOUR Discord Application ID here
        self.client_id = "1523801127962022070"

        self.rpc = None

    def connect(self):

        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()

            print("✅ Connected to Discord!")

            self.rpc.update(
                details="Testing 03:37am Presence",
                state="Discord connection successful",
                large_text="03:37am Presence"
            )

            return True

        except Exception as e:

            print(e)
            return False