# Mosaic

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/jotasilv4/Mosaic?style=for-the-badge&logo=github&color=FFB686&logoColor=D9E0EE&labelColor=292324)](https://github.com/jotasilv4/Mosaic/stargazers)
[![I3WM](https://img.shields.io/badge/Made%20for-I3WM-pink?style=for-the-badge&logo=linux&logoColor=D9E0EE&labelColor=292324&color=C6A0F6)](https://i3wm.org/)
[![Fabric](https://img.shields.io/badge/Powered%20by-Fabric-blue?style=for-the-badge&logo=python&logoColor=D9E0EE&labelColor=292324&color=89B4FA)](https://github.com/Fabric-Development/fabric)
[![Arch Linux](https://img.shields.io/badge/Target-Arch%20Linux-1793D1?style=for-the-badge&logo=archlinux&logoColor=D9E0EE&labelColor=292324)](https://archlinux.org/)

</div>

Mosaic is a hackable desktop shell for `i3wm`, built with [Fabric](https://github.com/Fabric-Development/fabric). It provides a top bar, an expandable notch, dashboard modules, notifications, media status, theming, and utility panels while keeping the window manager lightweight and script-friendly.

## Features

- Top bar with workspace, system tray, clock, active window, and launcher access.
- Expandable notch with dashboard, launcher, power menu, tools, emoji picker, notifications, and OTP authenticator.
- Wallpaper picker with directory selection, category chips, rounded thumbnails, current wallpaper badge, and `matugen` color generation.
- Dynamic icon theming that refreshes when the wallpaper palette changes.
- Media indicator in the closed notch using `playerctl` and MPRIS metadata.
- Notification center backed by Mosaic's own notification service.
- Network panel with Wi-Fi and wired connection controls through `nmcli`.
- Bluetooth panel using `bluetoothctl`.
- Audio panel using PulseAudio/PipeWire Pulse through `pactl`.
- OTP manager with manual entries, QR scan support, copy action, and deletion.
- Toolbox hooks for screenshots, screen recording, OCR, color picker, and emoji workflows.

## Requirements

Mosaic currently targets Arch Linux with `i3wm` on X11. The installer handles most dependencies, including:

- `i3-wm`, `picom`, `gtk3`, `vte3`, `python-gobject`, `python-cairo`
- `networkmanager`, `bluez`, `bluez-utils`, `libpulse`, `brightnessctl`
- `matugen`, `playerctl`, `libnotify`, `xclip`, `slop`, `maim`, `zbar`
- Python modules such as `fabric`, `Pillow`, `pyotp`, `pyzbar`, `i3ipc`, `watchdog`, `ijson`, and `loguru`

Some components are optional but recommended: `youtube-music-bin`, `hyprpicker`, `gpu-screen-recorder`, and `tesseract`.

## Installation

> [!NOTE]
> Run the installer as your normal user, not as root.

```bash
curl -fsSL https://raw.githubusercontent.com/jotasilv4/Mosaic/dev/install.sh | bash
```

The installer can also update an existing installation. It installs missing dependencies, prepares fonts, generates the Mosaic config, and can optionally enable `NetworkManager`/Bluetooth services and disable `xfce4-notifyd` to avoid notification conflicts.

## Manual Run

After installing, you can start Mosaic directly:

```bash
cd ~/.config/Mosaic
python main.py
```

To restart the shell after config or CSS changes, use the configured i3 restart shortcut or run:

```bash
pkill mosaic
python ~/.config/Mosaic/main.py
```

## Keybindings

Default keybindings are generated in `config/config.json` and can be edited from the config UI.

| Action | Default |
| --- | --- |
| Launcher | `Mod4+d` |
| Toolbox | `Mod4+Shift+t` |
| Restart / reload i3 | `Mod4+Shift+r` |
| Ax message shortcut | `Mod4+Shift+b` |

Some modules are also opened from the notch, dashboard sidebar, or launcher commands such as `:w`, `:d`, and `:p`.

## Configuration

Main user configuration lives in:

```text
~/.config/Mosaic/config/config.json
```

Useful files and folders:

- `main.css` imports all Mosaic styles.
- `styles/` contains per-module styling.
- `config/components/matugen/` contains templates used by `matugen`.
- `~/.current.wall` stores the currently selected wallpaper path.
- `wallpapers_dir` in `config/config.json` controls the wallpaper directory.

## Wallpaper And Theming

The wallpaper panel applies wallpapers through `matugen`:

```bash
matugen -c ~/.config/matugen/config.toml image /path/to/wallpaper
```

When a wallpaper is selected, Mosaic writes the path to `~/.current.wall`, regenerates the color palette, refreshes themed SVG icons, and updates the bar logo.

## Troubleshooting

### Notifications do not appear

Another notification daemon may be taking ownership of D-Bus notifications. If you use XFCE, disable `xfce4-notifyd` during install or kill it manually:

```bash
pkill xfce4-notifyd
```

### Network or Bluetooth panels are empty

Make sure services are enabled:

```bash
sudo systemctl enable --now NetworkManager.service
sudo systemctl enable --now bluetooth.service
```

### OTP QR scanning fails

Install the QR dependencies:

```bash
sudo pacman -S zbar python-pip
python -m pip install --user --break-system-packages pyzbar
```

### Icons do not update after changing wallpaper

Restart Mosaic or trigger the configured i3 reload. Mosaic refreshes themed icons after CSS is reapplied.

## Roadmap

- [x] App launcher
- [x] Power menu
- [x] Wallpaper selector
- [x] Dynamic theming with `matugen`
- [x] System tray
- [x] Dashboard
- [x] Notifications
- [x] OTP authenticator
- [x] Emoji picker
- [x] Network manager
- [x] Bluetooth manager
- [x] Audio controls
- [x] Media indicator
- [x] Color picker integration
- [x] Screenshot / recording / OCR hooks
- [ ] Calendar
- [ ] Clipboard manager
- [ ] Gaming mode
- [ ] Multi-monitor polish
- [ ] Wayland support

## Contributing

Mosaic is intentionally modular. Most UI modules live in `modules/`, styles live in `styles/`, and shared widgets live in `widgets/`.

When adding a feature, prefer the existing Fabric widget patterns, keep styles in a dedicated CSS file, and update `install.sh` if new external commands or Python modules are required.
