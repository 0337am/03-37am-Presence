# Changelog

## v2.4.0 - Atmosphere Update

Released 13 July 2026.

### Added

- Added custom Atmosphere backgrounds with local image import, validation, blur, opacity, dim overlay, enable, and reset controls.
- Added a background renderer with cached source images and cached blurred output for smoother live adjustment.
- Added glass-style Dashboard, Presence, and Settings cards so custom backgrounds can show through.
- Added Atmosphere values to settings backups while excluding custom background images and local file paths.

### Improved

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

- Branding text unexpectedly resetting.
- Sidebar and Dashboard themes not updating together.
- Corrupted navigation symbols.
- Duplicate Dashboard cleanup methods.
- Inconsistent hardcoded page colours.

### Notes

- Listening history was still session-based in this release.
