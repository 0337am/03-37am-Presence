import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = (
    REPOSITORY_ROOT
    / "installer"
    / "03-37am-Presence.iss"
)


def installer_source() -> str:
    return INSTALLER_PATH.read_text(
        encoding="utf-8-sig"
    )


class InstallerTemplateTests(unittest.TestCase):
    def test_installer_template_exists(self):
        self.assertTrue(
            INSTALLER_PATH.is_file()
        )

    def test_installer_requires_release_metadata(self):
        source = installer_source()

        self.assertIn(
            "#ifndef MyAppVersion",
            source,
        )
        self.assertIn(
            "#ifndef MyReleaseName",
            source,
        )
        self.assertIn(
            (
                "#error MyAppVersion must be supplied "
                "by the release build script."
            ),
            source,
        )
        self.assertIn(
            (
                "#error MyReleaseName must be supplied "
                "by the release build script."
            ),
            source,
        )

    def test_installer_preserves_upgrade_identity(self):
        source = installer_source()

        required_values = (
            "AppId=0337am.Presence.Desktop",
            (
                "DefaultDirName={autopf}"
                "\\03-37am Presence"
            ),
            "PrivilegesRequired=admin",
            "ArchitecturesAllowed=x64compatible",
            (
                "ArchitecturesInstallIn64BitMode="
                "x64compatible"
            ),
            "CloseApplications=yes",
            "RestartApplications=no",
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_installer_uses_repository_relative_paths(self):
        source = installer_source()

        required_values = (
            "SourceDir=..",
            "OutputDir=release",
            "SetupIconFile=icons\\app_icon.ico",
            (
                'Source: "dist\\'
                '03-37am Presence.exe"'
            ),
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_installer_uses_supplied_version_metadata(self):
        source = installer_source()

        required_values = (
            "AppVersion={#MyAppVersion}",
            (
                "OutputBaseFilename="
                "03-37am-Presence-Setup-v"
                "{#MyAppVersion}"
            ),
            (
                "VersionInfoVersion="
                "{#MyAppVersion}.0"
            ),
            (
                "VersionInfoDescription="
                "{#MyAppName} - {#MyReleaseName}"
            ),
            (
                "VersionInfoProductVersion="
                "{#MyAppVersion}.0"
            ),
        )

        for required_value in required_values:
            self.assertIn(
                required_value,
                source,
            )

    def test_installer_contains_no_personal_paths(self):
        source = installer_source().lower()

        forbidden_values = (
            "c:\\users\\",
            "gtafe",
            "03-37am-presence-clean",
            "v2.6-final-release-artifacts",
            "library & insights update",
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
