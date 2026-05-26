from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import exec_shell_command_async, idle_add
import modules.icons as icons
from gi.repository import GLib, Gdk, Gtk
import subprocess
import threading
import re
import os

class AudioDeviceItem(Button):
    def __init__(self, name, description, is_default, is_input, audio_module, **kwargs):
        super().__init__(
            name="audio-device-item",
            on_clicked=lambda *_: self.set_as_default(),
            **kwargs
        )
        self.device_name = name
        self.description = description
        self.is_default = is_default
        self.is_input = is_input
        self.audio_module = audio_module

        icon = "mic" if is_input else "vol_high"
        
        self.icon_label = icons.image(icon, widget_name="device-icon", size=20)
        self.name_label = Label(name="device-name", label=description, h_align="start", ellipsize="end")
        self.status_label = Label(name="device-status", h_align="start", style_classes="dim")
        self.info_box = Box(orientation="v", spacing=2, children=[self.name_label, self.status_label])
        self.content_box = Box(orientation="h", spacing=10, children=[self.icon_label, self.info_box])
        self.indicator = icons.image("accept", widget_name="default-indicator", size=18)
        
        self.add(self.content_box)
        self.update_state(is_default)

        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)

    def update_state(self, is_default):
        self.is_default = is_default
        if is_default:
            self.add_style_class("default")
            self.status_label.set_label("Ativo")
            if self.indicator not in self.content_box.get_children():
                self.content_box.add(self.indicator)
        else:
            self.remove_style_class("default")
            self.status_label.set_label("Disponível")
            if self.indicator in self.content_box.get_children():
                self.content_box.remove(self.indicator)
        self.show_all()

    def on_enter(self, widget, event):
        window = widget.get_window()
        if window: window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_leave(self, widget, event):
        window = widget.get_window()
        if window: window.set_cursor(None)

    def set_as_default(self):
        if self.is_default: return
        
        cmd = "set-default-source" if self.is_input else "set-default-sink"
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        
        subprocess.run(["pactl", cmd, self.device_name], env=env)
        
        if not self.is_input:
            try:
                sink_inputs = subprocess.check_output(["pactl", "list", "short", "sink-inputs"], text=True, env=env)
                for line in sink_inputs.splitlines():
                    if line:
                        subprocess.run(["pactl", "move-sink-input", line.split()[0], self.device_name], env=env)
            except: pass
        
        self.audio_module.update_status()

class Audio(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="audio-menu",
            orientation="v",
            spacing=10,
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
            **kwargs,
        )
        self.notch = kwargs.get("notch")

        # Header
        self.header = Box(
            name="audio-header",
            orientation="h",
            spacing=10,
            children=[
                Button(
                    name="back-button",
                    child=icons.image("chevron_left", size=20),
                    on_clicked=lambda *_: (self.notch.open_notch("dashboard"), self.notch.dashboard.go_to_child(2))
                ),
                Label(label="Áudio", name="audio-title", h_align="start"),
            ]
        )

        self.output_volume_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.output_volume_slider.set_name("audio-slider")
        self.output_volume_slider.set_draw_value(False)
        self.output_volume_slider.connect("value-changed", self.on_output_volume_changed)

        self.input_volume_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.input_volume_slider.set_name("audio-slider")
        self.input_volume_slider.set_draw_value(False)
        self.input_volume_slider.connect("value-changed", self.on_input_volume_changed)

        self.output_list = Box(orientation="v", spacing=5)
        self.input_list = Box(orientation="v", spacing=5)

        self.output_scrolled = ScrolledWindow(
            name="audio-devices-scrolled",
            h_expand=True,
            v_expand=False,
            child=self.output_list,
        )
        self.output_scrolled.set_size_request(-1, 110)
        self.output_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.output_scrolled.set_propagate_natural_height(False)

        self.input_scrolled = ScrolledWindow(
            name="audio-devices-scrolled",
            h_expand=True,
            v_expand=False,
            child=self.input_list,
        )
        self.input_scrolled.set_size_request(-1, 110)
        self.input_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.input_scrolled.set_propagate_natural_height(False)

        self.add(self.header)
        self.add(Box(name="audio-sliders-box", orientation="v", spacing=15, children=[
            Box(orientation="v", spacing=5, children=[
                Box(orientation="h", children=[icons.image("vol_high", widget_name="slider-icon", size=20), Label(label="Volume de Saída", h_align="start", h_expand=True)]),
                self.output_volume_slider
            ]),
            Box(orientation="v", spacing=5, children=[
                Box(orientation="h", children=[icons.image("mic", widget_name="slider-icon", size=20), Label(label="Volume de Entrada", h_align="start", h_expand=True)]),
                self.input_volume_slider
            ])
        ]))
        
        self.add(
            Box(
                orientation="v",
                spacing=10,
                children=[
                    Label(label="Saídas", h_align="start", name="list-section-title"),
                    self.output_scrolled,
                    Label(label="Entradas", h_align="start", name="list-section-title"),
                    self.input_scrolled,
                ],
            )
        )

        self.update_status()
        GLib.timeout_add_seconds(5, self.update_status)

    def on_output_volume_changed(self, slider):
        val = int(slider.get_value())
        exec_shell_command_async(f"pactl set-sink-volume @DEFAULT_SINK@ {val}%")

    def on_input_volume_changed(self, slider):
        val = int(slider.get_value())
        exec_shell_command_async(f"pactl set-source-volume @DEFAULT_SOURCE@ {val}%")

    def open_audio(self):
        self.update_status()

    def update_status(self):
        threading.Thread(target=self._fetch_audio_data, daemon=True).start()
        return True

    def _fetch_audio_data(self):
        try:
            env = os.environ.copy(); env["LC_ALL"] = "C"
            info_out = subprocess.check_output(["pactl", "info"], text=True, env=env)
            def_sink = re.search(r"Default Sink: (.*)", info_out).group(1).strip()
            def_source = re.search(r"Default Source: (.*)", info_out).group(1).strip()

            sinks_out = subprocess.check_output(["pactl", "list", "sinks"], text=True, env=env)
            sinks, out_vol = self._parse_pactl_list(sinks_out, def_sink)
            
            sources_out = subprocess.check_output(["pactl", "list", "sources"], text=True, env=env)
            sources, in_vol = self._parse_pactl_list(sources_out, def_source)
            # Corrigido o filtro de monitores
            sources = [s for s in sources if ".monitor" not in s["name"]]

            idle_add(self._update_ui, sinks, sources, out_vol, in_vol)
        except Exception as e:
            print(f"Error fetching audio data: {e}")

    def _parse_pactl_list(self, output, default_name):
        devices = []; vol = 0
        # Forma mais robusta de splitar: por blocos que começam com Name:
        blocks = output.split("Name: ")[1:]
        for block in blocks:
            name = block.split("\n")[0].strip()
            desc_match = re.search(r"Description: (.*)", block)
            if desc_match:
                desc = desc_match.group(1).strip()
                is_default = (name == default_name)
                devices.append({"name": name, "desc": desc, "is_default": is_default})
                if is_default:
                    vol_match = re.search(r"Volume:.*?(\d+)%", block)
                    if vol_match: vol = int(vol_match.group(1))
        return devices, vol

    def _update_ui(self, sinks, sources, out_vol, in_vol):
        self.output_volume_slider.handler_block_by_func(self.on_output_volume_changed)
        self.input_volume_slider.handler_block_by_func(self.on_input_volume_changed)
        self.output_volume_slider.set_value(out_vol)
        self.input_volume_slider.set_value(in_vol)
        self.output_volume_slider.handler_unblock_by_func(self.on_output_volume_changed)
        self.input_volume_slider.handler_unblock_by_func(self.on_input_volume_changed)

        self._sync_list(self.output_list, sinks, False)
        self._sync_list(self.input_list, sources, True)

    def _sync_list(self, container, new_data, is_input):
        current_widgets = container.get_children()
        current_names = [w.device_name for w in current_widgets]
        new_names = [d["name"] for d in new_data]
        
        if current_names != new_names:
            for child in current_widgets: container.remove(child)
            for dev in new_data:
                container.add(AudioDeviceItem(dev["name"], dev["desc"], dev["is_default"], is_input, self))
        else:
            for i, dev in enumerate(new_data):
                current_widgets[i].update_state(dev["is_default"])
