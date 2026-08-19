import inspect
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import src.ui.settings as settings_module


SETTINGS_CLASS = next(
    value
    for _, value in inspect.getmembers(
        settings_module,
        inspect.isclass,
    )
    if value.__module__ == settings_module.__name__
    and hasattr(
        value,
        "export_library_csv",
    )
)


class FakeStatus:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = str(text)


class FakeHistoryStore:
    def __init__(
        self,
        *,
        tracks=(),
        events=(),
    ):
        self.tracks = tracks
        self.events = events
        self.track_limits = []
        self.event_limits = []

    def list_tracks(self, *, limit):
        self.track_limits.append(limit)
        return self.tracks

    def list_events(self, *, limit):
        self.event_limits.append(limit)
        return self.events


class FakeSettingsPage:
    def __init__(
        self,
        directory,
        history_store,
    ):
        self._directory = Path(directory)
        self.history_store = history_store
        self.status = FakeStatus()

    def data_directory(self):
        return self._directory


class SettingsLibraryExportTests(
    unittest.TestCase
):
    def test_library_summary_export(
        self,
    ):
        with TemporaryDirectory() as directory:
            track = SimpleNamespace(
                title="Track"
            )

            store = FakeHistoryStore(
                tracks=(track,)
            )

            page = FakeSettingsPage(
                directory,
                store,
            )

            selected = (
                Path(directory)
                / "summary"
            )

            destination = selected.with_suffix(
                ".csv"
            )

            dialog = SimpleNamespace(
                getSaveFileName=Mock(
                    return_value=(
                        str(selected),
                        "CSV files (*.csv)",
                    )
                )
            )

            writer = Mock(
                return_value=(
                    destination,
                    1,
                )
            )

            with patch.object(
                settings_module,
                "QFileDialog",
                dialog,
            ), patch.object(
                settings_module,
                "write_track_summary_csv",
                writer,
            ):
                SETTINGS_CLASS.export_library_csv(
                    page
                )

        self.assertEqual(
            store.track_limits,
            [50000],
        )

        writer.assert_called_once_with(
            str(selected),
            (track,),
        )

        self.assertEqual(
            page.status.text,
            (
                "Library summary exported: "
                "1 tracks to summary.csv."
            ),
        )

    def test_activity_export(
        self,
    ):
        with TemporaryDirectory() as directory:
            event = SimpleNamespace(
                title="Confirmed"
            )

            store = FakeHistoryStore(
                events=(event,)
            )

            page = FakeSettingsPage(
                directory,
                store,
            )

            selected = (
                Path(directory)
                / "activity.csv"
            )

            dialog = SimpleNamespace(
                getSaveFileName=Mock(
                    return_value=(
                        str(selected),
                        "CSV files (*.csv)",
                    )
                )
            )

            writer = Mock(
                return_value=(
                    selected,
                    3,
                )
            )

            with patch.object(
                settings_module,
                "QFileDialog",
                dialog,
            ), patch.object(
                settings_module,
                "write_listening_activity_csv",
                writer,
            ):
                SETTINGS_CLASS.export_listening_activity_csv(
                    page
                )

        self.assertEqual(
            store.event_limits,
            [50000],
        )

        writer.assert_called_once_with(
            str(selected),
            (event,),
        )

        self.assertEqual(
            page.status.text,
            (
                "Listening activity exported: "
                "3 confirmed plays to activity.csv."
            ),
        )

    def test_cancelled_library_export_is_safe(
        self,
    ):
        store = FakeHistoryStore()

        page = FakeSettingsPage(
            ".",
            store,
        )

        dialog = SimpleNamespace(
            getSaveFileName=Mock(
                return_value=(
                    "",
                    "",
                )
            )
        )

        writer = Mock()

        with patch.object(
            settings_module,
            "QFileDialog",
            dialog,
        ), patch.object(
            settings_module,
            "write_track_summary_csv",
            writer,
        ):
            SETTINGS_CLASS.export_library_csv(
                page
            )

        self.assertEqual(
            store.track_limits,
            [],
        )

        writer.assert_not_called()

    def test_cancelled_activity_export_is_safe(
        self,
    ):
        store = FakeHistoryStore()

        page = FakeSettingsPage(
            ".",
            store,
        )

        dialog = SimpleNamespace(
            getSaveFileName=Mock(
                return_value=(
                    "",
                    "",
                )
            )
        )

        writer = Mock()

        with patch.object(
            settings_module,
            "QFileDialog",
            dialog,
        ), patch.object(
            settings_module,
            "write_listening_activity_csv",
            writer,
        ):
            SETTINGS_CLASS.export_listening_activity_csv(
                page
            )

        self.assertEqual(
            store.event_limits,
            [],
        )

        writer.assert_not_called()

    def test_export_failure_shows_warning(
        self,
    ):
        with TemporaryDirectory() as directory:
            store = FakeHistoryStore(
                tracks=(
                    SimpleNamespace(
                        title="Track"
                    ),
                )
            )

            page = FakeSettingsPage(
                directory,
                store,
            )

            selected = (
                Path(directory)
                / "summary.csv"
            )

            dialog = SimpleNamespace(
                getSaveFileName=Mock(
                    return_value=(
                        str(selected),
                        "CSV files (*.csv)",
                    )
                )
            )

            message_box = SimpleNamespace(
                warning=Mock()
            )

            writer = Mock(
                side_effect=RuntimeError(
                    "simulated disk failure"
                )
            )

            with patch.object(
                settings_module,
                "QFileDialog",
                dialog,
            ), patch.object(
                settings_module,
                "QMessageBox",
                message_box,
            ), patch.object(
                settings_module,
                "write_track_summary_csv",
                writer,
            ):
                SETTINGS_CLASS.export_library_csv(
                    page
                )

        message_box.warning.assert_called_once()

        warning_arguments = (
            message_box.warning.call_args.args
        )

        self.assertEqual(
            warning_arguments[1],
            "Export failed",
        )

        self.assertIn(
            "simulated disk failure",
            warning_arguments[2],
        )

    def test_settings_source_contains_both_exports(
        self,
    ):
        source = Path(
            "src/ui/settings.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"Export Library CSV"',
            source,
        )

        self.assertIn(
            '"Export Activity CSV"',
            source,
        )

        self.assertIn(
            '"Export confirmed listening activity CSV"',
            source,
        )

        self.assertIn(
            "write_track_summary_csv",
            source,
        )

        self.assertIn(
            "write_listening_activity_csv",
            source,
        )

        self.assertIn(
            "self.export_listening_activity_csv",
            source,
        )


if __name__ == "__main__":
    unittest.main()
