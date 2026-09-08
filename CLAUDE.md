# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RoboCutter is a Windows desktop app (Python + PySide6) for cutting-plan
(zaagplan) optimization for furniture makers. All code, comments, docs,
and identifiers are in **Dutch** — match that when editing. The design
is fully specified in `design/chapters/*.md` (source of truth for
product decisions, summarized in `design/checklist.md`), and
`OVERDRACHT.md` at the repo root is the running build log / handoff
doc — **read it before starting new work**, it records what's built,
what's deliberately deferred, open questions for the product owner
(Sven), and lessons learned (including documented Qt pitfalls).

## Commands

```bash
# Install
pip install -e ".[dev]"   # pytest, pillow
pip install -e ".[ui]"    # PySide6, needed for anything under src/robocutter/ui or scripts/*_ui.py

# Tests (pythonpath=["src"] is set in pyproject.toml, no extra setup needed)
# Use `python -m pytest`, not a bare `pytest` — the latter isn't guaranteed
# to be on PATH in every shell this repo gets developed from.
python -m pytest                          # full suite
python -m pytest tests/test_modellen.py   # one file
python -m pytest tests/test_modellen.py::test_directe_cirkelverwijzing_wordt_geblokkeerd  # one test
python -m pytest -q                       # quiet

# Run the real app
python -m robocutter.ui.app

# Rough/unstyled PySide6 test-UIs, one per backend module, used to exercise
# a module before its real screen exists (see Architecture below)
python scripts/test_materialen_ui.py
python scripts/test_reststukken_ui.py
python scripts/test_modellen_ui.py
python scripts/test_projecten_ui.py
python scripts/test_instellingen_ui.py

# Visual sanity-check output for the optimizer (writes output/*.png)
python scripts/demo_render.py

# Build a demo .exe + Windows installer (PyInstaller + Inno Setup — see
# OVERDRACHT.md for why this is PyInstaller, not the intended Nuitka, pre-release)
pip install -e ".[build]"
.\scripts\build_exe.ps1          # -> dist\RoboCutter.exe
.\installer\build_installer.ps1  # -> installer\Output\RoboCutter-Setup.exe (needs Inno Setup 6)
```

There is no lint/format/build tooling configured in this repo — don't invent one.

## Architecture

### Backend modules follow one repeated pattern

`src/robocutter/{materialen,reststukken,modellen,projecten}/` each contain:
- `models.py` — plain `@dataclass` records + `str`-subclassed `Enum`s. Deliberately independent from `robocutter.optimalisatie.models` (the lean engine-facing shapes) — the bibliotheek records carry metadata the optimizer doesn't need, and vice versa; conversion happens explicitly where needed.
- `bibliotheek.py` — a `*Bibliotheek` class: in-memory dict keyed by id, loaded from/persisted to SQLite via its `opslag.py` on every mutation. A module-level `valideer(record, ...) -> list[str]` returns Dutch error strings (never exceptions/pop-ups for validation — that's a deliberate UX principle carried into the backend). Status-transition guards (archive, delete) raise a module-local `OngeldigeStatusOvergangError`-style exception instead.
- `opslag.py` — thin `sqlite3` wrapper: `open_verbinding`, `laad_alles`, `opslaan`, `verwijderen`. All four share one physical file (`data/robocutter.db`, path resolved via `robocutter.instellingen.beheer.InstellingenBeheer().effectieve_db_pad()` — never hardcode this path), each in its own table.

Cross-module dependencies are constructor-injected (e.g. `ReststukkenBibliotheek`/`ModellenBibliotheek`/`ProjectenBibliotheek` all take a `MaterialenBibliotheek` instance to validate `materiaal_id` references) rather than each module opening its own connection — in the UI, `main_window.py` wires one shared `MaterialenBibliotheek` into every page that needs it.

`src/robocutter/instellingen/` is the exception: a single `Instellingen` record (no CRUD/list) persisted as JSON at `%APPDATA%\RoboCutter\instellingen.json`, not in `data/robocutter.db` — deliberately, since the setting that says *where the database lives* can't itself live inside that database. `InstellingenBeheer` also owns `wijzig_opslaglocatie()`, which moves an existing db file when the location changes. **When testing this module, always pass an explicit `standaard_data_map` (and `bestand_pad`) pointing inside `tmp_path`** — a prior test that omitted this accidentally moved the real dev `data/robocutter.db` into a pytest tmp dir.

`src/robocutter/optimalisatie/` is the cutting-plan engine itself (`engine.py`, two placement strategies — `"efficient"`/`"rijen"`), kept intentionally decoupled from every bibliotheek module.

`src/robocutter/projecten/` additionally has two engine-facing modules beyond the usual `models.py`/`bibliotheek.py`/`opslag.py`: `zaaglijst.py` flattens a project's models/parts into one sortable cut list (`bouw_zaaglijst`/`sorteer_zaaglijst`), and `zaagplannen.py` groups that list by `materiaal_id` and calls `optimalisatie.engine.genereer_zaagplannen` per group, converting to/from the engine's lean `Materiaal`/`Onderdeel` shapes. Generated zaagplannen are **not persisted** — no revision history yet (deliberately deferred, see `OVERDRACHT.md`); a plan is recomputed in memory every time the UI asks for it.

### UI (`src/robocutter/ui/`)

- `app.py` boots `QApplication` → `MainWindow`.
- `main_window.py`: dark "chrome" header (always dark in both themes) with the four main nav items, a VS Code-style tab strip (`_open_tabs`, closable except the pinned "Projecten" tab), and per-tab page widgets. Page instances (`MaterialenPage`, `ReststukkenPage`, `ModellenPage`, `ProjectenPage`, `InstellingenPage`) are constructed once and kept alive across theme/tab rebuilds (`_rebuild_content` reparents them before deleting the old central widget) — losing them would drop open SQLite connections and in-progress form state. Opening a project spawns its own closable `ProjectDetailPage`, cached in `_project_pages: dict[str, ProjectDetailPage]` keyed by project id so re-opening the same project reuses the existing tab.
- Each `*_page.py` follows the same internal shape: a sidebar (status/type/tag filters), a main area (search + sortable `QTableWidget`), and a slide-in "drawer" panel (add/edit form, no modal pop-ups). Shared helpers (`_field_spin`, `_segmented`, `_rand_chip_rij`, `_clear_layout`) are duplicated per-file rather than factored into a shared module — that's the established convention here, not an oversight.
- `theme.py` builds one big Qt stylesheet string from a `Theme` dataclass (`LICHT`/`DONKER`); `icons.py` renders hand-drawn SVG icon strings (Phosphor Bold style) to `QPixmap`/`QIcon` at runtime — there's no icon font/resource file.
- `sample_data.py`'s `ProjectStatus` is just a re-export of the real `robocutter.projecten.models.ProjectStatus` (kept for backward compat with earlier placeholder-data code, now that `ProjectenPage`/`ProjectDetailPage` are wired to the real SQLite-backed bibliotheek).
- `widgets/` holds small reusable pieces shared between pages: `project_card.py`, `stat_tile.py` (KPI tiles), `zaagplaat_widget.py` (renders one physical sheet's cut layout).
- `zaagplan_pdf.py` exports a generated zaagplan to PDF by drawing directly with `QPainter` (rectangles/lines/text) against its own print-specific white palette, in millimeters converted to device pixels via `_dpmm`. **Never** build a print export by calling `QWidget.render()` on the on-screen (dark-themable) widgets — an earlier version did that and shipped a dark background onto an otherwise-white PDF; Sven rejected it explicitly ("ik wil echt dat hij de pdfs eigenlijk van de grond opbouwt").

**Known Qt/PySide6 pitfalls already worked around in this codebase** (don't reintroduce them):
- A `str`-subclassed `Enum` stored via `QWidget.setProperty` / `QComboBox` userData silently comes back as a plain `str`. Store `.value` and reconstruct via the enum constructor on read.
- A bare `QPushButton` used only as a layout container collapses its `sizeHint()` — use a plain `QWidget` subclass with a custom `clicked` signal instead.
- A custom `QWidget` subclass won't paint a stylesheet `background:` unless `WA_StyledBackground` is set.
- `QScrollArea`'s internal viewport needs an explicit `background: transparent` rule (by objectName) or it can show the OS theme instead of the app's theme.
- Once a widget has *any* stylesheet, `QDoubleSpinBox`/`QSpinBox`'s native up/down arrows render as solid blocks, not triangles — build custom step buttons instead (see `_field_spin`/`_field_spin_int` in the page files).
- A `QComboBox` with no styling of its own can render fully invisible if an ancestor's background was forced transparent — give every input its own explicit style.
- When mixing a `Stretch` column with `Interactive` ones in a `QTableWidget`, the stretch column gets squeezed unreadably thin instead of triggering scroll — make all columns `Interactive` and recompute the flexible one's width yourself on resize (deferred via `QTimer.singleShot(0, ...)`, since the viewport width during the resize event itself is often stale).

### UI workflow convention

New screens get an HTML mockup (published as a Claude Artifact) approved by the user *before* the PySide6 implementation — this has been overridden only when the user explicitly says a screen is close enough to an existing one to skip it. Backend-first is the default sequencing for a new module (models/bibliotheek/opslag + tests + a rough, unstyled `scripts/test_*_ui.py`) before any mockup or real screen work begins.

### Tests

`tests/` covers only the backend (`models.py`/`bibliotheek.py`/`opslag.py`/`zaaglijst.py`) per module — the `ui/*_page.py` classes have no pytest coverage; they're verified manually (running the real app or a `scripts/test_*_ui.py`) or via one-off smoke scripts. SQLite persistence tests follow a consistent pattern: write with one connection, open a second connection on the same file to simulate an app restart, assert the reload matches.
