import os
import re
from pathlib import Path
from fabric.widgets.image import Image
from gi.repository import GdkPixbuf
import config.data as data

# Parameters
font_family: str = 'tabler-icons'
font_weight: str = '650'

span: str = f"<span font-family='{font_family}' font-weight='{font_weight}'>"

ROOT_DIR = Path(__file__).resolve().parent.parent
LUCIDE_DIR = ROOT_DIR / "assets" / "lucide"
COLORS_FILE = ROOT_DIR / "styles" / "colors.css"
LUCIDE_CACHE_DIR = Path(data.CACHE_DIR) / "icons" / "lucide"
_THEMED_IMAGES = []

LUCIDE_ICONS = {
    "widgets": "layout-dashboard",
    "wallpapers": "image",
    "apps": "apple",
    "qrcode": "qr-code",
    "authcode": "shield-check",
    "colorpicker": "pipette",
    "media": "music",
    "emoji": "smile",
    "ssfull": "camera",
    "ssregion": "scan",
    "screenrecord": "video",
    "ocr": "scan-text",
    "stop": "square",
    "reload": "refresh-cw",
    "add": "plus",
    "trash": "trash-2",
    "trash_bold": "trash-2",
    "chevron_left": "chevron-left",
    "chevron_right": "chevron-right",
    "lock": "lock",
    "suspend": "moon",
    "logout": "log-out",
    "reboot": "rotate-ccw",
    "shutdown": "power",
    "wifi_3": "wifi",
    "wifi_off": "wifi-off",
    "world": "globe",
    "world_off": "cloud-off",
    "bluetooth": "bluetooth",
    "bluetooth_connected": "bluetooth-connected",
    "bluetooth_disconnected": "bluetooth-off",
    "notifications_off": "bell-off",
    "notifications_clear": "list-x",
    "vol_high": "volume-2",
    "mic": "mic",
    "accept": "check",
    "cancel": "x",
    "config": "settings",
    "brightness_high": "sun",
    "palette": "palette",
    "circle": "circle",
}

def read_css_color(variable: str = "--primary", fallback: str = "#8bd0f0") -> str:
    try:
        with open(COLORS_FILE, "r") as file:
            match = re.search(rf"{re.escape(variable)}\s*:\s*(#[0-9a-fA-F]{{6}})", file.read())
            return match.group(1) if match else fallback
    except OSError:
        return fallback

def icon_path(name: str, color: str | None = None) -> str:
    lucide_name = LUCIDE_ICONS.get(name, name)
    source = LUCIDE_DIR / f"{lucide_name}.svg"
    color = color or read_css_color()
    color_slug = color.lstrip("#").lower()
    target = LUCIDE_CACHE_DIR / f"{lucide_name}-{color_slug}.svg"

    LUCIDE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with open(source, "r") as file:
        svg = file.read()

    svg = svg.replace('stroke="currentColor"', f'stroke="{color}"')
    svg = svg.replace("stroke='currentColor'", f"stroke='{color}'")

    with open(target, "w") as file:
        file.write(svg)

    return str(target)

def image(name: str, size: int = 20, widget_name: str | None = None, color: str | None = None, **kwargs) -> Image:
    widget = Image(
        name=widget_name,
        image_file=icon_path(name, color),
        size=size,
        **kwargs,
    )
    register_themed_image(widget, name, color, size)
    return widget

def set_image(widget, name: str, color: str | None = None) -> None:
    widget.set_from_file(icon_path(name, color))
    try:
        size = widget.get_pixel_size()
    except Exception:
        size = 20
    register_themed_image(widget, name, color, size if size > 0 else 20)

def register_themed_image(widget, name: str, color: str | None = None, size: int = 20) -> None:
    for icon_data in _THEMED_IMAGES:
        if icon_data["widget"] is widget:
            icon_data.update({"name": name, "color": color, "size": size})
            return
    _THEMED_IMAGES.append({"widget": widget, "name": name, "color": color, "size": size})

def refresh_themed_images() -> None:
    for icon_data in list(_THEMED_IMAGES):
        widget = icon_data["widget"]
        try:
            path = icon_path(icon_data["name"], icon_data["color"])
            size = icon_data.get("size", 20)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
            widget.set_from_pixbuf(pixbuf)
            widget.set_pixel_size(size)
        except Exception:
            try:
                widget.set_from_file(icon_path(icon_data["name"], icon_data["color"]))
            except Exception:
                pass

# Dashboard
widgets: str = "&#x10006;"
wallpapers: str = "&#xef56;"
controls: str = "&#xec38;"

#Panels
apps: str = "&#xfd74;"
dashboard: str = "&#xea87;"
chat: str = "&#xf59f;"

# Utility
dot: str = "&#xf698;"
trash_bold: str = "&#xf783;"
qrcode: str = "&#xeb11;"
authcode: str = "&#xfc7b;"
lock_rotate: str = "&#xefe6;"

# Bar
colorpicker: str = "&#xebe6;"
media: str = "&#xf00d;"
emoji: str = "&#xf2ec;"

#Toolbox
toolbox: str = "&#xebca;"       # toolbox
ssfull: str = "&#xeaea;"    # camera
ssregion: str = "&#xf201;"    # camera
screenrecord: str = "&#xeafa;"  # video
ocr: str = "&#xfcc3;"          # text-recognition
close : str = "&#xeb55;"

# Circles
temp: str = "&#xeb38;"
disk: str = "&#xea88;"
battery: str = "&#xea38;"
memory: str = "&#xfa97;"
cpu: str = "&#xef8e;"

# AIchat
reload: str = "&#xf3ae;"
detach: str = "&#xea99;"

# Wallpapers
add: str = "&#xeb0b;"
sort: str = "&#xeb5a;"
circle: str = "&#xf671;"

# Chevrons
chevron_up: str = "&#xea62;"
chevron_down: str = "&#xea5f;"
chevron_left: str = "&#xea60;"
chevron_right: str = "&#xea61;"

# Power
lock: str = "&#xeae2;"
suspend: str = "&#xece7;"
logout: str = "&#xeba8;"
reboot: str = "&#xeb13;"
shutdown: str = "&#xeb0d;"

# Power Manager
power_saving: str = "&#xed4f;"
power_balanced: str = "&#xfa77;"
power_performance: str = "&#xec45;"
charging: str = "&#xefef;"
discharging: str = "&#xefe9;"
alert: str = "&#xefb4;"

# Applets
wifi_0: str = "&#xeba3;"
wifi_1: str = "&#xeba4;"
wifi_2: str = "&#xeba5;"
wifi_3: str = "&#xeb52;"
world: str = "&#xeb54;"
world_off: str = "&#xf1ca;"
bluetooth: str = "&#xea37;"
night: str = "&#xeaf8;"
coffee: str = "&#xef0e;"
notifications: str = "&#xea35;"

wifi_off: str = "&#xecfa;"
bluetooth_off: str = "&#xeceb;"
night_off: str = "&#xf162;"
notifications_off: str = "&#xece9;"

notifications_clear: str = "&#xf814;";

# Bluetooth
bluetooth_connected: str = "&#xecea;"
bluetooth_disconnected: str = "&#xf081;"

# Player
pause: str = "&#xf690;"
play: str = "&#xf691;"
stop: str = "&#xf695;"
skip_back: str = "&#xf693;"
skip_forward: str = "&#xf694;"
prev: str = "&#xf697;"
next: str = "&#xf696;"
shuffle: str = "&#xf000;"
repeat: str = "&#xeb72;"
music: str = "&#xeafc;"
rewind_backward_5: str = "&#xfabf;"
rewind_forward_5: str = "&#xfac7;"

# Volume
vol_off: str = "&#xf1c3;"
vol_mute: str = "&#xeb50;"
vol_medium: str = "&#xeb4f;"
vol_high: str = "&#xeb51;"

mic: str = "&#xeaf0;"
mic_mute: str = "&#xed16;"

# Overview
circle_plus: str = "&#xea69;"

# Pins
copy_plus: str = "&#xfdae;"
paperclip: str = "&#xeb02;"

# Confirm
accept: str = "&#xea5e;"
cancel: str = "&#xeb55;"
trash: str = "&#xeb41;"

# Config
config: str = "&#xeb20;"

# Icons
firefox: str = "&#xecfd;"
chromium: str = "&#xec18;"
spotify: str = "&#xfe86;"
disc: str = "&#x1003e;"
disc_off: str = "&#xf118;"

# Brightness
brightness_low: str = "&#xeb7d;"
brightness_medium: str = "&#xeb7e;"
brightness_high: str = "&#xeb30;"

# Misc
dot: str = "&#xf698;"
palette: str = "&#xeb01;"
cloud_off: str = "&#xed3e;"
loader: str = "&#xeca3;"
radar: str = "&#xf017;"
emoji: str = "&#xeaf7;"

exceptions: list[str] = [
    'font_family',
    'font_weight',
    'span',
]

def apply_span() -> None:
    global_dict = globals()
    for key, value in list(global_dict.items()):
        if isinstance(value, str) and key not in exceptions and not key.startswith('__'):
            global_dict[key] = f"{span}{value}</span>"

apply_span()