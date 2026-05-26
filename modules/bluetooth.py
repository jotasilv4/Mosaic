from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import exec_shell_command_async, idle_add
import modules.icons as icons
from gi.repository import GLib, Gdk, Gtk
import subprocess
import threading
import os
import re

class BluetoothDeviceItem(Button):
    def __init__(self, address, name, connected, paired, bluetooth_module, **kwargs):
        super().__init__(
            name="bluetooth-device-item",
            on_clicked=lambda *_: self.toggle_connection(),
            **kwargs
        )
        self.address = address
        self.device_name = name
        self.connected = connected
        self.paired = paired
        self.bluetooth_module = bluetooth_module

        self.icon_label = icons.image(
            "bluetooth_connected" if connected else "bluetooth_disconnected",
            widget_name="device-icon",
            size=20,
        )
        
        self.name_label = Label(
            name="device-name",
            label=name,
            h_align="start",
            ellipsize="end"
        )
        
        self.status_label = Label(
            name="device-status",
            label="Connected" if connected else ("Paired" if paired else "Available"),
            h_align="start",
            style_classes="dim"
        )

        self.info_box = Box(
            orientation="v",
            spacing=2,
            children=[self.name_label, self.status_label]
        )

        self.content_box = Box(
            orientation="h",
            spacing=10,
            children=[self.icon_label, self.info_box]
        )
        
        self.add(self.content_box)
        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)

    def on_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def toggle_connection(self):
        if self.connected:
            exec_shell_command_async(f"bluetoothctl disconnect {self.address}")
        else:
            if not self.paired:
                exec_shell_command_async(
                    f"bluetoothctl pair {self.address} && bluetoothctl trust {self.address} && bluetoothctl connect {self.address}"
                )
            else:
                exec_shell_command_async(f"bluetoothctl trust {self.address} && bluetoothctl connect {self.address}")
        GLib.timeout_add_seconds(2, self.bluetooth_module.update_status)

class Bluetooth(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="bluetooth-menu",
            orientation="v",
            spacing=10,
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
            **kwargs,
        )

        self.notch = kwargs.get("notch")
        self.scanning = False
        self.bt_env = os.environ.copy()
        self.bt_env["LC_ALL"] = "C"

        # Header
        self.header = Box(
            name="bluetooth-header",
            orientation="h",
            spacing=10,
            children=[
                Button(
                    name="back-button",
                    child=icons.image("chevron_left", size=20),
                    on_clicked=lambda *_: (self.notch.open_notch("dashboard"), self.notch.dashboard.go_to_child(2))
                ),
                Label(label="Bluetooth", name="bluetooth-title", h_align="start"),
                Box(h_expand=True),
                Button(
                    name="scan-button",
                    child=icons.image("reload", size=20),
                    on_clicked=lambda *_: self.toggle_scan()
                )
            ]
        )

        # Power Toggle (Android style)
        self.power_switch = Gtk.Switch(name="bluetooth-switch")
        self.power_switch.set_valign(Gtk.Align.CENTER)
        self.power_switch.connect("state-set", self.on_power_switched)

        self.power_box = Box(
            name="bluetooth-power-box",
            orientation="h",
            spacing=10,
            children=[
                Label(label="Bluetooth Power", h_align="start", h_expand=True),
                self.power_switch
            ]
        )

        # Device List
        self.device_list_box = Box(
            orientation="v",
            spacing=5
        )

        self.scrolled_window = ScrolledWindow(
            name="bluetooth-devices-scrolled",
            child=self.device_list_box,
            h_expand=True,
            v_expand=False,
            min_content_size=(-1, 200)
        )
        self.scrolled_window.set_size_request(-1, 220)
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_propagate_natural_height(False)

        self.add(self.header)
        self.add(self.power_box)
        self.add(self.scrolled_window)

        self.update_status()
        
        # Refresh timer
        GLib.timeout_add_seconds(5, self.update_status)

    def on_power_switched(self, switch, state):
        if state:
            exec_shell_command_async("bluetoothctl power on")
        else:
            exec_shell_command_async("bluetoothctl power off")
        return False # Accept the change

    def open_bluetooth(self):
        self.update_status()

    def toggle_scan(self):
        if self.scanning:
            exec_shell_command_async("bluetoothctl scan off")
            self.scanning = False
        else:
            exec_shell_command_async("bluetoothctl power on && bluetoothctl scan on")
            self.scanning = True
        self.update_status()

    def update_status(self):
        # Run in a thread to not block UI
        threading.Thread(target=self._fetch_bluetooth_data, daemon=True).start()
        return True

    def _fetch_bluetooth_data(self):
        try:
            # Check if adapter exists
            adapter_list = self._run_bt(["list"])
            if not adapter_list.strip():
                idle_add(self._update_ui_no_adapter)
                return

            power_out = self._run_bt(["show"])
            powered = self._is_yes_field(power_out, "Powered")
            
            # Get devices
            devices_out = self._run_bt(["devices"])
            devices = []
            for line in devices_out.strip().split('\n'):
                if line:
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        addr = parts[1]
                        name = parts[2]
                        
                        # Check if connected/paired
                        info_out = self._run_bt(["info", addr])
                        connected = self._is_yes_field(info_out, "Connected")
                        paired = self._is_yes_field(info_out, "Paired")
                        devices.append((addr, name, connected, paired))
            
            idle_add(self._update_ui, powered, devices)
        except Exception as e:
            print(f"Error fetching bluetooth data: {e}")
            idle_add(self._update_ui_no_adapter)

    def _run_bt(self, args):
        result = subprocess.run(
            ["bluetoothctl", *args],
            text=True,
            capture_output=True,
            env=self.bt_env,
            timeout=8,
            check=False,
        )
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return output.strip()

    @staticmethod
    def _is_yes_field(text, field_name):
        match = re.search(rf"{re.escape(field_name)}:\s*(.+)", text, re.IGNORECASE)
        if not match:
            return False
        value = match.group(1).strip().lower()
        return value in {"yes", "sim", "true", "on"}

    def _update_ui_no_adapter(self):
        self.power_switch.set_active(False)
        self.power_switch.set_sensitive(False)
        for child in self.device_list_box.get_children():
            self.device_list_box.remove(child)
        self.device_list_box.add(Label(label="No Bluetooth Adapter Found", style_classes="dim"))
        self.show_all()

    def _update_ui(self, powered, devices):
        self.power_switch.set_sensitive(True)
        self.power_switch.set_active(powered)
        
        # Clear list
        for child in self.device_list_box.get_children():
            self.device_list_box.remove(child)
            
        if not powered:
            self.device_list_box.add(Label(label="Bluetooth is disabled", style_classes="dim"))
        elif not devices:
            self.device_list_box.add(Label(label="No devices found", style_classes="dim"))
        else:
            # Sort: Connected first, then Paired, then others
            devices.sort(key=lambda x: (not x[2], not x[3], x[1]))
            for addr, name, connected, paired in devices:
                item = BluetoothDeviceItem(addr, name, connected, paired, self)
                self.device_list_box.add(item)
        
        self.show_all()
