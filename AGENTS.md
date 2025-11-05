# Repository Guidelines

## Project Structure & Module Organization
`app/` hosts the CustomTkinter codebase: `main.py` boots the UI, `admin_windows.py` manages modal dialogs, `dashboard_manager.py` renders metrics, `import_export.py` handles Excel sync, and `db.py` wraps SQLite access. Visual resources live under `app/assets/`. Runtime data is segregated: `data/sistema_gym.db` for the live database, `backups/` for dated copies, `logs/` for audit trails. Packaging scripts sit at the root (`run.py` launcher, `crear_exe.py` builder) with PyInstaller artefacts under `build/` and `dist/`.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` syncs dependencies for development or packaging.
- `python -m app.main` runs the app in module mode, ideal while iterating UI changes.
- `python run.py` executes via the same entry point the packaged build uses; run this before releases.
- `python crear_exe.py` invokes PyInstaller and refreshes `dist/SomaEntrenamientos.exe`; clear stale `build/` folders if assets change.

## Coding Style & Naming Conventions
Use 4 spaces per indent and keep functions, variables, and file names in snake_case (`backup_manager.py`, `load_members`). GUI classes, frames, and dialogs follow PascalCase (`ConsultaKioscoFrame`). Place shared constants in `app/config.py` and reuse `config.COLORS` and `config.FONTS` instead of redefining. Prefer `logging` for diagnostics and keep end-user strings in Spanish to match the existing UI.

## Testing Guidelines
Automated tests are not yet in place; perform manual passes covering kiosk lookups, admin CRUD flows, dashboard refresh, and backup creation after database edits. When adding automated coverage, mirror the module layout under a new `tests/` folder, name files `test_<module>.py`, and run with `python -m pytest`. Use temporary SQLite copies to avoid mutating `data/sistema_gym.db`.

## Commit & Pull Request Guidelines
Write concise, imperative commit subjects (`fix kiosk lookup`) and expand with context when touching schema or assets. Pull requests should document user-facing impact, list manual test commands executed, attach screenshots or recordings for UI tweaks, and reference related tickets. Call out migration or cleanup steps (e.g., pruning `backups/`) so reviewers can reproduce.

## Security & Configuration Tips
Treat `data/` and `backups/` as sensitive; exclude them from commits and scrub before sharing archives. Always resolve resource paths through `config.resource_path()` so packaged builds locate assets reliably. Document required environment variables inside `config.py` comments rather than separate files.
