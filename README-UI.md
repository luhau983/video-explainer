# AI Explainer — local workbench

Requires Python 3.10+. UI/server need only the Python standard library; no npm install is required. Original generation scripts have their own dependencies.

## Start

From this project directory:

```bash
python3 ui_server.py --port 39919
```

Open http://127.0.0.1:39919 on the SAME computer. Use `--port 0` to select a free port; read the printed URL. Port 3000 is reserved and rejected. Ctrl+C stops the server. Localhost-only, not for public deployment. A Telegram phone cannot access the computer's 127.0.0.1 directly.

## Implemented

- Edit/save script.md, style.md and existing scenes.csv rows.
- Select scenes and inspect descriptions, camera, motion and available media.
- Validate unique three-digit scene IDs, known character names, required fields and matching script/scene ID sets.
- Read character descriptions and see missing-sheet states.
- Generate real motion prompts offline using scripts/build_motion_prompts.py. Without audio timing the existing generator assumes 4.5 seconds per scene; this is NOT measured speech duration.
- Show actual available assets and explicitly unsupported generation steps.
- Atomic writes retain previous versions under ui-backups/. Review these backups before deleting them.

## Limitations

- Adding/removing script IDs is blocked unless scenes also match; coordinated script/scene import is not implemented yet. Edit both files directly with matching IDs to change scene count, then reload.
- Character descriptions are read-only in this UI.
- Image generation, TTS, video API and final export are NOT connected in the UI. No paid service is called by UI actions.
- Media previews are implemented but the supplied archive contains no media; real playback was not browser-tested.
- No authentication or multi-user collaboration; keep bound to localhost. Do not expose through a public tunnel without additional access control.

## Checks

```bash
python3 -m unittest test_ui -v
node --check ui/app.js
```

Five server tests pass. Browser verification exercised edit/save/reload/restore, invalid scene rejection, offline prompt generation, missing asset states and desktop/tablet/mobile layouts. No runtime JavaScript errors were observed; invalid input intentionally produces HTTP 400.

## Project files

ui_server.py — local HTTP server and project validation
ui/ — HTML, CSS and JavaScript
 test_ui.py — server/integration tests
scripts/ — original pipeline scripts (not modified by this UI pass)

Original uploaded ZIP is preserved separately. This portable bundle excludes .env, backups, caches and generated verification artifacts.
