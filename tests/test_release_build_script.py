import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

BUILD_SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "scripts"
    / "build_release.ps1"
)


def build_script_source() -> str:
    return BUILD_SCRIPT_PATH.read_text(
        encoding="utf-8-sig"
    )


class ReleaseBuildScriptTests(unittest.TestCase):
    def test_build_script_exists(self):
        self.assertTrue(
            BUILD_SCRIPT_PATH.is_file()
        )

    def test_build_script_reads_release_metadata(self):
        source = build_script_source()

        required_values = (
            "src\\version.py",
            "APP_VERSION",
            "RELEASE_NAME",
            "Get-ReleaseMetadata",
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_build_script_uses_expected_toolchain(self):
        source = build_script_source()

        required_values = (
            'C:\\Python314\\python.exe',
            "-m PyInstaller",
            "03-37am Presence.spec",
            "ISCC.exe",
            "03-37am-Presence.iss",
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_build_script_creates_release_artifacts(self):
        source = build_script_source()

        required_values = (
            "03-37am-Presence-Setup-v",
            "03-37am-Presence-v",
            "SHA256SUMS.txt",
            "build-manifest.txt",
            "Get-FileHash",
            "SHA256",
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_build_script_validates_windows_metadata(self):
        source = build_script_source()

        required_values = (
            "FileVersion",
            "ProductVersion",
            "ProductName",
            "FileDescription",
            "WindowsVersion",
            "ExpectedDescription",
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_build_script_uses_canonical_product_name(self):
        source = build_script_source()

        self.assertIn(
            (
                '$ProductName -ne '
                '"03:37am Presence"'
            ),
            source,
        )

        self.assertIn(
            '"03:37am Presence - " +',
            source,
        )

    def test_build_script_has_safe_build_controls(self):
        source = build_script_source()

        required_values = (
            "[switch]$Force",
            "[switch]$ValidateOnly",
            "[switch]$SkipRepositoryStateCheck",
            "The repository must be clean",
            "Use -Force to replace it",
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_build_script_contains_no_release_specific_values(self):
        source = build_script_source().lower()

        forbidden_values = (
            'app_version = "2.6.0"',
            'app_version = "2.7.0"',
            'app_version = "2.8.0"',
            "library & insights update",
            "updates & distribution",
            "first-run polish",
            "v2.6-final-release-artifacts",
        )

        for forbidden_value in forbidden_values:
            self.assertNotIn(
                forbidden_value,
                source,
            )

    def test_build_script_contains_no_personal_paths(self):
        source = build_script_source().lower()

        forbidden_values = (
            "c:\\users\\gtafe",
            "03-37am-presence-clean",
            "03-37am-presence-v2.7-backups",
            "03-37am-presence-v2.8-backups",
        )

        for forbidden_value in forbidden_values:
            self.assertNotIn(
                forbidden_value,
                source,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
