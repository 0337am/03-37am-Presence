# 03:37am Presence

03:37am Presence is a Windows desktop app that turns your current media and custom status choices into a polished Discord Rich Presence. It includes a live customisable dashboard, custom Link cards, listening history, automatic AFK handling, custom themes, custom blurred Atmosphere backgrounds, personal artwork hosting, and privacy-aware settings backup and restore.

## v2.4.0 highlights

- Atmosphere backgrounds let you choose a local image, blur it, dim it, and tune its visibility behind the app.
- Dashboard, Presence, and Settings cards now use a softer glass look so custom backgrounds can show through while text stays readable.
- Atmosphere sliders support live preview with cached rendering for smoother adjustment.
- Background images stay local to the device and are never included in settings backups.
- Settings backups now include Atmosphere blur, opacity, and dim values while excluding the custom background image and local file path.

## Core features

- Discord Rich Presence for Spotify and supported browser media.
- Custom Dashboard Link cards with optional website icons.
- Dashboard layout profiles and snap-to-grid editing.
- Custom presence modes and presets.
- Persistent listening history backed by SQLite.
- Recently Played artwork caching.
- Automatic AFK presence with restoration of the previous mode.
- Theme presets, custom colours, editable title and subtitle, an optional fixed About footer, and fixed app-icon About artwork.
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
5. Unlock the Dashboard layout when you want to move, resize, overlap, hide, restore, delete, snap, profile, or reset cards.
6. Use Settings to control themes, media sources, artwork hosting, startup behaviour, storage, diagnostics, and backups.

The About-page thank-you footer can be shown or hidden, but its wording is fixed as part of the application.

## Settings backup and restore

Settings backups are versioned JSON files. By default they include portable UI, theme, Atmosphere slider, branding text, media-source, Auto AFK, window, startup, dashboard-layout, Dashboard Layout Profile, custom Link-card, and Presence Preset settings. Local artwork files, preset image files, Atmosphere background images, favicon caches, OAuth tokens, credentials, and local paths stay private on the device.

The following are always excluded:

- Listening history.
- Artwork cache files.
- Link-card favicon/icon cache files.
- OAuth tokens and API credentials.
- Diagnostics.
- Local file paths.
- Custom Atmosphere background images.
- Custom sidebar image files.

Artwork-hosting identifiers are excluded unless the user explicitly enables the opt-in checkbox before export. Every restore is validated first, and the app creates a private local safety snapshot before changing settings.

## Local data and privacy

App-managed data such as the Library database, artwork cache, Link-card icon cache, dashboard layout, layout profiles, logs, and private restore snapshots is stored under:

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
