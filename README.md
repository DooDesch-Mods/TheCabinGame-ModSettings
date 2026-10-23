# CabinModSettings

> 🛟 **Need help or found a bug?** Get support at [support.doodesch.de/modsettings](https://support.doodesch.de/modsettings).

Adds a fourth main-menu card named **Mods**. Flip it to choose **Settings** or **Info**.

Settings opens a separate window with a selector for each supported installed mod and **Apply**, **Cancel** and **Defaults**. Each mod keeps its own preferences. Info opens a separate window with installed mods, their actual versions and HTTPS support links where supplied. Missing version or support information is shown as unavailable.

Requires [UE4SS 3.0.1 or later](https://www.nexusmods.com/thecabingame/mods/4). Install UE4SS separately.

1. Close the game and install UE4SS in your game folder.
2. Copy `Mods/CabinModSettings` into `the_cabin_game/Binaries/Win64/ue4ss/Mods`.
3. Copy the archive's `the_cabin_game/Content/Paks/~mods` files to the same path in your game folder. Keep the three container files together.

CabinModSettings is optional. Each function mod uses its defaults and its own validated settings file without the Mods menu. GraphicsProfiles supplies profile templates without the Mods menu and never applies a profile on startup.

Host settings are marked in the menu and take effect next round. Other settings are local.

Close the game before removal. Remove only this mod's folder and its named container files, if included. Back up `Scripts/settings.dat` first to keep preferences. GraphicsProfiles does not restore graphics automatically on removal; use Restore previous before removal if required.

## Build and release

Tested baseline: Steam build `25553694`, Unreal 5.5 and UE4SS `v3.0.1-1164-g5e627997`.

Use Python 3.13. Run `python -m pip install -r requirements-dev.txt`, `python -m unittest discover -s tests -v`, `python tests/check_lua.py`, then `python tools/package.py`.

The builder writes a deterministic ZIP and checksum in `dist`. Overlay containers are committed build inputs; CI packages them and does not cook Unreal assets or download the game. Runtime Lua and containers are covered by the acceptance fingerprint. `python tools/package.py --release` rejects a missing or stale product acceptance.

CI checks Linux and Windows. See [publishing](docs/publishing.md) for the GitHub/Nexus flow and [Nexus description](docs/nexus.md) for the prepared listing.

## Registry API

Registry version 1: require `cabin_registry` and call `new(ModRef, log)` in the registering mod's Lua VM. Include `cabin_codec` beside it. Call `register(definition, adapter)` with a stable lowercase `id`, `name` and `fields`. Each field has `key`, `label`, `type` and a default except actions. Supported types are `boolean`, `number`, `choice` and `action`; choices contain `{value, label}` options. Numbers can declare `min`, `max`, `positive` and `integer`. Mark round-dependent fields with `host=true`.

The adapter's `read()` returns values and an integer revision. Its `apply(values, action)` validates, saves and returns confirmed values and the new revision, or raises an error with its cause. `cabin_store` provides the same validated persistence used by the supported mods. Poll the registry on the game thread. Registration and the panel communicate through serialized ModRef shared variables because UE4SS mods have separate Lua VMs. Local Lua functions remain with their owning mod. Hot reload is outside the tested scope.

To supply Info metadata, add an optional `Mods/<mod-name>/mod-info.ini` with both `version=<actual package version>` and `support=<https URL>`, one per line. Use the package's real version and a direct HTTPS support URL. Mods without this file remain listed with unavailable metadata.

Rejoin integration requires its matching layout/host-settings adapter and authority copies. The 0.1.3 fixes have local menu and host/client integration evidence; a complete group round remains unmeasured. Do not overwrite an active Rejoin runtime.
