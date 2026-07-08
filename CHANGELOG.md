# Changelog

## v2.0.0 — Smart Presence Update

### Major features

- Completely redesigned Dashboard with live Discord, media, Library, and Auto AFK status.
- Added persistent SQLite listening history and Library statistics.
- Added Spotify and browser-media detection, including SoundCloud support.
- Added persistent album-art thumbnails for Recently Played.
- Added automatic AFK switching with restoration of the previous presence mode.
- Added system-tray presence-mode quick controls.
- Added direct navigation from Dashboard controls to exact Settings sections.
- Added Data & Storage controls with CSV export and cache-management tools.
- Added Diagnostics & Support with live status reporting and clipboard export.
- Added Library source filtering and sorting.
- Improved Discord and media shortcut buttons throughout the Dashboard.
- Improved compact-mode layout, sidebar navigation, themes, and visual polish.

### Upgrade notes

- Existing Library data and artwork caches are preserved during upgrades.
- The app now uses a permanent Windows identity: `0337am.Presence.Desktop`.
- User settings, presence modes, themes, source preferences, and Auto AFK settings remain persistent.

\# 03:37am Presence Changelog



\## v1.2.0 — Vanity Update



\### Added



\- Custom application branding

\- Custom title, subtitle, footer, and portrait image

\- Multiple built-in theme presets

\- Custom background, sidebar, card, accent, text, muted, and border colours

\- Compact interface mode

\- Discord-style activity previews

\- New application, taskbar, tray, and executable icon

\- Windows executable version metadata



\### Improved



\- Redesigned Dashboard page

\- Redesigned Presence page

\- Redesigned Library page

\- Redesigned About page

\- Shared live theme system across every page

\- More compact layouts and improved spacing

\- Cleaner media and Discord connection status displays

\- Improved Library empty state and session track counter

\- Branding now updates immediately throughout the application

\- Cloudinary artwork configuration no longer depends on a packaged `.env` file



\### Fixed



\- Branding text unexpectedly resetting

\- Sidebar and Dashboard themes not updating together

\- Corrupted navigation symbols

\- Duplicate Dashboard cleanup methods

\- Inconsistent hardcoded page colours



\### Notes



\- Auto AFK detection is planned for a future major release.

\- Listening history remains session-based and resets when the application closes.

