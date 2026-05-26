import os
import json
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib

from fabric.utils.helpers import get_relative_path

APP_NAME = "mosaic"
APP_NAME_CAP = "Mosaic"

CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{APP_NAME}"

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

try:
    screen = Gdk.Screen.get_default()
    if screen:
        CURRENT_WIDTH = screen.get_width()
        CURRENT_HEIGHT = screen.get_height()
    else:
        # Fallback to some default if screen is not available
        CURRENT_WIDTH = 1920
        CURRENT_HEIGHT = 1080
except Exception:
    CURRENT_WIDTH = 1920
    CURRENT_HEIGHT = 1080

default_wallpapers_dir = get_relative_path("../assets/wallpapers_example")
CONFIG_FILE = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    # Pega o caminho do config, corrige o typo 'assests' se houver
    WALLPAPERS_DIR = config.get('wallpapers_dir', default_wallpapers_dir).replace("assests", "assets")
    
    # Se o caminho salvo estiver fora do home atual (ex: de outro usuário), tenta relocalizar
    if "/home/" in WALLPAPERS_DIR:
        parts = WALLPAPERS_DIR.split("/")
        # Tenta reconstruir o caminho relativo ao HOME_DIR atual
        # Ex: /home/moretti/.config/Mosaic/assets/... -> ~/.config/Mosaic/assets/...
        try:
            mosaic_idx = parts.index(APP_NAME_CAP)
            # Reconstroi a partir do ponto comum .config/Mosaic
            sub_path = "/".join(parts[mosaic_idx-1:])
            new_path = os.path.join(HOME_DIR, sub_path)
            if os.path.exists(new_path):
                WALLPAPERS_DIR = new_path
        except (ValueError, IndexError):
            pass

    # Valida se o diretório existe, senão usa o padrão
    if not os.path.exists(WALLPAPERS_DIR):
        WALLPAPERS_DIR = default_wallpapers_dir
else:
    WALLPAPERS_DIR = default_wallpapers_dir