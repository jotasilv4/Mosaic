from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from fabric.utils import exec_shell_command_async, idle_add
import modules.icons as icons
from gi.repository import GLib, Gdk, Gtk
import subprocess
import threading

class Brightness(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="brightness-menu",
            orientation="v",
            spacing=15,
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
            **kwargs,
        )

        self.notch = kwargs.get("notch")

        # Header
        self.header = Box(
            name="brightness-header",
            orientation="h",
            spacing=10,
            children=[
                Button(
                    name="back-button",
                    child=icons.image("chevron_left", size=20),
                    on_clicked=lambda *_: (self.notch.open_notch("dashboard"), self.notch.dashboard.go_to_child(2))
                ),
                Label(label="Brilho", name="brightness-title", h_align="start"),
            ]
        )

        # Brightness Slider (Material You Style)
        self.brightness_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.brightness_slider.set_name("brightness-slider")
        self.brightness_slider.set_draw_value(False)
        self.brightness_slider.set_hexpand(True)
        self.brightness_slider.connect("value-changed", self.on_brightness_changed)

        self.slider_overlay = Overlay(
            name="brightness-slider-overlay",
            child=self.brightness_slider,
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
        self.slider_overlay.set_overlay_pass_through(self.slider_overlay.get_overlays()[0], True)

        self.label_value = Label(label="0%", name="slider-value-label")

        self.slider_container = Box(
            name="brightness-slider-box-new",
            orientation="h",
            spacing=10,
            children=[
                self.slider_overlay,
                self.label_value
            ]
        )

        self.add(self.header)
        self.add(self.slider_container)
        self.add(Box(v_expand=True))

        self.update_status()
        # Atualiza a cada 5 segundos caso o brilho mude por teclas de atalho
        GLib.timeout_add_seconds(5, self.update_status)

    def on_brightness_changed(self, slider):
        val = int(slider.get_value())
        if val < 10:
            val = 10
            slider.set_value(10)
        self.label_value.set_label(f"{val}%")
        exec_shell_command_async(f"brightnessctl set {val}%")

    def open_brightness(self):
        self.update_status()

    def update_status(self):
        threading.Thread(target=self._fetch_brightness_data, daemon=True).start()
        return True

    def _fetch_brightness_data(self):
        try:
            # Obter brilho atual em porcentagem
            brightness_out = subprocess.check_output(["brightnessctl", "g"], text=True).strip()
            max_brightness = subprocess.check_output(["brightnessctl", "m"], text=True).strip()
            
            curr = int(brightness_out)
            max_val = int(max_brightness)
            percent = int((curr / max_val) * 100)
            
            if percent < 10:
                percent = 10
            
            idle_add(self._update_ui, percent)
        except Exception as e:
            print(f"Error fetching brightness data: {e}")

    def _update_ui(self, percent):
        self.brightness_slider.handler_block_by_func(self.on_brightness_changed)
        self.brightness_slider.set_value(percent)
        self.label_value.set_label(f"{percent}%")
        self.brightness_slider.handler_unblock_by_func(self.on_brightness_changed)
        self.show_all()
