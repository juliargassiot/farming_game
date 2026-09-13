# Steam Deck setup

One-time, in Desktop Mode (hold the power button, choose Switch to Desktop). Open Konsole for the commands.

## 1. Git

Run `git --version`. If it prints a version, skip to step 2. Otherwise install Homebrew, which survives SteamOS updates, then git:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
brew install git
```

## 2. Read-only access token

Skip this step if the repository is public. While it is private the Deck needs a token. On GitHub (logged in as the repository owner): Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token. Name it "Steam Deck", set the longest expiration offered, choose "Only select repositories" → `farming_game`, and under Repository permissions set Contents to Read-only. Copy the token.

## 3. Clone

```
git config --global credential.helper store
mkdir -p ~/games && cd ~/games
git clone https://github.com/juliargassiot/farming_game.git farm
```

When asked, the username is `juliargassiot` and the password is the token. It is remembered after the first time.

## 4. Godot and first import

```
~/games/farm/deck/setup.sh
```

This downloads Godot 4.7.2 to `~/games/godot` and runs the first asset import. Test it before involving Steam:

```
~/games/farm/deck/play.sh
```

The game should open full screen; Quit on the title screen returns to the desktop.

## 5. Steam shortcuts

In Steam (Desktop Mode): Games → Add a Non-Steam Game to My Library → Browse. Set the file type filter to All Files, pick `/home/deck/games/farm/deck/play.sh`, and add it. Then right-click it → Properties:

- Rename it to **Farm**.
- Add it a second time the same way, rename that one **Farm (stable)**, and put `stable` in Launch Options.
- Optional: set artwork under Properties so it looks like a real title in Game Mode.

In each shortcut's Controller settings choose the **Gamepad** template so the Deck presents itself as a standard controller.

Return to Game Mode. "Farm" pulls the latest version on every launch; "Check for updates" on the title screen pulls again without leaving the game. "Farm (stable)" runs the last version marked good; it only works once `stable` has been promoted for the first time.

## Laptop

The same steps work on a Linux laptop. The launcher assumes the clone lives at `~/games/farm` and Godot at `~/games/godot`.
