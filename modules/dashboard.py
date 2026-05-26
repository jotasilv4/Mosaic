import random
import os
from fabric.utils import get_relative_path, exec_shell_command_async, idle_add
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.stack import Stack
from fabric.widgets.image import Image
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from modules.wallpapers import WallpaperSelector
import modules.icons as icons
import subprocess
import threading
import re
import gi
from gi.repository import Gdk, Gtk, GdkPixbuf, GLib

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

class Dashboard(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dashboard",
            orientation="v",
            spacing=8,
            h_align="fill",
            v_align="fill",
            h_expand=True,
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs["notch"]

        self.wallpapers = WallpaperSelector()

        self.button_widgets = Button(
            name="btn-dashboard",
            h_align="center",
            v_align="center",
            tooltip_text="Nook",
            on_clicked=lambda *_: self.go_to_child(0),
            child=Box(
                name="btn-box-dashboard",
                orientation="h",
                h_align="fill",
                h_expand=True,
                spacing=5,
                children=[
                    icons.image("widgets", size=20),
                    Label(label="Nook", style_classes="text")
                ]
            )
        )
        self.button_widgets.connect("enter_notify_event", self.on_button_enter)
        self.button_widgets.connect("leave_notify_event", self.on_button_leave)

        self.button_wallpapers = Button(
            name="btn-dashboard",
            h_align="center",
            v_align="center",
            tooltip_text="Wallpapers",
            on_clicked=lambda *_: self.go_to_child(1),
            child=Box(
                name="btn-box-dashboard",
                orientation="h",
                h_align="fill",
                h_expand=True,
                spacing=5,
                children=[
                    icons.image("wallpapers", size=20),
                    Label(label="Wallpapers", style_classes="text")
                ]
            )
        )
        self.button_wallpapers.connect("enter_notify_event", self.on_button_enter)
        self.button_wallpapers.connect("leave_notify_event", self.on_button_leave)

        self.button_config = Button(
            name="btn-dashboard",
            h_align="center",
            v_align="center",
            tooltip_text="Configuration",
            on_clicked=lambda *_: self.go_to_child(2),
            child=icons.image("config", size=20)
        )
        self.button_config.connect("enter_notify_event", self.on_button_enter)
        self.button_config.connect("leave_notify_event", self.on_button_leave)

        self.sidebar_button_widgets = self._create_sidebar_button("widgets", "Nook", 0)
        self.sidebar_button_wallpapers = self._create_sidebar_button("wallpapers", "Wallpapers", 1)
        self.sidebar_button_config = self._create_sidebar_button("config", "Configuration", 2)
        self.sidebar_buttons = [
            self.sidebar_button_widgets,
            self.sidebar_button_wallpapers,
            self.sidebar_button_config,
        ]
        self.sidebar_button_widgets.add_style_class("active")

        self.header = CenterBox(
            name="header-dashboard",
            orientation="h",
            visible=True,
            h_align="fill",
            h_expand=True,
            spacing=10,
            start_children=[
                self.button_widgets,
                self.button_wallpapers
            ],
            end_children=self.button_config
        )

        self.teste1 = Box(
            name="teste1",
            orientation="h",
            h_align="fill",
            h_expand=True,
            v_align="fill",
            v_expand=True
        )

        # 1. Brilho Material You (Tamanho Completo)
        self.brightness_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.brightness_slider.set_name("brightness-slider")
        self.brightness_slider.set_draw_value(False)
        self.brightness_slider.set_hexpand(True)
        self.brightness_slider.set_size_request(-1, 56) # Força altura mínima
        self.brightness_slider.connect("value-changed", self.on_brightness_changed)

        self.brightness_overlay = Overlay(
            name="dashboard-brightness-overlay",
            child=self.brightness_slider,
            h_expand=True,
            overlays=[
                icons.image(
                    "brightness_high",
                    widget_name="slider-icon-inside",
                    size=20,
                    h_align="start",
                    v_align="center",
                )
            ]
        )

        self.sidebar = Box(
            name="dashboard-sidebar",
            orientation="v",
            spacing=12,
            h_align="fill",
            v_align="fill",
            children=[
                self.sidebar_button_widgets,
                self.sidebar_button_wallpapers,
                Box(v_expand=True),
                self.sidebar_button_config,
            ],
        )
        self.brightness_overlay.set_overlay_pass_through(self.brightness_overlay.get_overlays()[0], True)


        self.brightness_box = Box(
            name="dashboard-brightness-box",
            orientation="h",
            spacing=10,
            children=[self.brightness_overlay]
        )

        # 2. Bluetooth Button (Real Data)
        self.bluetooth_label = Label(label="Desligado", name="config-item-subtext", h_align="start")
        self.bluetooth_btn = Button(
            name="config-item-button",
            h_expand=True,
            on_clicked=lambda *_: self.notch.open_notch("bluetooth"),
            child=Box(
                orientation="h",
                spacing=12,
                children=[
                    icons.image("bluetooth", widget_name="config-item-icon", size=22),
                    Box(
                        orientation="v",
                        h_align="start",
                        children=[
                            Label(label="Bluetooth", name="config-item-text", h_align="start"),
                            self.bluetooth_label
                        ]
                    ),
                    Box(h_expand=True),
                    icons.image("chevron_right", widget_name="config-item-arrow", size=18)
                ]
            )
        )

        # 3. Audio Button (Real Data)
        self.audio_label = Label(label="Desconectado", name="config-item-subtext", h_align="start")
        self.audio_btn = Button(
            name="config-item-button",
            h_expand=True,
            on_clicked=lambda *_: self.notch.open_notch("audio"),
            child=Box(
                orientation="h",
                spacing=12,
                children=[
                    icons.image("vol_high", widget_name="config-item-icon", size=22),
                    Box(
                        orientation="v",
                        h_align="start",
                        children=[
                            Label(label="Áudio", name="config-item-text", h_align="start"),
                            self.audio_label
                        ]
                    ),
                    Box(h_expand=True),
                    icons.image("chevron_right", widget_name="config-item-arrow", size=18)
                ]
            )
        )

        # 4. Network Button (Real Data)
        self.network_icon_label = icons.image("wifi_3", widget_name="config-item-icon", size=22)
        self.network_label = Label(label="Desconectado", name="config-item-subtext", h_align="start")
        self.network_btn = Button(
            name="config-item-button",
            h_expand=True,
            on_clicked=lambda *_: self.notch.open_notch("network"),
            child=Box(
                orientation="h",
                spacing=12,
                children=[
                    self.network_icon_label,
                    Box(
                        orientation="v",
                        h_align="start",
                        children=[
                            Label(label="Rede", name="config-item-text", h_align="start"),
                            self.network_label
                        ]
                    ),
                    Box(h_expand=True),
                    icons.image("chevron_right", widget_name="config-item-arrow", size=18)
                ]
            )
        )

        # Página de Configurações
        self.config_page = Box(
            name="dashboard-config-page",
            orientation="v",
            spacing=4,
            h_align="fill",
            h_expand=True,
            v_align="start",
            v_expand=True,
            children=[
                Label(label="Painel de Controle", name="config-title", h_align="start"),
                self.brightness_box,
                Box(
                    name="config-items-grid",
                    orientation="h",
                    spacing=10,
                    h_align="fill",
                    h_expand=True,
                    children=[
                        self.bluetooth_btn,
                        self.audio_btn,
                        self.network_btn
                    ]
                )
            ]
        )
        
        self.stack = Stack(
            name="content-dashboard",
            transition_type="slide-left-right",
            transition_duration=500,
            orientation="h",
            h_align="fill",
            h_expand=True,
            v_align="fill",
            v_expand=True,
            children=[
                self.teste1,
                self.wallpapers,
                self.config_page
            ]
        )

        self.dashboard_shell = Box(
            name="dashboard-shell",
            orientation="h",
            spacing=10,
            h_align="fill",
            h_expand=True,
            v_align="fill",
            v_expand=True,
            children=[
                self.sidebar,
                self.stack,
            ],
        )

        self.add(self.dashboard_shell)

        # Polling para status real
        self.update_status()
        GLib.timeout_add_seconds(3, self.update_status)

        self.show_all()

    def on_brightness_changed(self, slider):
        val = int(slider.get_value())
        if val < 10:
            val = 10
            slider.set_value(10)
        exec_shell_command_async(f"brightnessctl set {val}%")

    def update_status(self):
        threading.Thread(target=self._fetch_all_data, daemon=True).start()
        return True

    def _fetch_all_data(self):
        # 1. Brilho
        try:
            curr = int(subprocess.check_output(["brightnessctl", "g"], text=True).strip())
            max_val = int(subprocess.check_output(["brightnessctl", "m"], text=True).strip())
            brightness_percent = int((curr / max_val) * 100)
        except: brightness_percent = 0

        # Preparar ambiente em inglês para pactl e bluetoothctl
        env = os.environ.copy()
        env["LC_ALL"] = "C"

        # 2. Bluetooth Status
        bt_text = "Desligado"
        try:
            bt_status = subprocess.check_output(["bluetoothctl", "show"], text=True, env=env)
            if "Powered: yes" in bt_status:
                bt_text = "Ligado"
                bt_info = subprocess.check_output(["bluetoothctl", "info"], text=True, env=env)
                name_match = re.search(r"Name: (.*)", bt_info)
                if name_match:
                    bt_text = name_match.group(1).strip()
            else:
                bt_text = "Desativado"
        except: pass

        # 3. Audio Status (Sink Default)
        audio_text = "Desconhecido"
        try:
            info_out = subprocess.check_output(["pactl", "info"], text=True, env=env)
            def_sink = re.search(r"Default Sink: (.*)", info_out).group(1).strip()
            
            sinks_out = subprocess.check_output(["pactl", "list", "sinks"], text=True, env=env)
            blocks = re.split(r"Sink #\d+", sinks_out)[1:]
            for block in blocks:
                if def_sink in block:
                    desc_match = re.search(r"Description: (.*)", block)
                    if desc_match:
                        audio_text = desc_match.group(1).strip()
                        if len(audio_text) > 15:
                            audio_text = audio_text[:12] + "..."
                        break
        except: pass

        # 4. Network Status
        network_text = "Desconectado"
        network_icon_name = "wifi_off"
        try:
            nm_status = subprocess.check_output(
                ["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"],
                text=True
            )
            wifi_enabled = subprocess.check_output(["nmcli", "radio", "wifi"], text=True).strip().lower() == "enabled"

            wifi_connection = None
            ethernet_connection = None
            for line in nm_status.splitlines():
                parts = line.split(":", 2)
                if len(parts) != 3:
                    continue
                dev_type, dev_state, dev_connection = parts
                if dev_type == "wifi" and dev_state == "connected":
                    wifi_connection = dev_connection.strip()
                    break
                if dev_type == "ethernet" and dev_state == "connected":
                    ethernet_connection = dev_connection.strip()

            if wifi_connection:
                network_text = wifi_connection or "Wi-Fi conectado"
                network_icon_name = "wifi_3"
            elif ethernet_connection:
                network_text = ethernet_connection or "Rede cabeada"
                network_icon_name = "world"
            elif not wifi_enabled:
                network_text = "Wi-Fi desligado"
                network_icon_name = "wifi_off"
            else:
                network_text = "Sem conexão"
                network_icon_name = "world_off"
        except:
            pass

        idle_add(self._update_ui, brightness_percent, bt_text, audio_text, network_text, network_icon_name)

    def _update_ui(self, brightness, bt_text, audio_text, network_text, network_icon_name):
        # Update Brightness Slider
        self.brightness_slider.handler_block_by_func(self.on_brightness_changed)
        self.brightness_slider.set_value(brightness)
        self.brightness_slider.handler_unblock_by_func(self.on_brightness_changed)
        
        # Update Labels
        self.bluetooth_label.set_label(bt_text)
        self.audio_label.set_label(audio_text)
        self.network_label.set_label(network_text)
        icons.set_image(self.network_icon_label, network_icon_name)

    def go_to_child(self, number):
        self.stack.set_visible_child(self.stack.get_children()[number])
        self._set_active_sidebar_button(number)
        self.wallpapers.search_entry.set_text("")
        if number == 1:
            self.wallpapers.search_entry.grab_focus()
        if number == 2:
            self.update_status()

    def _create_sidebar_button(self, icon_name, tooltip, child_index):
        button = Button(
            name="dashboard-sidebar-button",
            h_align="center",
            v_align="center",
            tooltip_text=tooltip,
            on_clicked=lambda *_: self.go_to_child(child_index),
            child=icons.image(icon_name, widget_name="dashboard-sidebar-icon", size=20),
        )
        button.connect("enter_notify_event", self.on_button_enter)
        button.connect("leave_notify_event", self.on_button_leave)
        return button

    def _set_active_sidebar_button(self, active_index):
        for index, button in enumerate(self.sidebar_buttons):
            if index == active_index:
                button.add_style_class("active")
            else:
                button.remove_style_class("active")

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)
