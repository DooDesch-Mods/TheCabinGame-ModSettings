# CabinModSettings

> 🛟 **Need help or found a bug?** Get support at [support.doodesch.de/modsettings](https://support.doodesch.de/modsettings).

Adds a **Mods** card to the main menu. Flip it to open **Settings** or **Info**.

Settings opens a separate window with a selector for each supported installed mod and **Apply**, **Cancel** and **Defaults**. Each mod keeps its own preferences. Info opens a separate window with installed mods, their actual versions and HTTPS support links where supplied. Missing information is shown as unavailable.

**Private test candidate. Game acceptance is pending. No public release yet.**

## Install

1. Close the game and install [UE4SS for the cabin game](https://www.nexusmods.com/thecabingame/mods/4).
2. Copy `Mods/CabinModSettings` from the ZIP into `the_cabin_game/Binaries/Win64/ue4ss/Mods`.
3. Copy the ZIP's `the_cabin_game/Content/Paks/~mods` files into the matching game folder. Keep the `.pak`, `.utoc` and `.ucas` files together.

CabinModSettings is optional for the individual mods. FastTurns and ShortEvents settings take effect next round and are controlled by the host. FastTurns requires its Lua and overlay on every participating client. Other settings are local. Multiplayer acceptance is pending.

## Remove

Close the game and remove this mod's folder and its named files from `Content/Paks/~mods`. Back up `Scripts/settings.dat` first to keep your preferences.

By DooDesch.
