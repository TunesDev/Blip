# Blip

*Developed by Tunes*

Blip is a little see-through desktop pet for Windows 10/11. It walks along your taskbar, naps, sits on your windows, dances to whatever music you play, reminds you of things, and does silly tricks now and then. It's built to be light on your PC.

## Install

1. Download **BlipSetup-x.y.z.exe** from the [latest release](https://github.com/TunesDev/Blip/releases/latest).
2. Run it. You don't need admin rights. It installs to your user folder and adds Blip to the Start menu.
3. Blip appears on your taskbar. **Right-click Blip** for the menu.

Windows may show "Windows protected your PC" because the installer isn't code-signed yet. Click **More info > Run anyway**.

Blip updates itself: once a day it checks for a new version and asks you before installing it. You can turn this off in **Customise & settings**. Uninstall from Windows **Settings > Apps > Installed apps**, or with **Customise & settings > Uninstall Blip…**.

## What Blip can do

- **Life on your desktop**: walks, naps, blinks, sits on top of your windows, climbs your desktop icons, and can be thrown around with the mouse. It hides during fullscreen games.
- **Music**: puts on headphones and dances (raise the roof, shuffle, floss, dab, robot…) to any player: Spotify, YouTube, VLC and so on. Play/Pause/Next is in the menu, and there's a built-in mini radio.
- **Chat**: reminders ("remind me in 20 min to check the oven"), a to-do list, a focus timer, opening your apps ("I'm going to play some games"), and game stats. Optional AI chat runs on your own PC through [Ollama](https://ollama.com).
- **Fun**: random antics (football, NFL catch with a friend, hide and seek…), levels 1–55 with 10 prestiges, unlockable skins, seasonal outfits, petting, and a happiness meter.
- **Help my PC**: shows what's using your RAM and CPU, frees RAM, cleans temp files and switches power plans. It never closes anything without you ticking it.
- **Do Not Disturb** for when you need quiet.

## Privacy

Everything runs on your PC. Blip's settings, memory, reminders and progress are stored only in `%APPDATA%\Blip`. Blip only uses the internet for:

- the daily update check (GitHub), which you can switch off,
- radio streams, when you play the radio,
- the optional AI brain download (Ollama), only when you click it.

## Build it yourself

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\build_exe.ps1                      # dist\Blip\Blip.exe
.\build_release.ps1 -Version 1.0.1   # installer + .sha256 in release\
```

Pushing a tag like `v1.0.1` makes GitHub Actions build the installer and publish the release automatically.

## Files

| File | What it does |
|---|---|
| `main.py` | starts Blip, the tray icon, the first-run welcome |
| `pet_window.py` | Blip's window and brain: walking, physics, reactions |
| `character.py`, `skins.py` | drawing Blip, hats and skins (all in code) |
| `ui.py` | menu, settings, chat, radio, PC helper windows |
| `antics.py`, `dance.py` | tricks and dance moves |
| `music.py`, `helper.py` | music detection and radio (helper process, only while music plays) |
| `brain.py`, `buddy.py`, `launcher.py` | chat AI, reminders/lists/questions, opening apps |
| `progress.py`, `extras.py` | levels and prestige; DND, focus, happiness, sounds |
| `pchelper.py`, `sensors.py`, `desktop.py` | PC helper, GPU temperature, Windows helpers |
| `updater.py`, `uninstall.py`, `autostart.py` | updates, uninstall, start with Windows |
| `config.py` | default settings and all the numbers you might want to tweak |
