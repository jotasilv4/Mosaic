import os, json, hashlib, shutil, shlex
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.entry import Entry
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import GdkPixbuf, Gtk, GLib, Gio, Gdk
from PIL import Image, ImageDraw
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from functools import partial
import config.data as data
import modules.icons as icons

class WallpaperSelector(Box):
    CACHE_DIR = os.path.join(data.CACHE_DIR, "thumbs")
    CATEGORY_KEYWORDS = [
        "Ambxst",
        "Catppuccin",
        "Gruvbox",
        "Minecraft",
        "Monochrome",
    ]

    def __init__(self, **kwargs):
        old_cache_dir = os.path.join(data.CACHE_DIR, "/wallpapers")
        if os.path.exists(old_cache_dir):
            shutil.rmtree(old_cache_dir)

        super().__init__(
            name="wallpapers",
            orientation="v",
            h_expand=True,
            v_expand=True,
            spacing=10,
            **kwargs
        )
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        self.button_data = {}

        self.files = self._list_wallpapers()
        self.thumbnails = []
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.thumb_lock = Lock()
        self.selected_index = -1
        self.file_monitor = None
        self._thumb_generation = 0
        
        self.active_category = "Images"

        self.wallpaper_box = Gtk.FlowBox()
        self.wallpaper_box.set_name("wallpapers-box")
        self.wallpaper_box.set_column_spacing(10)
        self.wallpaper_box.set_row_spacing(10)
        self.wallpaper_box.set_homogeneous(False)
        self.wallpaper_box.set_min_children_per_line(1)
        self.wallpaper_box.set_max_children_per_line(6)
        self.wallpaper_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.wallpaper_box.set_halign(Gtk.Align.START)
        self.wallpaper_box.set_valign(Gtk.Align.START)

        self.scrolled_window = ScrolledWindow(
            name="scrolled-window-walls",
            orientation="v",
            spacing=10,
            min_content_size=(720, 300),
            max_content_size=(720, 300),
            child=self.wallpaper_box
        )
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_propagate_natural_height(False)

        self.search_entry = Entry(
            name="search-entry-walls",
            placeholder="Search Wallpapers...",
            h_expand=True,
            h_align="fill",
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text())
        )
        
        # Conectar eventos de teclado para navegação
        self.search_entry.connect("key-press-event", self.on_search_entry_key_press)

        # Dropdown de esquemas
        self.schemes = {
            "scheme-tonal-spot": "Tonal Spot",
            "scheme-content": "Content",
            "scheme-expressive": "Expressive",
            "scheme-fidelity": "Fidelity",
            "scheme-fruit-salad": "Fruit Salad",
            "scheme-monochrome": "Monochrome",
            "scheme-neutral": "Neutral",
            "scheme-rainbow": "Rainbow",
        }
        self.scheme_dropdown = Gtk.ComboBoxText()
        self.scheme_dropdown.set_name("scheme-dropdown")
        for key, display_name in self.schemes.items():
            self.scheme_dropdown.append(key, display_name)
        self.scheme_dropdown.set_active_id("scheme-tonal-spot")
        self.scheme_dropdown.set_tooltip_text("Esquema de cores")

        self.directory_button = Button(
            name="wallpaper-dir-button",
            tooltip_text=data.WALLPAPERS_DIR,
            on_clicked=lambda *_: self.choose_wallpaper_directory(),
            child=Box(
                orientation="h",
                spacing=6,
                children=[
                    icons.image("wallpapers", size=18, widget_name="wallpaper-dir-icon"),
                    Label(name="wallpaper-dir-label", label="Pasta"),
                ],
            ),
        )
        self.directory_button.connect("enter-notify-event", self.on_button_enter)
        self.directory_button.connect("leave-notify-event", self.on_button_leave)

        self.category_box = Box(
            name="wallpaper-category-box",
            orientation="h",
            spacing=6,
            h_align="start",
        )
        self.category_buttons = {}
        self.rebuild_category_buttons()

        self.header_box = CenterBox(
            name="header",
            orientation="h",
            spacing=20,
            h_align="fill",
            h_expand=True,
            start_children=[self.search_entry],
            end_children=[
                Box(
                    orientation="h",
                    spacing=8,
                    children=[
                        self.directory_button,
                        self.scheme_dropdown,
                    ],
                )
            ]
        )

        # Adicionar o CSS para estilizar a seleção
        self._setup_css()

        self.add(self.header_box)
        self.add(self.category_box)
        self.add(self.scrolled_window)

        self._start_thumbnail_thread()
        self.setup_file_monitor()
        self.show_all()
        self.search_entry.grab_focus()

    def _list_wallpapers(self):
        if not os.path.isdir(data.WALLPAPERS_DIR):
            return []
        wallpapers = []
        for root, _dirs, files in os.walk(data.WALLPAPERS_DIR):
            for file_name in files:
                if self._is_image(file_name):
                    full_path = os.path.join(root, file_name)
                    wallpapers.append(os.path.relpath(full_path, data.WALLPAPERS_DIR))
        return sorted(wallpapers, key=str.lower)

    def rebuild_category_buttons(self):
        for child in self.category_box.get_children():
            self.category_box.remove(child)

        categories = self._available_categories()
        if self.active_category not in categories:
            self.active_category = "Images"
        self.category_buttons = {}
        for category in categories:
            button = Button(
                name="wallpaper-category-button",
                child=Label(name="wallpaper-category-label", label=category),
                on_clicked=lambda *_args, cat=category: self.set_category(cat),
            )
            if category == self.active_category:
                button.add_style_class("active")
            self.category_buttons[category] = button
            self.category_box.add(button)
        self.category_box.show_all()

    def _available_categories(self):
        categories = ["Images"]
        if any(file_name.lower().endswith(".gif") for file_name in self.files):
            categories.append("GIF")

        lower_files = [file_name.lower() for file_name in self.files]
        for category in self.CATEGORY_KEYWORDS:
            if any(category.lower() in file_name for file_name in lower_files):
                categories.append(category)

        for file_name in self.files:
            parts = file_name.split(os.sep)
            if len(parts) > 1:
                label = parts[0].replace("-", " ").replace("_", " ").title()
                if label not in categories:
                    categories.append(label)

        return categories

    def set_category(self, category):
        self.active_category = category
        for cat, button in self.category_buttons.items():
            if cat == category:
                button.add_style_class("active")
            else:
                button.remove_style_class("active")
        self.arrange_viewport(self.search_entry.get_text())

    def _setup_css(self):
        """Configura o CSS para estilizar o botão selecionado"""
        return

    def setup_file_monitor(self):
        if self.file_monitor is not None:
            self.file_monitor.cancel()
        gfile = Gio.File.new_for_path(data.WALLPAPERS_DIR)
        self.file_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self.on_directory_changed)

    def choose_wallpaper_directory(self):
        dialog = Gtk.FileChooserDialog(
            title="Selecionar pasta de wallpapers",
            parent=self.get_toplevel() if isinstance(self.get_toplevel(), Gtk.Window) else None,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "Cancelar",
            Gtk.ResponseType.CANCEL,
            "Selecionar",
            Gtk.ResponseType.ACCEPT,
        )
        dialog.set_filename(data.WALLPAPERS_DIR)

        response = dialog.run()
        selected_dir = dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        dialog.destroy()

        if selected_dir and os.path.isdir(selected_dir):
            self.set_wallpaper_directory(selected_dir)

    def set_wallpaper_directory(self, directory):
        directory = os.path.abspath(directory)
        data.WALLPAPERS_DIR = directory
        self.directory_button.set_tooltip_text(directory)
        self._save_wallpaper_directory(directory)
        self.reload_wallpapers()

    def _save_wallpaper_directory(self, directory):
        config = {}
        if os.path.exists(data.CONFIG_FILE):
            try:
                with open(data.CONFIG_FILE, "r") as file:
                    config = json.load(file)
            except (json.JSONDecodeError, OSError):
                config = {}

        config["wallpapers_dir"] = directory
        os.makedirs(os.path.dirname(data.CONFIG_FILE), exist_ok=True)
        with open(data.CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)

    def reload_wallpapers(self):
        self._thumb_generation += 1
        self.files = self._list_wallpapers()
        self.thumbnails = []
        self.button_data.clear()
        self.selected_index = -1
        for child in self.wallpaper_box.get_children():
            self.wallpaper_box.remove(child)
        self.search_entry.set_text("")
        self.rebuild_category_buttons()
        self.setup_file_monitor()
        self._start_thumbnail_thread()
        self.wallpaper_box.show_all()

    def on_directory_changed(self, monitor, file, other_file, event_type):
        file_name = file.get_basename()
        if event_type == Gio.FileMonitorEvent.DELETED:
            if file_name in self.files:
                self.files.remove(file_name)
                cache_path = self._get_cache_path(file_name)
                if os.path.exists(cache_path):
                    try: os.remove(cache_path)
                    except Exception as e: print(f"Erro ao deletar cache {cache_path}: {e}")
                self.thumbnails = [(p, n) for p, n in self.thumbnails if n != file_name]
                GLib.idle_add(self.arrange_viewport, self.search_entry.get_text())
        elif event_type == Gio.FileMonitorEvent.CREATED:
            if self._is_image(file_name):
                new_name = file_name.lower().replace(" ", "-")
                full_path = os.path.abspath(os.path.join(data.WALLPAPERS_DIR, file_name))
                new_full_path = os.path.join(data.WALLPAPERS_DIR, new_name)
                if new_name != file_name and not os.path.exists(new_full_path):
                    try: os.rename(full_path, new_full_path)
                    except Exception as e: print(f"Erro ao renomear arquivo {full_path}: {e}")
                if new_name not in self.files:
                    self.files.append(new_name)
                    self.files.sort()
                    self.executor.submit(self._process_file, new_name, self._thumb_generation)
        elif event_type == Gio.FileMonitorEvent.CHANGED:
            if self._is_image(file_name) and file_name in self.files:
                cache_path = self._get_cache_path(file_name)
                if os.path.exists(cache_path):
                    try: os.remove(cache_path)
                    except Exception as e: print(f"Erro ao deletar cache {file_name}: {e}")
                self.executor.submit(self._process_file, file_name, self._thumb_generation)
        GLib.idle_add(self.wallpaper_box.queue_draw)

    def arrange_viewport(self, query: str = ""):
        # Limpar widget e dicionário de dados
        for child in self.wallpaper_box.get_children():
            self.wallpaper_box.remove(child)
        self.button_data.clear()
        
        filtered = [
            (t, n)
            for t, n in self.thumbnails
            if query.casefold() in n.casefold()
            and self._matches_category(n, self.active_category)
        ]
        filtered.sort(key=lambda x: x[1].lower())
        
        for i, (pixbuf, name) in enumerate(filtered):
            button = self._create_wallpaper_button(name, pixbuf)
            
            # Usar ID único para o botão
            button_id = f"button-{i}"
            self.button_data[button_id] = {
                "file_name": name,
                "index": i
            }
            
            button.connect("clicked", lambda btn, bid=button_id: 
                self.on_wallpaper_selected_by_id(bid))
            
            self._add_wallpaper_button(button)
        
        self.wallpaper_box.show_all()
        
        if query.strip() == "":
            self.selected_index = -1
        elif len(filtered) > 0:
            self.update_selection(0)

    def on_wallpaper_selected_by_id(self, button_id):
        if button_id in self.button_data:
            file_name = self.button_data[button_id]["file_name"]
            index = self.button_data[button_id]["index"]
            
            # Atualizar a seleção visual
            self.update_selection(index)
            
            # Aplicar o wallpaper e as cores via matugen
            full_path = os.path.abspath(os.path.join(data.WALLPAPERS_DIR, file_name))
            selected_scheme = self.scheme_dropdown.get_active_id()
            
            # Save the current wallpaper path to ~/.current.wall
            try:
                with open(os.path.expanduser("~/.current.wall"), "w") as f:
                    f.write(full_path)
            except Exception as e:
                print(f"Error saving wallpaper path: {e}")

            quoted_path = shlex.quote(full_path)
            exec_shell_command_async(f"matugen -c {os.path.expanduser('~/.config/matugen/config.toml')} image {quoted_path} -t {selected_scheme} --source-color-index 0")
            self.arrange_viewport(self.search_entry.get_text())

    def on_wallpaper_selected(self, file_name):
        full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
        selected_scheme = self.scheme_dropdown.get_active_id()
        
        # Save the current wallpaper path to ~/.current.wall
        try:
            with open(os.path.expanduser("~/.current.wall"), "w") as f:
                f.write(full_path)
        except Exception as e:
            print(f"Error saving wallpaper path: {e}")

        quoted_path = shlex.quote(full_path)
        exec_shell_command_async(f"matugen -c {os.path.expanduser('~/.config/matugen/config.toml')} image {quoted_path} -t {selected_scheme} --source-color-index 0")
        self.arrange_viewport(self.search_entry.get_text())

    def _matches_category(self, file_name, category):
        if category == "Images":
            return True
        if category == "GIF":
            return file_name.lower().endswith(".gif")
        parts = file_name.split(os.sep)
        if len(parts) > 1 and parts[0].replace("-", " ").replace("_", " ").title() == category:
            return True
        return category.lower() in file_name.lower()

    def on_search_entry_key_press(self, widget, event):
        if event.keyval in (Gdk.KEY_Right, Gdk.KEY_Left):
            self.move_selection(event.keyval)
            return True
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.selected_index != -1:
                children = self.wallpaper_box.get_children()
                if 0 <= self.selected_index < len(children):
                    # Encontrar o ID do botão pelo índice
                    button_id = next((bid for bid, data in self.button_data.items() 
                        if data["index"] == self.selected_index), None)
                    if button_id:
                        self.on_wallpaper_selected_by_id(button_id)
            return True
        return False

    def move_selection(self, keyval):
        children = self.wallpaper_box.get_children()
        total = len(children)
        if total == 0: return

        current = self.selected_index if self.selected_index != -1 else 0

        if keyval == Gdk.KEY_Right: 
            new = current + 1
        elif keyval == Gdk.KEY_Left: 
            new = current - 1
        else: 
            return

        new = max(0, min(new, total - 1))
        self.update_selection(new)
    
    def update_selection(self, new_index: int):
        children = self.wallpaper_box.get_children()
        if not children or new_index < 0 or new_index >= len(children):
            return
            
        # Remover estilo de seleção anterior
        if 0 <= self.selected_index < len(children):
            old_button = self._flowbox_button(children[self.selected_index])
            context = old_button.get_style_context()
            if context.has_class("selected"):
                context.remove_class("selected")
                
        # Aplicar estilo de seleção ao novo botão
        new_button = self._flowbox_button(children[new_index])
        context = new_button.get_style_context()
        if not context.has_class("selected"):
            context.add_class("selected")
            
        # Rolar para tornar visível se necessário
        adjustment = self.scrolled_window.get_vadjustment()
        if adjustment:
            allocation = children[new_index].get_allocation()
            button_start = allocation.y
            button_end = button_start + allocation.height
            
            visible_start = adjustment.get_value()
            visible_end = visible_start + adjustment.get_page_size()
            
            if button_start < visible_start:
                adjustment.set_value(button_start)
            elif button_end > visible_end:
                adjustment.set_value(button_end - adjustment.get_page_size())
                
        self.selected_index = new_index

    @staticmethod
    def _flowbox_button(child):
        return child.get_child() if isinstance(child, Gtk.FlowBoxChild) else child

    def _add_wallpaper_button(self, button):
        flow_child = Gtk.FlowBoxChild()
        flow_child.set_halign(Gtk.Align.START)
        flow_child.set_valign(Gtk.Align.START)
        flow_child.set_hexpand(False)
        flow_child.set_vexpand(False)
        flow_child.set_size_request(112, 112)
        flow_child.add(button)
        self.wallpaper_box.add(flow_child)

    def _start_thumbnail_thread(self):
        GLib.Thread.new("thumbnail-loader", self._preload_thumbnails, self._thumb_generation)

    def _preload_thumbnails(self, generation):
        futures = [self.executor.submit(self._process_file, f, generation) for f in self.files]
        concurrent.futures.wait(futures)

    def _process_file(self, file_name, generation):
        if generation != self._thumb_generation:
            return
        try:
            full_path = os.path.abspath(os.path.join(data.WALLPAPERS_DIR, file_name))
            cache_path = self._get_cache_path(file_name)
            
            if not os.path.exists(cache_path):
                with Image.open(full_path) as img:
                    target_size = 94
                    img = img.convert("RGB")
                    scale = max(target_size / img.width, target_size / img.height)
                    resized_size = (int(img.width * scale), int(img.height * scale))
                    resized_img = img.resize(resized_size, Image.Resampling.LANCZOS)
                    left = (resized_img.width - target_size) // 2
                    top = (resized_img.height - target_size) // 2
                    new_img = resized_img.crop((left, top, left + target_size, top + target_size)).convert("RGBA")
                    mask = Image.new("L", (target_size, target_size), 0)
                    ImageDraw.Draw(mask).rounded_rectangle(
                        (0, 0, target_size - 1, target_size - 1),
                        radius=14,
                        fill=255,
                    )
                    new_img.putalpha(mask)
                    new_img.save(cache_path, "PNG")
            
            with self.thumb_lock:
                GLib.idle_add(partial(self._add_thumbnail, cache_path, file_name, generation))
        except Exception as e:
            print(f"Erro ao processar {file_name}: {e}")
            GLib.idle_add(partial(self._handle_processing_error, file_name, generation))

    def _add_thumbnail(self, cache_path, file_name, generation):
        if generation != self._thumb_generation:
            return False
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path)
            self.thumbnails.append((pixbuf, file_name))
            
            self.arrange_viewport(self.search_entry.get_text())
                
        except Exception as e:
            print(f"Erro ao carregar thumbnail {cache_path}: {e}")
        return False

    def _create_wallpaper_button(self, file_name, pixbuf):
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.set_name("wallpaper-card-image")
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.START)
        image.set_hexpand(False)
        image.set_vexpand(False)

        image_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        image_box.set_name("wallpaper-card-image-box")
        image_box.set_size_request(94, 94)
        image_box.set_halign(Gtk.Align.CENTER)
        image_box.set_valign(Gtk.Align.CENTER)
        image_box.set_hexpand(False)
        image_box.set_vexpand(False)
        image_box.pack_start(image, False, False, 0)

        current_badge = Gtk.Label(label="CURRENT")
        current_badge.set_name("wallpaper-current-badge")
        current_badge.set_halign(Gtk.Align.CENTER)
        current_badge.set_valign(Gtk.Align.END)
        current_badge.set_no_show_all(True)

        image_overlay = Gtk.Overlay()
        image_overlay.set_name("wallpaper-card-overlay")
        image_overlay.set_size_request(94, 94)
        image_overlay.set_halign(Gtk.Align.CENTER)
        image_overlay.set_valign(Gtk.Align.CENTER)
        image_overlay.set_hexpand(False)
        image_overlay.set_vexpand(False)
        image_overlay.add(image_box)
        image_overlay.add_overlay(current_badge)

        is_current = self._is_current_wallpaper(file_name)
        if is_current:
            current_badge.show()
        else:
            current_badge.hide()

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        content.set_size_request(94, 94)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)
        content.set_hexpand(False)
        content.set_vexpand(False)
        content.pack_start(image_overlay, False, False, 0)

        button = Gtk.Button()
        button.set_name(f"wallpaper-{file_name}")
        button.set_tooltip_text(file_name)
        button.set_size_request(110, 110)
        button.set_halign(Gtk.Align.START)
        button.set_valign(Gtk.Align.START)
        button.set_hexpand(False)
        button.set_vexpand(False)
        button.get_style_context().add_class("wallpaper-card")
        if is_current:
            button.get_style_context().add_class("current")
        button.add(content)
        return button

    def _is_current_wallpaper(self, file_name):
        try:
            with open(os.path.expanduser("~/.current.wall"), "r") as file:
                current_wallpaper = os.path.realpath(os.path.expanduser(file.read().strip()))
        except OSError:
            return False
        full_path = os.path.realpath(os.path.join(data.WALLPAPERS_DIR, file_name))
        return current_wallpaper == full_path

    def _handle_processing_error(self, file_name, generation):
        if generation != self._thumb_generation:
            return False
        if file_name in self.files:
            self.files.remove(file_name)
            self.thumbnails = [(p, n) for p, n in self.thumbnails if n != file_name]
            GLib.idle_add(self.arrange_viewport, self.search_entry.get_text())
        return False

    def _get_cache_path(self, file_name: str) -> str:
        full_path = os.path.abspath(os.path.join(data.WALLPAPERS_DIR, file_name))
        file_hash = hashlib.md5(full_path.encode("utf-8")).hexdigest()
        return os.path.join(self.CACHE_DIR, f"{file_hash}-grid-rounded.png")

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    @staticmethod
    def _is_image(file_name: str) -> bool:
        return file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))
