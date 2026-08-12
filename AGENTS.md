# AGENTS.md

## Project

This repository contains 03:37am Presence, a Windows desktop application built primarily with Python and PyQt6.

The application provides music-focused Discord Rich Presence, Spotify integration, Windows media-session integration, local music support, artwork handling, playback controls, Library and Insights features, Settings, tray behavior, updates, and release packaging.

Development is currently taking place on the v3.0.0-overhaul branch.

## Core Working Rules

- Inspect the relevant implementation and tests before editing.
- Prefer small, atomic, reviewable changes.
- Do not modify unrelated files.
- Do not perform speculative refactors during a focused feature or bug-fix patch.
- Preserve existing architecture unless the task explicitly requires an architectural change.
- Preserve existing public behavior unless the requested patch explicitly changes it.
- Prefer adding or extending focused regression tests for behavior changes.
- Never silently weaken an existing safety boundary to make a test pass.
- Do not delete or rewrite existing tests merely because they fail after a change.
- Explain unexpected failures rather than hiding them.

## Git Safety

- Always inspect the current branch, HEAD, and working tree before making changes.
- Do not discard, reset, clean, checkout, restore, or overwrite existing user changes unless explicitly instructed.
- Never run `git reset --hard`.
- Never run `git clean`.
- Never force-push.
- Never amend a commit unless explicitly instructed.
- Never commit unless explicitly instructed.
- Never push unless explicitly instructed.
- Never create, move, or delete tags unless explicitly instructed.
- Stage only the files explicitly intended for the accepted patch.
- Run `git diff --check` before a commit gate.
- Treat LF/CRLF warnings as informational unless they correspond to an actual diff or encoding problem.

## Testing Protocol

For code changes:

1. Run syntax or compile checks for touched Python files when appropriate.
2. Run focused tests covering the changed behavior.
3. Run nearby regression tests for affected components.
4. Run `git diff --check`.
5. Do not claim full-project acceptance unless the complete test suite has actually run successfully.

The full test suite is:

`C:\Python314\python.exe -m unittest discover -s tests -p "test_*.py" -v`

For automated Qt tests, normally use:

`QT_QPA_PLATFORM=offscreen`

For live/manual Windows UI testing, use:

`QT_QPA_PLATFORM=windows`

Python unittest legitimately writes progress and test output to stderr. Judge success by the process exit code and unittest result rather than stderr output alone.

## Windows and PowerShell

- Primary development platform is Windows 11.
- Primary shell is PowerShell.
- Repository path during current development is normally:
  `C:\Users\Gtafe\Desktop\03-37am-Presence-CLEAN`
- Python used for development is normally:
  `C:\Python314\python.exe`
- Prefer Windows-safe paths and behavior.
- Do not introduce Linux-only assumptions into production application behavior.
- Temporary helper scripts should normally use the system temporary directory rather than cluttering the repository or desktop.

## File and Encoding Safety

- Preserve existing encoding and newline behavior when modifying files.
- Be especially careful with large UI files and files that may contain a UTF-8 BOM.
- Do not rewrite an entire large file merely to make a tiny textual change unless a full rewrite is genuinely required.
- Avoid accidental whitespace-only or line-ending-only churn.
- `src/ui/main_window.py` has historically required careful encoding preservation.
- Do not modify `src/ui/welcome.py` solely to normalize encoding or BOM behavior.

## Absolute Playback and Focus-Safety Rules

Playback behavior must NEVER steal foreground focus from the user.

Never introduce behavior that:

- activates Spotify,
- foregrounds Spotify,
- visibly opens Spotify UI,
- minimizes or tabs out of a game,
- changes the foreground window merely to initiate playback.

Never reintroduce:

- `os.startfile("spotify:local:...")`
- Spotify UI Automation for playback
- simulated keyboard/mouse control of Spotify
- Qt `QMediaPlayer` as a fallback for Spotify or Spotify-local playlist playback

Spotify catalogue and playlist playback must continue through the existing Spotify Web API playback architecture.

Current intended playback path:

`SpotifyQtPlaybackRuntime -> SpotifyPlaybackService -> Spotify Web API`

For Spotify playlist playback:

- catalogue items use playlist context URI plus `offset.uri`
- local Spotify playlist items use playlist context URI plus numeric `offset.position`
- album playback uses album context plus `offset.uri`

Windows media/session state remains presentation truth for current playback state.

Do not casually alter conservative current-playing matching logic.

## Discord Presence Architecture

Discord RPC lifecycle belongs to the Discord presence worker thread.

- Do not connect, disconnect, clear, or recreate pypresence RPC directly from the UI thread.
- Identity changes must remain worker-owned.
- Do not put Discord reconnect/control commands into the maxsize=1 media update queue.
- Media queue replacement semantics must not be able to discard identity-switch requests.
- Preserve safe fallback to the official 03:37am Presence Application ID.
- Malformed custom Discord Application IDs must never brick application startup.
- Custom Discord identity accepts only a public Discord Application ID.
- Never request, store, log, or handle a Discord Client Secret for this feature.
- Never request, store, log, or handle a bot token.
- Never request, store, log, or handle a Discord user token.

## Spotify Security

- Spotify OAuth uses the existing PKCE architecture.
- Do not introduce a Spotify Client Secret into the desktop application.
- Do not expose access tokens or refresh tokens through UI models, logs, exceptions, repr output, or test diagnostics.
- Preserve DPAPI-backed credential storage and current-user protection boundaries.
- Network URLs and redirects must continue to pass existing trust validation.

## Local Music

- Preserve local-only path safety.
- Do not expose local filesystem paths through portable settings backups.
- Do not add network-path support unless explicitly requested and reviewed.
- Local scanning must remain cancellable and must not block the GUI thread.

## UI and Qt

- Preserve the existing PyQt ownership and threading boundaries.
- Avoid callbacks that can outlive deleted Qt objects.
- Delayed Qt callbacks must tolerate normal QObject lifetime changes where applicable.
- Avoid creating accidental top-level windows.
- Preserve the startup hidden/reveal architecture unless a task explicitly concerns startup behavior.
- Do not casually change `src/system/startup_native_stage.py`.
- Do not reintroduce the historical startup phantom-window behavior.

## Startup Phantom Window

The startup phantom-window issue was previously fixed and manually accepted.

Important invariant:

`install_startup_native_stage(MainWindow)`

must remain immediately before:

`window = MainWindow()`

unless a specifically scoped startup patch proves a different implementation safe.

Do not revive previous DWM-cloak experiments without explicit instruction.

## Artwork

- Artwork updates must not allow stale artwork from a previous track to overwrite the current track.
- Larger real artwork may repair a small cached fallback.
- A smaller fallback must not overwrite known-good cached artwork.
- Keep artwork behavior asynchronous where currently designed.
- Spotify playlist artwork work must not change playback behavior as a side effect.

## Settings and Preferences

- Preserve existing QSettings keys, stores, signals, callbacks, object names, and behavior unless migration is explicitly part of the task.
- Settings changes should respect category-scoped status messages.
- Reset behavior must remain safe and explicit.
- New persisted preferences require validation and safe fallback behavior.

## Release and Packaging

- End users must not require a separate Python installation.
- Preserve PyInstaller and Inno Setup release paths unless a release-specific change is requested.
- Do not modify release metadata as part of unrelated feature work.
- Do not build, publish, upload, tag, or release unless explicitly instructed.
- Do not sign artifacts unless explicitly instructed.

## Patch Workflow

When given a named patch or gate:

1. Confirm branch, HEAD, and working-tree state.
2. Inspect the relevant source and tests.
3. State the intended file set before editing when practical.
4. Make only the scoped change.
5. Run focused validation.
6. Run `git diff --check`.
7. Report exactly which files changed.
8. Stop before committing unless the user explicitly authorizes a commit.

If an unexpected failure appears outside the immediate feature, investigate it rather than automatically assuming the feature caused it.

## Communication

- Be precise about what was inspected, changed, tested, and not tested.
- Distinguish automated test success from manual UI acceptance.
- Do not claim a manual behavior was verified unless a human actually verified it.
- When a command fails, report the relevant error and current repository state.
- Do not hide warnings that could matter.
- Keep proposed changes understandable and reviewable.

## Current v3.0 Direction

Current v3.0 work includes:

- Settings reorganization and cleanup
- Custom Discord Presence identity
- broader UI/design overhaul
- Spotify playlist artwork overhaul

Do not assume roadmap items are approved for implementation merely because they are listed here. Work only on the explicitly assigned task.