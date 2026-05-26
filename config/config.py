import os
import json
import shutil
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import glib 
from PIL import Image
import toml
from configparser import ConfigParser

from fabric.utils.helpers import get_relative_path
import data

CONFIG_DIR = os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}")
WALLPAPERS_DIR_DEFAULT = os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}/assets/wallpapers_example")

bind_vars = {
    "restart": {
        "command": "Mod4+Shift+r"
    },
    "axmsg": {
        "command": "Mod4+Alt+t"
    },
    "dash": {
        "command": "Mod4+Shift+r"
    },
    "bluetooth": {
        "command": "Mod4+Shift+r"
    },
    "launcher": {
        "command": "Mod4+d"
    },
    "toolbox": {
        "command": "Mod4+Shift+t"
    },
    "emoji": {
        "command": "Mod4+Shift+r"
    },
    "power": {
        "command": "Mod4+Shift+r"
    },
    "css": {
        "command": "Mod4+Shift+r"
    },
    "wallpapers_dir": WALLPAPERS_DIR_DEFAULT,
}

def deep_update(target: dict, update: dict) -> dict:
    """
    Recursively update a nested dictionary with values from another dictionary.
    """
    for key, value in update.items():
        if isinstance(value, dict):
            target[key] = deep_update(target.get(key, {}), value)
        else:
            target[key] = value
    return target

def ensure_matugen_config():
    expected_config = {
        "config": {
            "reload_apps": True,
            "wallpaper": {
                "command": "feh --bg-fill \"{{image}}\"",
                "set": True
            },
            "custom_colors": {
                "red": {
                    "color": "#FF0000",
                    "blend": True
                },
                "green": {
                    "color": "#00FF00",
                    "blend": True
                },
                "yellow": {
                    "color": "#0000FF",
                    "blend": True
                },
                "blue": {
                    "color": "#0000FF",
                    "blend": True
                },
                "magenta": {
                    "color": "#FF00FF",
                    "blend": True
                },
                "cyan": {
                    "color": "#00FFFF",
                    "blend": True
                },
                "white": {
                    "color": "#FFFFFF",
                    "blend": True
                }
            }
        },
        "templates": {
            f"{data.APP_NAME}": {
                "input_path": os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}/config/components/matugen/templates/{data.APP_NAME}.css"),
                'output_path': os.path.expanduser(f'~/.config/{data.APP_NAME_CAP}/styles/colors.css'),
                'post_hook': "echo \"{{image}}\" > ~/.current.wall && fabric-cli exec mosaic 'app.set_css()' &"
            },
            "alacritty": {
                "input_path": os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}/config/components/matugen/templates/alacritty.toml"),
                "output_path": os.path.expanduser("~/.config/alacritty/colors.toml")
            }
        }
    }

    config_path = os.path.expanduser('~/.config/matugen/config.toml')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    existing_config = {}
    if os.path.exists(config_path):
        with open(config_path) as r:
            existing_config = toml.load(r)

        shutil.copyfile(config_path, config_path + ".bkp")

    # Merge configurations
    import shlex
    merged_config = deep_update(existing_config, expected_config)
    
    # Force overwrite wallpaper configuration
    merged_config["config"]["wallpaper"] = {
        "command": "feh --bg-fill \"{{image}}\"",
        "set": True
    }
    
    with open(config_path, 'w') as f:
        toml.dump(merged_config, f)

    current_wall = os.path.expanduser("~/.current.wall")
    if not os.path.exists(current_wall):
        image_path = os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg")
        
        # Save initial wallpaper path
        with open(current_wall, "w") as f:
            f.write(image_path)

        quoted_img = shlex.quote(image_path)
        quoted_config = shlex.quote(config_path)
        os.system(f"matugen -c {quoted_config} image {quoted_img} --source-color-index 0")

def load_bind_vars():
    """
    Load saved key binding variables from JSON, if available.
    """
    config_json = os.path.expanduser(f'~/.config/{data.APP_NAME_CAP}/config/config.json')
    try:
        with open(config_json, 'r') as f:
            saved_vars = json.load(f)
            
            # Fix typo 'assests' and ensure path is for the current user
            if "wallpapers_dir" in saved_vars:
                # Corrigir typo se houver
                saved_vars["wallpapers_dir"] = saved_vars["wallpapers_dir"].replace("assests", "assets")
                
                # Relocar para o home atual se necessário
                if "/home/" in saved_vars["wallpapers_dir"]:
                    user_part = saved_vars["wallpapers_dir"].split("/home/")[1].split("/")[0]
                    current_user = os.getlogin()
                    if user_part != current_user:
                        saved_vars["wallpapers_dir"] = saved_vars["wallpapers_dir"].replace(f"/home/{user_part}", f"/home/{current_user}")
                
                # Se ainda não existir, reverter para o padrão
                if not os.path.exists(saved_vars["wallpapers_dir"]):
                    saved_vars["wallpapers_dir"] = WALLPAPERS_DIR_DEFAULT
                    
            bind_vars.update(saved_vars)
    except FileNotFoundError:
        # Use default values if no saved config exists
        pass

def generate_i3conf() -> str:
    home = os.path.expanduser("~")

    mosaic_config = f"""### MOSAIC CONFIG ###
set $mod Mod4
set $fabricSend fabric-cli exec {data.APP_NAME}

### KEYS MOSAIC ###
#bindsym {bind_vars["restart"]["command"]} exec --no-startup-id killall {data.APP_NAME}; python {home}/.config/{data.APP_NAME_CAP}/main.py & # Reload
#bindsym {bind_vars["axmsg"]["command"]} # Desativado Temporariamente
#bindsym {bind_vars["dash"]["command"]} exec --no-startup-id $fabricSend 'notch.open_notch("dashboard")' # Dashboard | Default: SUPER + SHIFT + R
#bindsym {bind_vars["bluetooth"]["command"]} exec --no-startup-id $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth | Default: SUPER + SHIFT + R
bindsym {bind_vars["launcher"]["command"]} exec --no-startup-id $fabricSend 'notch.open_notch("launcher")' # App Launcher | Default: SUPER + D
bindsym {bind_vars["toolbox"]["command"]} exec --no-startup-id $fabricSend 'notch.open_notch("tools")' # Toolbox | Default: SUPER + SHIFT + T
#bindsym {bind_vars["emoji"]["command"]} exec --no-startup-id $fabricSend 'notch.open_notch("emoji")' # Emoji | Default: SUPER + SHIFT + R
#bindsym {bind_vars["power"]["command"]} exec --no-startup-id $fabricSend 'notch.open_notch("power")' # Power Menu | Default: SUPER + SHIFT + R
#bindsym {bind_vars["css"]["command"]} exec --no-startup-id $fabricSend 'app.set_css()' # Reload CSS | Default: SUPER SHIFT + R

# Wallpapers directory: {bind_vars['wallpapers_dir']}

exec_always --no-startup-id sh -c "feh --bg-fill '$(cat ~/.current.wall)'"
exec_always --no-startup-id ~/.config/Mosaic/config/components/systemboot
"""

    i3_conf_template = get_relative_path("./components/i3/config")
    with open(i3_conf_template, "r") as config:
        replace_config = config.read()
        # Replace the placeholder with the entire mosaic config
        replace_config = replace_config.replace("CONFIG_MOSAIC", mosaic_config)

    i3_config_path = os.path.expanduser("~/.config/i3/config")
    os.makedirs(os.path.dirname(i3_config_path), exist_ok=True)

    if os.path.exists(i3_config_path):
        backup_path = i3_config_path + ".bkp"
        if not os.path.exists(backup_path):
            shutil.copyfile(i3_config_path, backup_path)
            print(f"i3 config backed up to {backup_path}")

    with open(i3_config_path, "w") as config:
        config.write(replace_config)

def ensure_face_icon():
    """
    Ensure the face icon exists. If not, copy the default icon.
    """
    face_icon_path = os.path.expanduser("~/.face.icon")
    default_icon_path = os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}/assets/default.png")
    if not os.path.exists(face_icon_path) and os.path.exists(default_icon_path):
        shutil.copy(default_icon_path, face_icon_path)

def backup_and_replace(src: str, dest: str, config_name: str):
    """
    Backup the existing configuration file and replace it with a new one.
    """
    if os.path.exists(dest):
        backup_path = dest + ".bkp"
        shutil.copy(dest, backup_path)
        print(f"{config_name} config backed up to {backup_path}")
    shutil.copy(src, dest)
    print(f"{config_name} config replaced from {src}")

class I3ConfGUI(Gtk.Window):
    def __init__(self, show_lock_checkbox: bool, show_idle_checkbox: bool):
        super().__init__(title=f"Configure {data.APP_NAME_CAP}")
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_skip_taskbar_hint(True)
    
        self.set_border_width(20)
        self.set_default_size(550, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Adicionando ícone da aplicação se disponível
        try:
            self.set_icon_from_file(os.path.expanduser(f"~/.config/{data.APP_NAME_CAP}/icons/icon.png"))
        except:
            pass

        self.selected_face_icon = None
        self.current_capture_entry = None
        self.capturing_keys = False
        self.current_icon_preview = None

        # Usando HeaderBar para um visual mais moderno
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(f"{data.APP_NAME_CAP} Settings")
        header.set_subtitle("Configure Key Bindings and Appearance")
        self.set_titlebar(header)

        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.add(main_box)

        # Notebook para separar as configurações em abas
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)

        # === Aba de Key Bindings ===
        keybind_grid = Gtk.Grid(column_spacing=15, row_spacing=15)
        keybind_grid.set_margin_top(20)
        keybind_grid.set_margin_bottom(20)
        keybind_grid.set_margin_start(20)
        keybind_grid.set_margin_end(20)
        keybind_scroll = Gtk.ScrolledWindow()
        keybind_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        keybind_scroll.add(keybind_grid)
        
        keybind_label = Gtk.Label(label="Key Bindings")
        notebook.append_page(keybind_scroll, keybind_label)

        # Estilize os cabeçalhos de coluna
        key_header = Gtk.Label(label="Action")
        key_header.set_markup("<b>Action</b>")
        key_header.set_halign(Gtk.Align.START)
        keybind_grid.attach(key_header, 0, 0, 1, 1)
        
        shortcut_header = Gtk.Label()
        shortcut_header.set_markup("<b>Shortcut</b>")
        shortcut_header.set_halign(Gtk.Align.START)
        keybind_grid.attach(shortcut_header, 1, 0, 1, 1)

        # Adicione um botão de ajuda que exibe informações sobre como configurar atalhos
        help_button = Gtk.Button()
        help_icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.BUTTON)
        help_button.set_image(help_icon)
        help_button.set_tooltip_text("Click for help with shortcuts")
        help_button.connect("clicked", self.show_help_dialog)
        keybind_grid.attach(help_button, 2, 0, 1, 1)

        self.entries = []
        bindings = [
            (f"Reload {data.APP_NAME_CAP}", 'restart'),
            ("Message", 'axmsg'),
            ("Dashboard", 'dash'),
            ("Bluetooth", 'bluetooth'),
            ("App Launcher", 'launcher'),
            ("Toolbox", 'toolbox'),
            ("Emoji Picker", 'emoji'),
            ("Power Menu", 'power'),
            ("Reload CSS", 'css'),
        ]

        # Populate grid with key binding rows, starting at row 1
        row = 1
        for label_text, binding_key in bindings:
            # Skip if the binding key doesn't exist in bind_vars
            if binding_key not in bind_vars:
                continue
                
            # Binding description com ícones quando disponíveis
            binding_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            
            # Tente adicionar ícones para ações comuns
            icon_name = self.get_icon_name_for_action(binding_key)
            if icon_name:
                icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
                binding_box.pack_start(icon, False, False, 0)
            
            binding_label = Gtk.Label(label=label_text)
            binding_label.set_halign(Gtk.Align.START)
            binding_box.pack_start(binding_label, True, True, 0)
            keybind_grid.attach(binding_box, 0, row, 1, 1)

            # Styled shortcut entry
            shortcut_entry = Gtk.Entry(editable=False)
            shortcut_entry.set_size_request(200, -1)
            
            # Format current shortcut from bind_vars
            if 'command' in bind_vars[binding_key]:
                current_shortcut = bind_vars[binding_key]['command']
            else:
                # Fallback para o formato antigo (prefix+suffix)
                prefix = bind_vars[binding_key].get('prefix', '')
                suffix = bind_vars[binding_key].get('suffix', '')
                current_shortcut = f"{prefix}+{suffix}"
                
            shortcut_entry.set_text(current_shortcut)
            
            # Melhor estilo visual para os campos de entrada
            context = shortcut_entry.get_style_context()
            context.add_class("keybind-entry")
            
            shortcut_entry.connect("focus-in-event", self.on_entry_focus, binding_key)
            shortcut_entry.connect("focus-out-event", self.on_entry_focus_out, binding_key)
            keybind_grid.attach(shortcut_entry, 1, row, 1, 1)
            
            # Reset button to restore default shortcut
            reset_btn = Gtk.Button()
            reset_icon = Gtk.Image.new_from_icon_name("edit-clear", Gtk.IconSize.BUTTON)
            reset_btn.set_image(reset_icon)
            reset_btn.set_tooltip_text("Reset to default")
            reset_btn.connect("clicked", self.on_reset_shortcut, binding_key, shortcut_entry)
            keybind_grid.attach(reset_btn, 2, row, 1, 1)

            self.entries.append((binding_key, shortcut_entry))
            row += 1

        # === Aba de Appearance ===
        appearance_grid = Gtk.Grid(column_spacing=15, row_spacing=20)
        appearance_grid.set_margin_top(20)
        appearance_grid.set_margin_bottom(20)
        appearance_grid.set_margin_start(20)
        appearance_grid.set_margin_end(20)
        
        appearance_label = Gtk.Label(label="Appearance")
        notebook.append_page(appearance_grid, appearance_label)

        # Wallpapers Directory chooser com preview
        wall_label = Gtk.Label(label="Wallpapers Directory")
        wall_label.set_halign(Gtk.Align.START)
        appearance_grid.attach(wall_label, 0, 0, 1, 1)
        
        wall_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.wall_dir_chooser = Gtk.FileChooserButton(
            title="Select a folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.wall_dir_chooser.set_size_request(300, -1)
        self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
        wall_box.pack_start(self.wall_dir_chooser, True, True, 0)
        
        # Botão para abrir o diretório no gerenciador de arquivos
        open_folder_btn = Gtk.Button()
        folder_icon = Gtk.Image.new_from_icon_name("folder-open", Gtk.IconSize.BUTTON)
        open_folder_btn.set_image(folder_icon)
        open_folder_btn.set_tooltip_text("Open in file manager")
        open_folder_btn.connect("clicked", self.open_wallpaper_folder)
        wall_box.pack_start(open_folder_btn, False, False, 0)
        
        appearance_grid.attach(wall_box, 1, 0, 2, 1)

        # Profile Icon selection com preview
        face_label = Gtk.Label(label="Profile Icon")
        face_label.set_halign(Gtk.Align.START)
        appearance_grid.attach(face_label, 0, 1, 1, 1)
        
        face_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Preview do ícone atual
        self.face_preview = Gtk.Image()
        self.face_preview.set_size_request(48, 48)
        self.update_face_preview()
        face_box.pack_start(self.face_preview, False, False, 0)
        
        face_btn = Gtk.Button(label="Select Image")
        face_btn.connect("clicked", self.on_select_face_icon)
        face_box.pack_start(face_btn, True, True, 0)
        
        appearance_grid.attach(face_box, 1, 1, 2, 1)

        # Row for optional checkboxes
        checkboxes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        checkboxes_box.set_margin_top(20)
        
        if show_lock_checkbox:
            self.lock_checkbox = Gtk.CheckButton(label="Replace Hyprlock config")
            self.lock_checkbox.set_active(False)
            checkboxes_box.pack_start(self.lock_checkbox, False, False, 0)
        
        if show_idle_checkbox:
            self.idle_checkbox = Gtk.CheckButton(label="Replace Hypridle config")
            self.idle_checkbox.set_active(False)
            checkboxes_box.pack_start(self.idle_checkbox, False, False, 0)
        
        appearance_grid.attach(checkboxes_box, 0, 2, 3, 1)

        # Footer with action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        main_box.pack_start(button_box, False, False, 0)

        # Row for Cancel and Accept buttons, styled
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self.on_cancel)
        
        accept_btn = Gtk.Button(label="Save Changes")
        accept_btn.get_style_context().add_class("suggested-action")
        accept_btn.connect("clicked", self.on_accept)
        
        button_box.pack_start(cancel_btn, False, False, 0)
        button_box.pack_start(accept_btn, False, False, 0)
        
        # Setup key press event
        self.connect("key-press-event", self.on_key_press)
        self.connect("key-release-event", self.on_key_release)
        self.connect("destroy", self.on_destroy)
        
        # Track pressed keys
        self.pressed_keys = set()
        self.pressed_key = None
        self.modifier_map = {
            Gdk.ModifierType.CONTROL_MASK: "Mod1",  # Ctrl key (modificado para Mod1)
            Gdk.ModifierType.SHIFT_MASK: "Shift",
            Gdk.ModifierType.MOD1_MASK: "Alt",      # Alt key
            Gdk.ModifierType.MOD4_MASK: "Mod4",     # Super/Windows key (modificado para Mod4)
        }
        
        # Current binding being configured
        self.current_binding_key = None
        
        # CSS para estilizar a interface
        self.apply_css()
        
        # Exibir a janela
        self.show_all()

    def get_icon_name_for_action(self, binding_key):
        """Retorna um nome de ícone apropriado para a ação"""
        icon_map = {
            'restart': 'view-refresh',
            'axmsg': 'mail-message',
            'dash': 'dashboard',
            'bluetooth': 'bluetooth',
            'launcher': 'applications-system',
            'toolbox': 'tools',
            'emoji': 'face-smile',
            'power': 'system-shutdown',
            'css': 'text-css'
        }
        return icon_map.get(binding_key, None)

    def apply_css(self):
        """Aplica estilos CSS personalizados à interface"""
        css_provider = Gtk.CssProvider()
        css = """
        .keybind-entry {
            font-family: monospace;
            font-weight: bold;
        }
        entry:focus {
            border-color: #3584e4;
        }
        """
        css_provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def update_face_preview(self):
        """Atualiza o preview do ícone de perfil atual"""
        face_path = os.path.expanduser("~/.face.icon")
        if os.path.exists(face_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(face_path, 48, 48, True)
                self.face_preview.set_from_pixbuf(pixbuf)
            except:
                self.face_preview.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
        else:
            self.face_preview.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)

    def show_help_dialog(self, widget):
        """Exibe um diálogo de ajuda sobre atalhos de teclado"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="How to Configure Shortcuts"
        )
        dialog.format_secondary_text(
            "1. Click on any shortcut field\n"
            "2. Press the key combination you want to use\n"
            "3. The new shortcut will be set automatically\n\n"
            "To reset a shortcut to default, click the clear button next to it."
        )
        dialog.run()
        dialog.destroy()

    def open_wallpaper_folder(self, widget):
        """Abre o diretório de wallpapers no gerenciador de arquivos"""
        folder_path = self.wall_dir_chooser.get_filename()
        if folder_path:
            try:
                subprocess.Popen(['xdg-open', folder_path])
            except Exception as e:
                print(f"Error opening folder: {e}")

    def on_reset_shortcut(self, button, binding_key, entry):
        """Reseta um atalho para seu valor padrão"""
        default_shortcuts = {
            'restart': bind_vars["restart"]["command"],
            'axmsg': bind_vars["axmsg"]["command"],
            'dash': bind_vars["dash"]["command"],
            'bluetooth': bind_vars["bluetooth"]["command"],
            'launcher': bind_vars["launcher"]["command"],
            'toolbox': bind_vars["toolbox"]["command"],
            'emoji': bind_vars["emoji"]["command"],
            'power': bind_vars["power"]["command"],
            'css': bind_vars["css"]["command"],
        }
        
        if binding_key in default_shortcuts:
            default = default_shortcuts[binding_key]
            # Atualizar para o novo formato de configuração
            bind_vars[binding_key] = {"command": default}
            entry.set_text(default)

    def on_entry_focus(self, entry, event, binding_key):
        """Called when an entry gets focus."""
        self.current_capture_entry = entry
        self.current_binding_key = binding_key
        self.capturing_keys = True
        self.pressed_keys.clear()
        self.pressed_key = None
        entry.set_text("Press keys...")
        entry.get_style_context().add_class("capturing")
        return False
        
    def on_entry_focus_out(self, entry, event, binding_key):
        """Called when an entry loses focus."""
        if self.capturing_keys:
            # If no keys were pressed, restore original shortcut
            if not self.pressed_keys and not self.pressed_key:
                if 'command' in bind_vars[binding_key]:
                    current_shortcut = bind_vars[binding_key]['command']
                else:
                    # Fallback para formato antigo
                    current_shortcut = f"{bind_vars[binding_key].get('prefix', '')}+{bind_vars[binding_key].get('suffix', '')}"
                entry.set_text(current_shortcut)
            
            self.capturing_keys = False
            self.current_capture_entry = None
            self.current_binding_key = None
            entry.get_style_context().remove_class("capturing")
        return False
        
    def on_key_press(self, widget, event):
        """Handle key press events for capturing shortcuts."""
        if not self.capturing_keys or not self.current_capture_entry:
            return False
            
        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)
        state = event.state
        
        # Detect modifier keys
        for mod_mask, mod_name in self.modifier_map.items():
            if state & mod_mask:
                self.pressed_keys.add(mod_name)
                
        # Add the current key if it's not a modifier
        if keyname not in ["Control_L", "Control_R", "Shift_L", "Shift_R", 
                         "Alt_L", "Alt_R", "Super_L", "Super_R"]:
            # Convert keyname to appropriate format
            if keyname:
                keyname = keyname.lower()  # Mudamos para minúsculas conforme padrão do hyprland
                self.pressed_key = keyname
                
                # Update the display immediately
                prefix = "+".join(sorted(self.pressed_keys))
                if prefix:
                    self.current_capture_entry.set_text(f"{prefix}+{keyname}")
                else:
                    self.current_capture_entry.set_text(keyname)
        
        return True
        
    def on_key_release(self, widget, event):
        """Handle key release events to finalize the shortcut."""
        if self.capturing_keys and self.current_capture_entry and self.current_binding_key:
            # Only finalize if we have both modifiers and a key
            if self.pressed_keys and self.pressed_key:
                prefix = "+".join(sorted(self.pressed_keys))
                
                # Update bind_vars para o novo formato
                if prefix:
                    command = f"{prefix}+{self.pressed_key}"
                else:
                    command = self.pressed_key
                    
                bind_vars[self.current_binding_key] = {"command": command}
                
                # Set the final text in the entry
                self.current_capture_entry.set_text(command)
                
                # Clear capture state
                self.capturing_keys = False
                self.current_capture_entry = None
                self.current_binding_key = None
                self.pressed_keys.clear()
                self.pressed_key = None
                
                # Remove visual indicator
                for entry_key, entry in self.entries:
                    entry.get_style_context().remove_class("capturing")
            
        return False

    def on_select_face_icon(self, widget):
        """
        Open a file chooser dialog for selecting a new face icon image.
        """
        dialog = Gtk.FileChooserDialog(
            title="Select Face Icon",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )

        # Filter to allow image files only
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image files")
        image_filter.add_mime_type("image/png")
        image_filter.add_mime_type("image/jpeg")
        image_filter.add_pattern("*.png")
        image_filter.add_pattern("*.jpg")
        image_filter.add_pattern("*.jpeg")
        dialog.add_filter(image_filter)

        # Adicionar preview de imagem
        preview = Gtk.Image()
        dialog.set_preview_widget(preview)
        dialog.connect("update-preview", self.update_preview_cb, preview)

        if dialog.run() == Gtk.ResponseType.OK:
            self.selected_face_icon = dialog.get_filename()
            # Update preview
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.selected_face_icon, 48, 48, True)
                self.face_preview.set_from_pixbuf(pixbuf)
            except:
                pass
        dialog.destroy()

    def update_preview_cb(self, file_chooser, preview):
        """Update the preview widget"""
        filename = file_chooser.get_preview_filename()
        try:
            if filename:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, 128, 128, True)
                preview.set_from_pixbuf(pixbuf)
                preview.show()
                file_chooser.set_preview_widget_active(True)
            else:
                file_chooser.set_preview_widget_active(False)
        except:
            file_chooser.set_preview_widget_active(False)

    def on_accept(self, widget):
        """
        Save the configuration and update the necessary files.
        """
        # Update wallpaper directory
        bind_vars['wallpapers_dir'] = self.wall_dir_chooser.get_filename()

        # Garantir que todos os atalhos estejam no formato correto
        for binding_key in [
            'restart', 'axmsg', 'dash', 'bluetooth', 
            'launcher', 'toolbox', 'emoji', 'power', 'css'
        ]:
            # Verificar se a chave existe
            if binding_key in bind_vars:
                # Se não estiver no formato de comando, converter
                if not isinstance(bind_vars[binding_key], dict) or 'command' not in bind_vars[binding_key]:
                    old_prefix = bind_vars[binding_key].get('prefix', 'Mod4+Shift')
                    old_suffix = bind_vars[binding_key].get('suffix', 'r')
                    bind_vars[binding_key] = {"command": f"{old_prefix}+{old_suffix}"}

        # Save the updated bind_vars to a JSON file
        config_json = os.path.expanduser(f'~/.config/{data.APP_NAME_CAP}/config/config.json')
        os.makedirs(os.path.dirname(config_json), exist_ok=True)
        
        try:
            # Salvar no formato JSON correto
            with open(config_json, 'w') as f:
                json.dump(bind_vars, f, indent=4)

            # Process face icon if one was selected
            if self.selected_face_icon:
                try:
                    img = Image.open(self.selected_face_icon)
                    side = min(img.size)
                    left = (img.width - side) / 2
                    top = (img.height - side) / 2
                    cropped_img = img.crop((left, top, left + side, top + side))
                    
                    # Salva em formato PNG com tamanho consistente
                    target_size = (256, 256)
                    cropped_img = cropped_img.resize(target_size, Image.LANCZOS)
                    cropped_img.save(os.path.expanduser("~/.face.icon"), format='PNG')
                except Exception as e:
                    print("Error processing face icon:", e)

            # Chamar a função para configuração
            start_config()
            
            # Fechar a janela principal
            self.destroy()
            
        except Exception as e:
            # Em caso de erro, mostrar mensagem simples
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Saving Settings"
            )
            dialog.format_secondary_text(f"An error occurred: {str(e)}")
            dialog.run()
            dialog.destroy()

    def on_cancel(self, widget):
        """Fecha a janela sem confirmação adicional"""
        self.destroy()
            
    def on_destroy(self, widget):
        """Cleanup ao fechar a janela"""
        # Se precisar fazer alguma limpeza antes de fechar
        pass

def start_config():
    """
    R
    """
    ensure_matugen_config()
    ensure_face_icon()

    generate_i3conf()

    os.system("i3-msg reload")
    os.system(f"pkill {data.APP_NAME}; python ~/.config/{data.APP_NAME_CAP}/main.py &")

def open_config():
    """
    Entry point for opening the configuration GUI.
    """
    load_bind_vars()

 
    show_lock_checkbox = False
    show_idle_checkbox = False
    

    # Create and run the GUI
    window = I3ConfGUI(show_lock_checkbox, show_idle_checkbox)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        load_bind_vars()
        start_config()
    else:
        open_config()
