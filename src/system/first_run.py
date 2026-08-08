from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


STATE_SCHEMA_VERSION = 1
WELCOME_VERSION = 1

FIRST_RUN_STATE_FILENAME = (
    "first_run_state.json"
)

FIRST_RUN_TEMP_FILENAME = (
    "first_run_state.json.tmp"
)

INVALID_STATE_PREFIX = (
    "first_run_state.invalid-"
)

WELCOME_STATE_PENDING = (
    "pending"
)

WELCOME_STATE_COMPLETE = (
    "complete"
)

VALID_WELCOME_STATES = {
    WELCOME_STATE_PENDING,
    WELCOME_STATE_COMPLETE,
}


class FirstRunStateError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class FirstRunState:
    state: str
    welcome_version: int

    def __post_init__(self):
        state = str(
            self.state
        ).strip().lower()

        if state not in VALID_WELCOME_STATES:
            raise FirstRunStateError(
                "Unsupported first-run welcome state."
            )

        version = self.welcome_version

        if (
            isinstance(
                version,
                bool,
            )
            or not isinstance(
                version,
                int,
            )
            or version < 0
        ):
            raise FirstRunStateError(
                "Welcome version must be a "
                "non-negative integer."
            )

        object.__setattr__(
            self,
            "state",
            state,
        )

    def to_payload(self) -> dict:
        return {
            "schema_version": (
                STATE_SCHEMA_VERSION
            ),
            "state": self.state,
            "welcome_version": (
                self.welcome_version
            ),
        }

    @classmethod
    def from_payload(
        cls,
        payload,
    ) -> FirstRunState:
        if not isinstance(
            payload,
            dict,
        ):
            raise FirstRunStateError(
                "First-run state must be a JSON object."
            )

        schema_version = payload.get(
            "schema_version"
        )

        if (
            isinstance(
                schema_version,
                bool,
            )
            or not isinstance(
                schema_version,
                int,
            )
            or schema_version
            != STATE_SCHEMA_VERSION
        ):
            raise FirstRunStateError(
                "Unsupported first-run state schema."
            )

        state = payload.get(
            "state"
        )

        if not isinstance(
            state,
            str,
        ):
            raise FirstRunStateError(
                "First-run welcome state must be text."
            )

        welcome_version = payload.get(
            "welcome_version"
        )

        return cls(
            state=state,
            welcome_version=welcome_version,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class FirstRunDecision:
    show_welcome: bool
    migrated_existing_install: bool = False
    reason: str = ""


class FirstRunStateStore:
    def __init__(
        self,
        *,
        app_data_directory: str | Path | None = None,
    ):
        self.app_data_directory = (
            Path(
                app_data_directory
            )
            if app_data_directory is not None
            else self.default_app_data_directory()
        )

        self.file_path = (
            self.app_data_directory
            / FIRST_RUN_STATE_FILENAME
        )

        self.temp_path = (
            self.app_data_directory
            / FIRST_RUN_TEMP_FILENAME
        )

    @staticmethod
    def default_app_data_directory() -> Path:
        configured = os.environ.get(
            "LOCALAPPDATA",
            "",
        ).strip()

        if configured:
            return (
                Path(
                    configured
                )
                / "0337am Presence"
            )

        return (
            Path.home()
            / ".0337am-presence"
        )

    def load(
        self,
    ) -> FirstRunState | None:
        if not self.file_path.exists():
            return None

        try:
            payload = json.loads(
                self.file_path.read_text(
                    encoding="utf-8"
                )
            )

            return (
                FirstRunState
                .from_payload(
                    payload
                )
            )
        except Exception as error:
            print(
                "First-run state load error: "
                f"{error}"
            )

            self._quarantine_invalid_file()

            return None

    def save(
        self,
        state: FirstRunState,
    ) -> None:
        if not isinstance(
            state,
            FirstRunState,
        ):
            raise TypeError(
                "state must be FirstRunState."
            )

        self.app_data_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = state.to_payload()

        text = (
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

        try:
            self.temp_path.write_text(
                text,
                encoding="utf-8",
            )

            os.replace(
                self.temp_path,
                self.file_path,
            )
        finally:
            if self.temp_path.exists():
                try:
                    self.temp_path.unlink()
                except OSError:
                    pass

    def _quarantine_invalid_file(
        self,
    ) -> Path | None:
        if not self.file_path.exists():
            return None

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        candidate = (
            self.app_data_directory
            / (
                f"{INVALID_STATE_PREFIX}"
                f"{timestamp}.json"
            )
        )

        counter = 1

        while candidate.exists():
            candidate = (
                self.app_data_directory
                / (
                    f"{INVALID_STATE_PREFIX}"
                    f"{timestamp}-{counter}.json"
                )
            )

            counter += 1

        try:
            self.file_path.replace(
                candidate
            )
        except OSError as error:
            print(
                "Invalid first-run state could not "
                f"be quarantined: {error}"
            )

            return None

        print(
            "Invalid first-run state quarantined: "
            f"{candidate}"
        )

        return candidate


class FirstRunManager:
    """
    Determines whether the one-time welcome experience should
    be shown.

    This state deliberately lives in its own LocalAppData JSON
    file rather than shared application settings. First-run
    detection therefore cannot modify unrelated application
    preferences.

    evaluate() must run before normal application services start
    creating LocalAppData. A genuinely fresh installation is
    immediately marked pending so a crash during onboarding
    still shows the welcome experience on the next launch.
    """

    def __init__(
        self,
        *,
        app_data_directory: str | Path | None = None,
        store: FirstRunStateStore | None = None,
    ):
        if (
            store is not None
            and app_data_directory is not None
        ):
            raise ValueError(
                "Pass either store or "
                "app_data_directory, not both."
            )

        self.store = (
            store
            if store is not None
            else FirstRunStateStore(
                app_data_directory=(
                    app_data_directory
                ),
            )
        )

        self.app_data_directory = (
            self.store.app_data_directory
        )

    def evaluate(
        self,
    ) -> FirstRunDecision:
        saved_state = self.store.load()

        if saved_state is not None:
            if (
                saved_state.state
                == WELCOME_STATE_PENDING
            ):
                return FirstRunDecision(
                    show_welcome=True,
                    migrated_existing_install=False,
                    reason="pending_welcome",
                )

            if (
                saved_state.state
                == WELCOME_STATE_COMPLETE
            ):
                if (
                    saved_state.welcome_version
                    != WELCOME_VERSION
                ):
                    self.mark_completed()

                return FirstRunDecision(
                    show_welcome=False,
                    migrated_existing_install=False,
                    reason="completed",
                )

        if self._has_existing_install_state():
            self.mark_completed()

            return FirstRunDecision(
                show_welcome=False,
                migrated_existing_install=True,
                reason="existing_install",
            )

        self.mark_pending()

        return FirstRunDecision(
            show_welcome=True,
            migrated_existing_install=False,
            reason="fresh_install",
        )

    def mark_pending(
        self,
    ) -> None:
        self.store.save(
            FirstRunState(
                state=(
                    WELCOME_STATE_PENDING
                ),
                welcome_version=0,
            )
        )

    def mark_completed(
        self,
    ) -> None:
        self.store.save(
            FirstRunState(
                state=(
                    WELCOME_STATE_COMPLETE
                ),
                welcome_version=(
                    WELCOME_VERSION
                ),
            )
        )

    def is_completed(
        self,
    ) -> bool:
        saved_state = self.store.load()

        if saved_state is None:
            return False

        return (
            saved_state.state
            == WELCOME_STATE_COMPLETE
            and saved_state.welcome_version
            >= WELCOME_VERSION
        )

    def _has_existing_install_state(
        self,
    ) -> bool:
        try:
            if not self.app_data_directory.exists():
                return False

            if not self.app_data_directory.is_dir():
                return True

            for child in (
                self.app_data_directory.iterdir()
            ):
                if self._is_first_run_artifact(
                    child
                ):
                    continue

                return True

            return False
        except OSError:
            # Be conservative if an existing directory cannot be
            # inspected. Avoid surprising a likely established
            # user with first-run UI.
            return True

    @staticmethod
    def _is_first_run_artifact(
        path: Path,
    ) -> bool:
        name = path.name.lower()

        if name == FIRST_RUN_STATE_FILENAME:
            return True

        if name == FIRST_RUN_TEMP_FILENAME:
            return True

        return name.startswith(
            INVALID_STATE_PREFIX
        )
