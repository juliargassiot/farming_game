# Steam Deck setup

One-time, in Desktop Mode (hold the power button, choose Switch to Desktop). Open Konsole, type this one line, and press Enter:

```
curl -fsSL https://raw.githubusercontent.com/juliargassiot/farming_game/main/deck/install.sh | bash
```

It installs git if the Deck lacks it, downloads the game to `~/games/farm` and Godot 4.7.2 to `~/games/godot`, runs the first asset import, and adds two Non-Steam games. Steam closes for a moment while they are saved and reopens by itself. Running the line again later is safe; it updates everything in place.

Then in Steam, for each of **Farm** and **Farm (stable)**: open the game page → Controller settings → choose the **Gamepad** template, so the Deck presents itself as a standard controller. Optional: set artwork under Properties so they look like real titles in Game Mode.

Return to Game Mode. "Farm" pulls the latest version on every launch; "Check for updates" on the title screen pulls again without leaving the game. "Farm (stable)" runs the last version marked good; it only works once `stable` has been promoted for the first time.

## Laptop

The same line works on a Linux laptop. The launcher assumes the clone lives at `~/games/farm` and Godot at `~/games/godot`; the game can also be started directly with `~/games/farm/deck/play.sh`.
