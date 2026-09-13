# Steam Deck setup

One-time, in Desktop Mode (hold the power button, choose Switch to Desktop). Open Konsole, type this one line, and press Enter:

```
curl -fsSL https://raw.githubusercontent.com/juliargassiot/farming_game/main/deck/install.sh | bash
```

It installs git if the Deck lacks it, downloads the game to `~/games/farm` and Godot 4.7.2 to `~/games/godot`, runs the first asset import, and adds two Non-Steam games with library artwork. Steam closes for a moment while they are saved and reopens by itself; if the desktop then asks which screen to share, cancel it. Running the line again later is safe; it updates everything in place.

Return to Game Mode. Steam's default controller layout for the shortcuts is a Gamepad one, which is what the game expects. Artwork lives in `deck/art/` (drawn by `tools/art/steam_art.py`) and the launcher refreshes Steam's copy on every start. "Farm" pulls the latest version on every launch; "Check for updates" on the title screen pulls again without leaving the game. "Farm (stable)" runs the last version marked good; it only works once `stable` has been promoted for the first time.

## Laptop

The same line works on a Linux laptop. The launcher assumes the clone lives at `~/games/farm` and Godot at `~/games/godot`; the game can also be started directly with `~/games/farm/deck/play.sh`.

## Buttons do nothing

The bottom of the title screen names the controller the game sees. If it says "No controller detected", Steam is not passing the Deck through as a gamepad: in Game Mode open the game page → Controller settings, confirm Steam Input is enabled for the game and the **Gamepad** template is selected, then relaunch. As a fallback, choose the **Keyboard (WASD) and Mouse** template; the game also accepts arrows or WASD, Enter, Space, E, and Escape. Steam + R1 takes a screenshot to share for diagnosis.
