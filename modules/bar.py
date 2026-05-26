import os
import re
from fabric.widgets.box import Box
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.x11 import X11Window as Window
from gi.repository import GLib, Gdk, GdkPixbuf
from modules.systemtray import SystemTray
import modules.icons as icons
from utils.i3 import Workspaces
import config.data as data

def read_css_color(variable, fallback):
    colors_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "styles", "colors.css"))
    try:
        with open(colors_path, "r") as file:
            match = re.search(rf"{re.escape(variable)}\s*:\s*(#[0-9a-fA-F]{{6}})", file.read())
            return match.group(1) if match else fallback
    except OSError:
        return fallback

def build_themed_svg(source_path, color):
    cache_dir = os.path.join(data.CACHE_DIR, "icons")
    os.makedirs(cache_dir, exist_ok=True)
    target_path = os.path.join(cache_dir, "bar-logo.svg")

    with open(source_path, "r") as file:
        svg = file.read()

    svg = re.sub(r'fill="white"', f'fill="{color}"', svg)
    svg = re.sub(r"fill='white'", f"fill='{color}'", svg)

    with open(target_path, "w") as file:
        file.write(svg)

    return target_path

class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            geometry="top",
            type_hint="dock",
            margin="-4px -4px -8px -4px",
            visible=True,
            all_visible=True
        )

        self.notch = kwargs.get("notch", None)

        self.workspaces = Workspaces()
        self.systray = SystemTray()
        self.date_time = DateTime(name="date-time", formatters=["%H:%M"], h_align="center", v_align="center")
        self.logo_source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "bar-logo.svg"))
        self.logo_path = build_themed_svg(self.logo_source_path, read_css_color("--primary", "#8bd0f0"))

        # Launcher Button
        self.button_apps = Button(
            name="button-bar",
            style_classes="logo",
            on_clicked=lambda *_: self.search_apps(),
            child=Image(
                name="button-bar-logo",
                image_file=self.logo_path,
                size=16,
            )
        )
        self.button_apps_logo = self.button_apps.get_child()
        self.button_apps.connect("enter_notify_event", self.on_button_enter)
        self.button_apps.connect("leave_notify_event", self.on_button_leave)
        
        # Power Button
        self.button_power = Button(
            name="button-bar",
            on_clicked=lambda *_: self.power_menu(),
            child=icons.image("shutdown", widget_name="button-bar-label", size=20)
        )
        self.button_power.connect("enter_notify_event", self.on_button_enter)
        self.button_power.connect("leave_notify_event", self.on_button_leave)

        # Config Bar
        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation="h",
            h_align="fill",
            v_align="center",
            start_children=Box(
                name="start-container",
                spacing=4,
                orientation="h",
                children=[
                    self.button_apps,
                    self.workspaces
                ]
            ),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h",
                children=[
                    self.systray,
                    self.date_time,
                    self.button_power,
                ],
            ),
        )

        self.children = self.bar_inner
        self.hidden = False

        self.systray._update_visibility()

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def search_apps(self):
        self.notch.open_notch("launcher")
    
    def power_menu(self):
        self.notch.open_notch("power")

    def refresh_theme(self):
        self.logo_path = build_themed_svg(self.logo_source_path, read_css_color("--primary", "#8bd0f0"))
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.logo_path, 16, 16, True)
            self.button_apps_logo.set_from_pixbuf(pixbuf)
            self.button_apps_logo.set_pixel_size(16)
        except Exception:
            self.button_apps_logo.set_from_file(self.logo_path)

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.bar_inner.add_style_class("hidden")
        else:
            self.bar_inner.remove_style_class("hidden")