# 03:37am Presence

03:37am Presence is a Windows desktop app that turns your current media and custom status choices into a polished Discord Rich Presence. It includes a live dashboard, listening history, automatic AFK handling, custom themes, personal artwork hosting, and privacy-aware settings backup and restore.

## v2.1.0 highlights

- A freeform dashboard canvas with movable, resizable, overlapping, hideable, and lockable cards.
- Responsive Recently Played and Quick Access cards that adapt to their available space.
- Optional personal Cloudinary artwork hosting for music and custom presences.
- Paused tracks remain visible instead of disappearing from Discord.
- Portable settings backup and restore with validation, rollback, and private-by-default exports.
- The app remembers the last page you had open.

See [CHANGELOG.md](CHANGELOG.md) for the complete release history.

## Core features

- Discord Rich Presence for Spotify and supported browser media.
- Custom presence modes and presets.
- Persistent listening history backed by SQLite.
- Recently Played artwork caching.
- Automatic AFK presence with restoration of the previous mode.
- Theme presets, custom colours, editable title and subtitle, an optional fixed About footer, and sidebar artwork.
- System tray controls and Windows startup options.
- Diagnostics, data controls, CSV library export, and settings backup.

## Requirements

- Windows 10 or Windows 11.
- Python 3.14 is recommended when running from source.
- Discord desktop must be running for Rich Presence updates.

## Run from source

```powershell
git clone https://github.com/0337am/03-37am-Presence.git
cd 03-37am-Presence

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

The supported application entry point is `main.py`.

## Using the app

1. Open Discord.
2. Start 03:37am Presence.
3. Play media in Spotify or a supported browser.
4. Use the Presence page for custom, AFK, streaming, or preset activity modes.
5. Unlock the Dashboard layout when you want to move, resize, overlap, hide, or reset cards.
6. Use Settings to control themes, media sources, artwork hosting, startup behaviour, storage, diagnostics, and backups.

The About-page thank-you footer can be shown or hidden, but its wording is fixed as part of the application.

## Settings backup and restore

Settings backups are versioned JSON files. By default they include portable UI, theme, branding text, media-source, Auto AFK, window, startup, and dashboard-layout settings.

The following are always excluded:

- Listening history.
- Artwork cache files.
- OAuth tokens and API credentials.
- Diagnostics.
- Local file paths.
- Custom sidebar image files.

Artwork-hosting identifiers are excluded unless the user explicitly enables the opt-in checkbox before export. Every restore is validated first, and the app creates a private local safety snapshot before changing settings.

## Local data and privacy

App-managed data such as the Library database, artwork cache, dashboard layout, logs, and private restore snapshots is stored under:

```text
%LOCALAPPDATA%\0337am Presence
```

Some UI preferences use the current Windows user's settings store through Qt. Personal Cloudinary values are stored locally and must never be committed, bundled into a release, or included in public screenshots.

Crash reports can contain local paths and environment details. Review them before sharing.

## Build the Windows executable

Install the dependencies, then run:

```powershell
python -m PyInstaller "03-37am Presence.spec" --clean --noconfirm
```

The executable is written to `dist\03-37am Presence.exe`.

Before publishing a build, inspect the repository, executable, installer, documentation, screenshots, and release archive for credentials, account identifiers, local paths, caches, logs, personal images, and other user-specific data.

## Project structure

```text
assets/                  Built-in visual assets
icons/                   Application icons
src/artwork/             Artwork hosting and upload logic
src/discord/             Discord Rich Presence integration
src/library/             Persistent listening history
src/music/               Media detection and metadata
src/system/              AFK, startup, and settings backup services
src/ui/                  PyQt6 interface
main.py                  Supported application entry point
03-37am Presence.spec    PyInstaller build definition
version_info.txt         Windows executable metadata
```

## Troubleshooting

- If Discord does not connect, ensure the Discord desktop app is running.
- If media is not detected, check the enabled media sources in Settings.
- If the app appears to be missing, check the Windows system tray.
- Diagnostics and saved-data controls are available in Settings.
- Crash logs are stored in the local app data folder shown above.

## Security notes

Never commit local token caches, `.env` files, credentials, private settings exports, generated logs, or user-specific release files. The repository ignore rules cover common local cache and development artifacts, but every release still requires a final privacy inspection.
