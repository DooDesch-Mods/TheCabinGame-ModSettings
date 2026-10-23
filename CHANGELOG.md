# Changelog

## 0.1.3 - 2026-10-23

### Fixed

- Search for optional panel functions only while the settings panel is open.
- Reuse the active menu reference and limit absent-menu discovery to once per second.

## 0.1.2 - 2026-10-13

### Fixed

- Convert declared integer sliders to Lua integers before validation and saving.
- Refresh unchanged settings when selecting a provider after another provider changes them.
- Keep the final native action caption visible at the bottom of a scrolled settings panel.

## 0.1.1 - 2026-10-13

### Fixed

- Hide and restore the Mods card together with the original main-menu cards.

## 0.1.0 - 2026-10-13

- Adds a Mods card to the main menu with separate Settings and Info windows.
- Settings uses native buttons and sliders with Apply, Cancel and Defaults. Each supported mod keeps its own preferences.
- Info shows installed mods, actual versions and HTTPS support links where supplied.
