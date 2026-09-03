# Changelog

## v3.4.0 - Multi-Presence

Released 4 September 2026.

### Added

- Added the Discord Application Library for saving named public Discord Application IDs with stable references that can be reused across Presences.
- Added per-Presence Discord Application assignment so Custom, Working, Sleep, AFK, and saved Presences can remember which Discord application identity they use.
- Added simultaneous Music + Secondary Presence support using independent Discord application sessions, allowing Music to remain active while a separate non-Music activity is shown.
- Added Secondary Presence controls to Presence Studio, including Apply as Secondary and Clear Secondary while Music remains the primary Presence.
- Added a Discord Application selector directly to Presence Studio using the shared Application Library.
- Added configurable artwork hover text for non-Music Presences. Leaving the field blank omits the Discord artwork tooltip entirely, while entered text is shown as the chosen hover label.
- Added artwork hover-text support to manual AFK, Auto AFK, Working, Sleep, saved Presences, and Secondary Presence.

### Improved

- Saved Presences now retain both their Discord Application assignment and artwork hover text when saved, reopened, duplicated, or updated.
- Settings Backup and Restore now includes Discord Application Library entries so application assignments remain portable with the rest of the supported Presence configuration.
- Existing global custom Discord Application ID configuration migrates into the Application Library without discarding the user's existing identity choice.
- Deleted or unavailable application references fail closed instead of silently switching to an unintended identity.
- Simultaneous lanes reject duplicate Discord Application IDs, preventing two Presence sessions from competing for the same Discord application.
- Music and Secondary updates remain isolated so changing or clearing one lane does not incorrectly replace the other.

### Safety and privacy

- Discord Application Library entries contain public Application IDs only. 03:37am Presence does not request Discord Client Secrets, bot tokens, user tokens, or self-bot credentials.
- Discord RPC lifecycle and multi-session ownership remain worker-managed rather than being moved into the UI.
- Music playback behavior and the existing Spotify safety boundaries remain unchanged.

### Upgrade notes

- Existing saved Presences that do not contain the new optional fields remain compatible and default safely.
- Existing v3.3.0 settings and Desktop Companion configuration remain part of the normal in-place upgrade path.
- The v3.4.0 installer and standalone build continue to use the established release, checksum, and update infrastructure.

## v3.3.0 - Desktop Companion

Released 1 September 2026.

### Added

- Added **Desktop Companion**, an optional transparent desktop overlay using a user-selected local PNG, JPG/JPEG, WebP, or animated GIF.
- Added Companion controls for scale, opacity, always-on-top behavior, click-through, remembered position and monitor, fullscreen hiding, and animated GIF speed.
- Added direct local dragging while click-through is disabled, including persisted placement and recovery of completely unreachable positions without forcing intentionally partial off-screen placement back onscreen.
- Added monitor-aware restore behavior and optional same-monitor fullscreen hiding with low-frequency, read-only foreground-window detection.
- Added a dedicated Desktop Companion section in Settings, a synchronized system-tray toggle, and an optional Quick Access shortcut.

### Improved

- Desktop Companion GIF playback uses a memory-backed Qt movie buffer so the source GIF is not kept locked by the running overlay.
- Companion visibility, Settings state, tray state, and Quick Access all reuse the same production runtime and preference ownership path.
- Quick Access cards now refresh their layout geometry when resized, apply the calculated responsive row height, and distribute incomplete final rows across the available width instead of leaving stale empty space.

### Safety, compatibility, and upgrade behavior

- Desktop Companion is local-only. Companion images are not uploaded to Cloudinary or another network service.
- This release does not add global keyboard or mouse hooks, Raw Input handling, simulated input, reactive key/click behavior, or foreground-focus manipulation.
- Desktop Companion remains separate from Presence Studio and does not alter Discord Rich Presence publication or playback ownership.
- Existing Dashboard layouts, Quick Access preferences, Presence data, Library data, Spotify connection state, tray behavior, updater identity, and prior settings continue using their established upgrade paths.

## v3.2.2 - Window & Tray Fixes

Released 1 September 2026.

### Fixed

- Fixed the main-window startup handoff so a recreated Qt window handle is recovered before the staged window is moved to its final onscreen position.
- Fixed the close button (`X`) so it reliably hides the main window to the system tray while keeping 03:37am Presence running.
- Fixed **Tray -> Hide window** so it reliably hides the main window after startup, while **Tray -> Open** restores it normally and **Tray -> Quit** remains the explicit full-shutdown path.

### Safety, compatibility, and upgrade behavior

- Startup hide suppression is now limited to the active native startup staging window and cannot remain active after that staging phase has ended.
- The existing startup phantom-window protection remains in place, including the native offscreen staging and final handoff behavior.
- Normal Windows taskbar minimize behavior is unchanged.
- Existing settings, Presence data, Discord behavior, Spotify playback, Library data, Dashboard layouts, Quick Access configuration, and updater identity continue using their established upgrade paths.

## v3.2.1 - Custom Presence Party

Released 28 August 2026.

### Added

- Added optional Party / Group controls to Custom Presence in Presence Studio, with editable current-member and maximum-member values.
- Custom Presence can now publish Discord's native Rich Presence party-size metadata so Discord itself renders the native group icon and `(x of y)` member count.
- Party information is preserved through Custom Presence settings and Presence Library presets, including saved member values when the Discord display option is turned off.

### Improved

- Added app-owned themed chevrons to the Party member controls, with white arrows while active and a muted presentation while the controls are disabled.

### Safety, compatibility, and upgrade behavior

- Party information is Custom Presence only and is omitted entirely when disabled or when another Presence mode is active.
- Existing settings and schema-1 Presence presets remain compatible; older data defaults Party information to off with safe 1-of-2 editor defaults.
- Discord RPC lifecycle and publication remain on the existing worker-owned path, with no Discord client secret, bot token, user token, foreground activation, or simulated input introduced.

## v3.2.0 - Playback & Quick Access

Released 28 August 2026.

### Added

- Added a complete Dashboard playback control row for Shuffle, Previous, Play/Pause, Next, and Repeat, with app-owned themed icons and live Spotify state.
- Added direct Dashboard seeking through the existing playback coordinator, with a thin progress rail and an invisible interaction overlay that keeps the presentation clean.
- Added playback-cycle detection for trusted Spotify Repeat One loops, including Discord elapsed-timer resets and an optional `Loop ×N` counter.
- Added an optional Spotify Queue Dashboard card with a current-track row and Up Next presentation.
- Added Quick Access 2.0 with persistent ordering, visibility, add/remove management, reset-to-defaults, and app-owned shortcut icons.
- Added Quick Access destinations for Presence modes and saved Presence presets, Launcher Cards, and Spotify playlists.
- Added a grouped and searchable Spotify playlist picker so playlist shortcuts can be added without flooding the root shortcut catalogue.

### Improved

- Spotify Queue presentation reconstructs local-file positions while Shuffle is off, including mixed local/catalogue boundaries and omitted catalogue anchors observed during live validation.
- When Shuffle is on, Queue now uses an explicitly partial Spotify-visible presentation because Spotify does not expose exact shuffled local-file positions.
- Quick Access resolves current metadata for saved Presence presets, Launcher Cards, and Spotify playlists while keeping stale managed entries removable instead of deleting user choices silently.
- Playback controls, seek, shuffle, repeat, Queue, and Quick Access were exercised through expanded automated and live acceptance coverage.

### Safety, compatibility, and upgrade behavior

- Dashboard playback actions continue routing through the app's existing trusted playback services and coordinator. Quick Access does not launch Spotify URIs, simulate input, steal foreground focus, or introduce a second playback engine.
- Spotify playlist Quick Access opens the existing in-app playlist detail view and does not start playback automatically.
- Existing Quick Access users retain the original four default shortcuts unless they choose to customize them; preferences remain schema-compatible and invalid data continues using the established recovery path.
- Existing settings, Dashboard layouts, Presence presets, Launcher Cards, Library data, Spotify connection state, and updater identity continue using their established upgrade paths.

## v3.1.0 - Discord Presence Studio

Released 15 August 2026.

### Added

- Added a reusable Discord profile and activity preview with connected Discord identity, avatar presentation, music state, and generic custom Presence rendering.
- Added Presence Studio with a searchable and filterable Presence Library, pinned-first cards, saved Presence editing, rename, duplicate, pin, and delete actions.
- Added up to two optional Discord Rich Presence Link Buttons for Music, AFK, Sleep, Working, and Custom Presences.
- Added a per-Presence `Show on Discord` control so saved Link Button labels and URLs can be retained without publishing them.
- Added live inert Link Button representations and visibility feedback to the Presence Studio preview.

### Improved

- Discord music presentation now follows the app's established media truth while keeping generic Presence modes and music presentation cleanly separated.
- Returning from a non-music Presence to Music invalidates stale presentation artwork state so current artwork can be restored correctly.
- Music Presence can now retain its own saved Link Buttons while track title, artist, artwork, timing, and playback state continue updating automatically.
- Presence Library presets preserve Link Button configuration through load, save, update, duplication, and settings backup flows.
- Presence Studio now gives clear feedback when Link Buttons are visible to others, hidden while still saved, or not yet configured.

### Safety, privacy, and upgrade behavior

- Discord preview rendering remains local presentation only and does not require a Discord user token, self-bot behavior, or access to private Discord credentials.
- Link Buttons are limited to Discord's two-button Rich Presence model and the app accepts browser-safe HTTP or HTTPS URLs only.
- Preview Link Buttons are inert visual elements and do not open URLs from inside Presence Studio.
- Discord does not show a user's own Rich Presence buttons to that same user; other users can see published buttons.
- Existing Presence modes, presets, settings, Dashboard behavior, Spotify integration, and Library data continue using their established upgrade paths.
- Existing saved Presence data remains compatible. Link Button fields default to hidden and empty when older settings or presets do not contain them.
- Disabled Presence continues clearing Discord activity and never publishes Link Buttons.

## v3.0.1 - Updater Relaunch Fix

Released 13 August 2026.

### Fixed

- Fixed the automatic post-update launch after upgrading from a PyInstaller one-file build. The installer now starts the newly installed app with `PYINSTALLER_RESET_ENVIRONMENT=1`, forcing a fresh runtime extraction instead of reusing the previous app's `_MEI` directory.
- Prevented the post-install launch from failing with a missing `python314.dll` after the updater exits and PyInstaller cleans up the old extraction directory.

### Upgrade notes

- Update discovery, SHA-256 verification, installer download, and in-place installation remain unchanged.
- Existing settings, local application data, and the established installer identity continue to use the same upgrade paths.
- This hotfix repairs the automatic relaunch step observed during the real v2.9.0 to v3.0.0 updater acceptance test.

## v3.0.0 - Overhaul

Released 13 August 2026.

### Added

- Added Settings categories for a cleaner, more focused configuration experience across General, Discord, Customization, Spotify, Local Music, Playback, Library & Data, Updates, and Advanced sections.
- Added optional custom Discord Application ID support so users can run Rich Presence through their own Discord application identity while retaining the official 03:37am Presence identity by default.
- Added Spotify playlist track artwork, including artwork support for resolved local Spotify playlist entries.
- Added a real audio-reactive Spotify equalizer powered by process-specific Windows audio capture and broad-band spectrum analysis instead of the previous simulated animation.

### Improved

- The Dashboard equalizer now follows actual Spotify audio with adaptive dynamics, quieter-song protection, responsive attack and release behaviour, and a balanced eight-band presentation.
- Spotify process audio capture automatically recovers when Spotify is closed and reopened without requiring 03:37am Presence to restart.
- Equalizer pause, resume, seeking, and song changes follow the existing Windows media presentation state while keeping raw captured audio ephemeral and outside persistent storage.
- Spotify playlist artwork loading now preserves safe fallbacks and avoids replacing good artwork with failed or stale results.

### Playback, privacy, and performance safety

- Spotify process audio analysis does not use Spotify UI automation, simulated keyboard or mouse input, foreground-window activation, or a playback fallback that opens Spotify.
- Foreground testing confirmed that neither 03:37am Presence nor Spotify takes foreground focus during remote Spotify song changes.
- Captured Spotify audio is analysed in memory only; the spectrum service publishes normalized band levels and does not save raw audio to disk.
- Live performance testing kept the complete 03:37am Presence process within the accepted CPU guard while the audio-reactive equalizer was active.

### Upgrade notes

- Existing v2.9 settings, Dashboard layouts, Layout Profiles, Link Cards, Launcher Cards, Presence Presets, Library history, Spotify connection state, first-run state, media-source preferences, and global media-hotkey preferences continue to use the existing upgrade paths.
- Custom Discord Application ID mode is optional. Existing users continue using the official Discord application identity unless they explicitly choose a custom ID.
- The v3.0.0 release keeps the existing installer identity so supported older installations can be upgraded in place.

## v2.9.0 - Spotify Integration

Released 10 August 2026.

### Added

- Added an opt-in Spotify account connection backed by OAuth session handling and the app's credential-storage boundary.
- Added Spotify playlist browsing with pagination, playlist detail views, catalogue-track playback, and support for local Spotify playlist entries resolved by their playlist position.
- Added a dedicated Liked Songs experience with pagination, native playback, and current-track highlighting.
- Added Spotify Search across tracks, albums, artists, and playlists with live search, artwork, result navigation, playback, and Load more results pagination.
- Added Spotify Album Detail with album metadata, track listings, current-playing state, individual-track playback, and album-context playback.
- Added Spotify Artist Detail with artist metadata, paginated releases, and direct navigation from artist releases into Album Detail.
- Added local-music indexing and an optional startup scan to improve resolution of Spotify local-file playlist entries.

### Improved

- Spotify playback now uses the Spotify Web API and existing Spotify desktop session instead of foreground-driving UI automation.
- Search, Playlist Detail, Liked Songs, and Album Detail use Windows media playback state as the source of truth for current-track presentation instead of assuming the most recently clicked row is playing.
- Playlist playback preserves Spotify playlist position where required so local-file entries can be started without opening or controlling the Spotify user interface.
- Album playback can preserve album context while starting the selected catalogue track.
- Search results can now be expanded incrementally without replacing already-visible rows, and failed pagination requests preserve the existing result set.
- Artwork cache recovery can repair stale fallback artwork when a better current image becomes available.

### Privacy and playback safety

- Spotify authentication remains optional and is never enabled automatically by onboarding or an upgrade.
- Spotify playback does not use Spotify UI automation, `QMediaPlayer`, or foreground-window activation as a playback fallback.
- Starting Spotify playback from 03:37am Presence is designed not to steal keyboard, mouse, or foreground focus from the user's current application.
- Spotify token and credential data is not included in portable settings backups.
- Local music scanning and indexing remain local to the device and do not upload the user's local music library.

### Upgrade notes

- Existing v2.8 settings, Dashboard layouts, Layout Profiles, Link Cards, Launcher Cards, Presence Presets, Library history, first-run state, media-source preferences, and global media-hotkey preferences continue to load normally.
- Spotify connection remains opt-in. Existing users can continue using the app without connecting a Spotify account.
- Local-music startup scanning is configurable and does not require changing existing media-source preferences.
- Playlist artwork enrichment beyond the current Spotify integration is deferred to a later major UI overhaul.

## v2.8.0 - First-Run Polish

Released 8 August 2026.

### Added

- Added reusable Windows media controls for play/pause, previous, next, shuffle, repeat, and seeking when supported by the active media session.
- Added configurable global media hotkeys backed by the Windows hotkey API and bridged safely into the Qt application.
- Added persistent media-hotkey preferences with duplicate-shortcut validation, safe reload behavior, and settings backup and restore support.
- Added a compact first-run Welcome experience with direct routes to Media Sources, Discord Presence, and Global Media Controls.
- Added durable local first-run state so incomplete onboarding can return on the next launch without relying on Qt settings.

### Improved

- Global media hotkeys remain disabled by default and are only registered after the user explicitly enables them.
- Existing installations are silently marked as having completed onboarding, so upgrading users are not shown a first-launch screen.
- Fresh installations keep onboarding visible even when the application is started with `--minimized`.
- Completed installations now honor `--minimized` by remaining in the system tray until opened.
- First-run evaluation occurs before application-managed LocalAppData artifacts and the single-instance lock can make a fresh installation look established.

### Fixed

- Fixed Windows startup launches carrying `--minimized` without the main application actually honoring the argument.
- Fixed fresh-install detection being affected by the single-instance lock file created during startup.
- Protected invalid or unsupported first-run state by quarantining it before recovery.

### Privacy and upgrade behavior

- First-run state is stored locally under `%LOCALAPPDATA%\0337am Presence` and is kept separate from portable settings backups.
- The Welcome experience does not automatically enable global hotkeys, Windows startup, browser media sources, Spotify OAuth, or other optional features.
- Existing settings, Dashboard layouts, Library history, Presence configuration, themes, media-source preferences, and global media-hotkey preferences continue to load normally.
- Media hotkey commands control the existing local media session only and do not stream audio or upload listening activity.
- Restoring application settings does not intentionally retrigger first-run onboarding.

## v2.7.0 - Updates & Distribution

Released 17 July 2026.

- Added repeatable standalone and installer release builds with matching Windows metadata.
- Added GitHub release checks with friendly offline, rate-limit, malformed-response, and no-release states.
- Added background update downloads with visible progress and mandatory SHA-256 verification.
- Added explicit approval before installation and an integrity recheck immediately before launch.
- Added safe shutdown through the existing tray lifecycle after the installer starts.
- Added a guided Cloudinary setup dialog with official links and a copyable checklist.
- The app never requests Cloudinary API keys, API secrets, passwords, or access tokens.
- Updates do not use silent installation, shell execution, automatic downgrades, or listening-data uploads.

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
