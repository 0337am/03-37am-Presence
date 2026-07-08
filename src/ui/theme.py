import os
import shutil
from pathlib import Path

from PyQt6.QtCore import (
    QObject,
    QSettings,
    pyqtSignal,
)


APP_DATA_DIRECTORY = (
    Path(os.getenv("LOCALAPPDATA", str(Path.home())))
    / "0337am Presence"
)

BRANDING_DIRECTORY = (
    APP_DATA_DIRECTORY / "branding"
)


DEFAULT_BRANDING = {
    "title": "03:37am ♡",
    "subtitle": "Yuno Presence",
    "footer": "Love is the strongest signal. ♡",
    "image_path": "",
    "show_title": True,
    "show_subtitle": True,
    "show_footer": True,
}


DEFAULT_THEME = {
    "preset": "Yuno",
    "background": "#140812",
    "sidebar": "#210b1a",
    "card": "#352747",
    "card_alt": "#3e2e54",
    "accent": "#ff79b9",
    "text": "#fff5fb",
    "muted": "#bca9ce",
    "border": "#5c4777",
    "compact": True,
}


THEME_PRESETS = {
    "Yuno": {
        "background": "#140812",
        "sidebar": "#210b1a",
        "card": "#352747",
        "card_alt": "#3e2e54",
        "accent": "#ff79b9",
        "text": "#fff5fb",
        "muted": "#bca9ce",
        "border": "#5c4777",
    },
    "Midnight": {
        "background": "#0b1020",
        "sidebar": "#11182b",
        "card": "#182139",
        "card_alt": "#202b49",
        "accent": "#6ea8ff",
        "text": "#f5f7ff",
        "muted": "#9ba9c5",
        "border": "#2d3b60",
    },
    "Purple": {
        "background": "#100b1b",
        "sidebar": "#191029",
        "card": "#2b1d45",
        "card_alt": "#37265a",
        "accent": "#b58cff",
        "text": "#faf7ff",
        "muted": "#b9a9cf",
        "border": "#5a4279",
    },
    "Rose": {
        "background": "#180b10",
        "sidebar": "#251018",
        "card": "#3b1d2a",
        "card_alt": "#4a2535",
        "accent": "#ff7fa8",
        "text": "#fff5f8",
        "muted": "#d8aab9",
        "border": "#6b354a",
    },
    "Monochrome": {
        "background": "#0f0f10",
        "sidebar": "#171719",
        "card": "#242428",
        "card_alt": "#2e2e34",
        "accent": "#d7d7df",
        "text": "#f7f7fa",
        "muted": "#a7a7b1",
        "border": "#45454f",
    },
}

class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)
    branding_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.store = QSettings(
            "0337am",
            "Presence",
        )

    def theme(self) -> dict:
        values = {}

        for key, default in DEFAULT_THEME.items():
            if key == "compact":
                values[key] = self.store.value(
                    f"theme/{key}",
                    default,
                    type=bool,
                )
            else:
                values[key] = str(
                    self.store.value(
                        f"theme/{key}",
                        default,
                    )
                )

        return values

    def branding(self) -> dict:
        values = {}

        boolean_keys = {
            "show_title",
            "show_subtitle",
            "show_footer",
        }

        for key, default in DEFAULT_BRANDING.items():
            if key in boolean_keys:
                values[key] = self.store.value(
                    f"branding/{key}",
                    default,
                    type=bool,
                )
            else:
                values[key] = str(
                    self.store.value(
                        f"branding/{key}",
                        default,
                    )
                    or ""
                )

        return values

    def set_theme_value(
        self,
        key: str,
        value,
    ):
        if key not in DEFAULT_THEME:
            return

        self.store.setValue(
            f"theme/{key}",
            value,
        )

        if key != "preset":
            self.store.setValue(
                "theme/preset",
                "Custom",
            )

        self.store.sync()
        self.theme_changed.emit(
            self.theme()
        )

    def set_branding_value(
        self,
        key: str,
        value,
    ):
        if key not in DEFAULT_BRANDING:
            return

        self.store.setValue(
            f"branding/{key}",
            value,
        )

        self.store.sync()
        self.branding_changed.emit(
            self.branding()
        )

    def apply_preset(
        self,
        preset_name: str,
    ):
        preset = THEME_PRESETS.get(
            preset_name
        )

        if preset is None:
            return

        self.store.setValue(
            "theme/preset",
            preset_name,
        )

        for key, value in preset.items():
            self.store.setValue(
                f"theme/{key}",
                value,
            )

        self.store.sync()
        self.theme_changed.emit(
            self.theme()
        )

    def save_branding_image(
        self,
        source_path: str,
    ) -> str:
        source = Path(source_path)

        if not source.exists():
            return ""

        suffix = source.suffix.lower()

        if suffix not in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        }:
            return ""

        try:
            BRANDING_DIRECTORY.mkdir(
                parents=True,
                exist_ok=True,
            )

            for old_image in BRANDING_DIRECTORY.glob(
                "sidebar_image.*"
            ):
                try:
                    old_image.unlink()
                except OSError:
                    pass

            destination = (
                BRANDING_DIRECTORY
                / f"sidebar_image{suffix}"
            )

            shutil.copy2(
                source,
                destination,
            )

            self.set_branding_value(
                "image_path",
                str(destination),
            )

            return str(destination)

        except OSError:
            return ""

    def reset_branding_image(self):
        branding = self.branding()
        image_path = Path(
            branding.get(
                "image_path",
                "",
            )
        )

        if image_path.exists():
            try:
                image_path.unlink()
            except OSError:
                pass

        self.set_branding_value(
            "image_path",
            "",
        )

    def reset_theme(self):
        for key, value in DEFAULT_THEME.items():
            self.store.setValue(
                f"theme/{key}",
                value,
            )

        self.store.sync()
        self.theme_changed.emit(
            self.theme()
        )

    def reset_branding(self):
        current_image = self.branding().get(
            "image_path",
            ""
        )

        if current_image:
            image_path = Path(current_image)

            if image_path.exists():
                try:
                    image_path.unlink()
                except OSError:
                    pass

        for key, value in DEFAULT_BRANDING.items():
            self.store.setValue(
                f"branding/{key}",
                value,
            )

        self.store.sync()
        self.branding_changed.emit(
            self.branding()
        )