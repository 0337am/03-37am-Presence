# Changelog

## v2.6.0 - Library & Insights Update

Released 17 July 2026.

### Added

- Added a detailed listening-event timeline for confirmed playback, stored alongside the existing aggregate Library history.
- Added SQL-backed Library searching, source filtering, date ranges, sorting, stable totals, and paginated result browsing.
- Added Library Insights covering aggregate tracks, plays, artists, albums, top tracks, top artists, and top albums.
- Added confirmed-activity insights covering listening days, current and longest streaks, first and latest confirmed plays, and recent playback activity.
- Added a dedicated Listening Activity CSV export for confirmed playback events.
- Added permanent automated coverage for Library queries, listening events, insights, exports, and Settings export integration.

### Improved

- Improved Library performance by moving filtering, sorting, date boundaries, totals, and pagination into the SQLite query layer.
- Improved Library wording so all-time aggregate history remains clearly separated from confirmed activity recorded by the newer timeline.
- Improved CSV exports with UTF-8 compatibility, automatic `.csv` filenames, atomic file replacement, parent-folder creation, and header-only empty exports.
- Improved artwork recovery so matching cached artwork is restored before Dashboard and Discord presence updates.
- Expanded the Library interface with date controls, result summaries, navigation controls, accessible names, disabled states, and responsive Insights presentation.

### Fixed

- Fixed an artwork synchronisation race where Recently Played could show artwork before Now Playing or Discord presence updated.
- Fixed first-observed Paused tracks so a later transition to Playing records one confirmed playback event.
- Fixed pause and resume transitions after confirmed playback so they do not create duplicate listening events.
- Fixed stale artwork recovery so cached artwork from another track cannot be applied to the current song.

### Privacy and security

- Listening history and detailed playback events remain local to the device and are excluded from portable settings backups.
- Library and activity exports occur only after an explicit user action.
- CSV cells beginning with spreadsheet-formula characters are neutralised before export.
- CSV files are written to temporary files and atomically replaced, protecting existing exports when a write fails.
- Listening Activity exports include confirmed Playing events only and exclude legacy Paused timeline entries.

### Upgrade notes

- Existing v2.5 settings, Dashboard layouts, Layout Profiles, Link Cards, Launcher Cards, Presence Presets, Atmosphere settings, and aggregate listening history continue to load normally.
- The Library database upgrades automatically to schema version 2 while preserving existing track records and play counts.
- Detailed timeline tracking begins after the database upgrade. Earlier aggregate plays cannot be reconstructed as dated events, so confirmed-play totals, listening days, and streaks initially cover only newly recorded activity.
- Existing settings backups remain restorable because listening history and Library database contents are intentionally excluded from portable settings backups.
- A restart is recommended after restoring settings so every service and Dashboard component reloads the restored values.

## v2.5.0 - Control Room Update

Released 15 July 2026.

### Added

- Added Launcher Cards for opening validated local applications and folders directly from the Dashboard.
- Added Launcher Card editing, duplication, deletion, hiding, restoring, responsive sizing, and optional custom card images.
- Added local Launcher Card image import with validation, scaling, deduplication, fallback artwork, and unused-image cleanup.
- Added Dashboard layout Undo and Redo with toolbar controls and `Ctrl+Z`, `Ctrl+Y`, and `Ctrl+Shift+Z` shortcuts.
- Added editing-session Revert so all layout changes made since entering edit mode can be restored together.
- Added keyboard card movement and resizing with one-pixel steps, Shift grid steps, Enter to save, Escape to cancel, and automatic save on focus change.
- Added magnetic alignment to nearby card edges, card centres, canvas edges, and the canvas centre.
- Added temporary visual alignment guides while moving and resizing cards.

### Improved

- Redesigned and polished the Dashboard Control Room toolbar, editing canvas, editor handles, compact layout, and locked or editing states.
- Improved Dashboard accessibility with explicit tab order, accessible names and descriptions, dynamic state information, focus styling, and keyboard-operable card handles.
- Expanded the Snap control so magnetic alignment takes priority and the existing 24 px grid remains available as a fallback.
- Improved Launcher Card opening with target revalidation immediately before launch and clear feedback for missing or changed targets.
- Improved Launcher Card layouts across tiny, compact, standard, and wide card sizes.
- Preserved each mouse drag, mouse resize, keyboard adjustment, preset change, and session revert as a single Undo or Redo history action.

### Privacy and security

- Launcher Card target paths and custom image paths stay local to the device and are excluded from portable settings backups.
- Launcher Cards reject relative paths, network targets, unsupported target types, malformed quoted paths, and mismatched application or folder targets.
- Script-like targets require explicit confirmation before opening, and every target is checked again immediately before launch.
- Launcher Card image imports accept only supported local image files and never upload images automatically.
- Settings backup validation rejects exported local Launcher Card targets and local Launcher Card image identifiers.

### Upgrade notes

- Existing v2.4 settings, Dashboard layouts, Layout Profiles, Link Cards, Presence Presets, Atmosphere settings, and listening history continue to load normally.
- Existing v2.4 and earlier settings backups remain restorable.
- Launcher Card target paths and custom images are intentionally excluded from portable backups. Restored Launcher Cards may require the local target or image to be selected again.
- A restart is recommended after restoring settings so every service and Dashboard component reloads the restored values.

## v2.4.0 - Atmosphere Update

Released 13 July 2026.

### Added

- Added custom Atmosphere backgrounds with local image import, validation, blur, opacity, dim overlay, enable, and reset controls.
- Added a background renderer with cached source images and cached blurred output for smoother live adjustment.
- Added glass-style Dashboard, Presence, and Settings cards so custom backgrounds can show through.
- Added Atmosphere values to settings backups while excluding custom background images and local file paths.

### Improved

- Replaced the default branding image with the app icon and removed the Yuno theme preset from the Theme picker.
- Improved Atmosphere slider behaviour with live preview, clearer labels, larger handles, and reduced repaint lag.
- Clarified Settings Backup & Restore copy so users know Atmosphere backgrounds are local-only and must be chosen again on each device.

### Privacy and security

- Custom Atmosphere background images are stored locally and are never exported in settings backups.
- Atmosphere restores blur, opacity, and dim values only. Restoring a backup clears the local background path and disables Atmosphere until a new image is chosen.

### Upgrade notes

- Existing v2.3 settings continue to load normally.
- Existing settings backups remain restorable.

## v2.3.0 - Presence Studio Update

Released 12 July 2026.

### Added

- Added Presence Presets so users can save, apply, update, duplicate, rename, pin, unpin, and delete reusable presence setups.
- Added pinned Presence Presets to Dashboard Quick Access for fast mode switching.
- Added Presence reset controls for clearing Custom presence data and returning to Music presence.
- Added an Artwork Manager area on the Presence page with image preview details, file size, dimensions, open-image, and open-folder actions.
- Added artwork import guardrails for supported image formats, broken image files, oversized images, and non-square Discord artwork tips.
- Added settings backup and restore support for Presence Presets.
- Added settings backup and restore support for Dashboard Layout Profiles.

### Improved

- Dashboard Quick Access now refreshes when Presence Presets are renamed, pinned, unpinned, deleted, or applied.
- Presence Preset empty states, button states, and status messages are clearer.
- Settings backups now cover Dashboard layouts, Dashboard Layout Profiles, custom Link cards, and Presence Presets together.
- Artwork controls now give clearer local-file feedback before Discord is updated.

### Privacy and security

- Presence Preset image files stay local and are excluded from settings backups.
- Local preset artwork paths are rejected during settings backup validation.
- Link-card favicon caches remain local and are excluded from settings backups.
- Artwork import only accepts PNG, JPG, JPEG, and WEBP images up to 10 MB.

### Upgrade notes

- Existing v2.2 Dashboard layouts, Link cards, and Layout Profiles continue to load normally.
- Existing v2.2 and v2.3 settings backups remain restorable.
- Presence Presets are included in new v2.3 settings backups, but preset image files are intentionally not exported.
- A restart is recommended after restoring settings so every service and Dashboard component reloads the restored values.

## v2.2.0 - Custom Dashboard Update

Released 11 July 2026.

### Added

- Added custom user-created Link cards for the Dashboard.
- Added safe web-only Link card destinations with support for `http://` and `https://`.
- Added Link card editing, duplication, deletion, hiding, restoring, moving, resizing, and overlapping.
- Added optional website favicon fetching for Link cards, with local caching and tiny-card fallbacks.
- Added responsive Link card layouts for tiny, small, medium, and large card sizes.
- Added Dashboard layout profiles so users can save, apply, and delete named layouts.
- Added snap-to-grid controls for cleaner Dashboard card movement and resizing.
- Added settings backup and restore support for custom Link cards.

### Improved

- Dashboard customisation now supports user-created cards alongside the built-in Dashboard cards.
- Settings backups now preserve custom Link cards while still excluding local favicon/icon caches.
- Layout profiles preserve card positions, sizes, visibility, overlap, order, and custom Link-card placement.
- Auto AFK now only activates from Music and Custom modes, so Sleep, Working, AFK, and Disabled modes are not overridden automatically.
- Link cards use the user-entered emoji first, then a fetched website icon, then a domain-letter fallback.

### Privacy and security

- Link cards only support normal web URLs in this release.
- Unsafe destinations such as local files, scripts, shell commands, executables, private-network redirects, and unsupported URI schemes are rejected.
- Link-card favicon caches remain local and are excluded from settings backups and public release files.
- Imported custom Link cards are validated before restore.

### Upgrade notes

- Existing v2.1 Dashboard layouts continue to load normally.
- Existing settings backups remain restorable.
- Custom Link cards are included in new v2.2 settings backups.
- Website favicons may need to be fetched again after restoring settings because icon caches are intentionally not exported.

## v2.1.0 - Personal Presence Update

Released 9 July 2026.

### Added

- Added optional personal Cloudinary artwork hosting for music and custom presences.
- Added an artwork-hosting settings card with validation and a connection test.
- Added a freeform Dashboard canvas with movable, resizable, overlapping, hideable, and lockable cards.
- Added responsive Recently Played rows that reveal more tracks when the card is taller.
- Added responsive Quick Access layouts for narrow, standard, and wide cards.
- Added versioned settings backup and restore with strict validation, automatic safety snapshots, and rollback on failure.
- Added privacy-safe backup defaults, with artwork-hosting identifiers available only through explicit opt-in.
- Added last-page memory so the app reopens where the user left it.

### Improved

- Paused songs now remain visible on Discord.
- Dashboard editor controls now float outside card content and follow cards during movement and resizing.
- Dashboard layouts now persist freeform position, size, visibility, order, and lock state.
- Existing grid layouts are migrated to the freeform layout format.
- Settings deep links and sidebar selection remain consistent when reopening the app.
- Refined the first-run branding and presence text defaults.
- Made the About-page thank-you footer fixed while keeping its visibility optional.

### Privacy and security

- Settings backups always exclude listening history, artwork caches, OAuth tokens, API credentials, diagnostics, local paths, and custom sidebar images.
- Sanitised repository history to remove a mistakenly tracked local token cache and compiled Python cache files.
- Strengthened ignore rules for local OAuth and token caches.
- Kept all development backups outside the repository.

### Upgrade notes

- Existing Library data and artwork caches are preserved.
- Existing Dashboard layouts are migrated automatically.
- Personal artwork-hosting values remain local.
- A restart is recommended after restoring settings so every service and Dashboard component reloads the restored values.

## v2.0.0 - Smart Presence Update

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
- The app uses the permanent Windows identity `0337am.Presence.Desktop`.
- User settings, presence modes, themes, source preferences, and Auto AFK settings remain persistent.

## v1.2.0 - Vanity Update

### Added

- Custom application branding.
- Custom title, subtitle, footer, and portrait image.
- Multiple built-in theme presets.
- Custom background, sidebar, card, accent, text, muted, and border colours.
- Compact interface mode.
- Discord-style activity previews.
- New application, taskbar, tray, and executable icon.
- Windows executable version metadata.

### Improved

- Redesigned Dashboard, Presence, Library, and About pages.
- Shared live theme system across every page.
- More compact layouts and improved spacing.
- Cleaner media and Discord connection status displays.
- Improved Library empty state and session track counter.
- Branding updates immediately throughout the application.
- Cloudinary artwork configuration no longer depends on a packaged `.env` file.

### Fixed

- Fixed the About branding image to use the built-in app icon instead of saved custom portrait paths.
- Branding text unexpectedly resetting.
- Sidebar and Dashboard themes not updating together.
- Corrupted navigation symbols.
- Duplicate Dashboard cleanup methods.
- Inconsistent hardcoded page colours.

### Notes

- Listening history was still session-based in this release.
