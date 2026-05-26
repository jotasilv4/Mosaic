import shlex
import subprocess
import threading

from fabric.utils import exec_shell_command_async, idle_add
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib, Gdk, Gtk

import modules.icons as icons


class NetworkItem(Button):
    def __init__(self, ssid, signal, security, in_use, network_module, **kwargs):
        super().__init__(
            name="network-item",
            on_clicked=lambda *_: self.connect_network(),
            **kwargs,
        )
        self.ssid = ssid
        self.in_use = in_use
        self.network_module = network_module

        privacy = " • Privada" if security and security != "--" else ""
        signal_text = f"{signal}%" if signal else "--"
        status_text = "Conectado" if in_use else f"Sinal: {signal_text}{privacy}"

        self.icon_label = icons.image("wifi_3", widget_name="network-item-icon", size=20)
        self.name_label = Label(
            name="network-item-name",
            label=ssid,
            h_align="start",
            ellipsize="end",
        )
        self.status_label = Label(
            name="network-item-status",
            label=status_text,
            h_align="start",
            style_classes="dim",
        )
        self.chevron = icons.image("chevron_right", widget_name="network-item-arrow", size=18)

        self.info_box = Box(
            orientation="v",
            spacing=2,
            children=[self.name_label, self.status_label],
        )

        self.content_box = Box(
            orientation="h",
            spacing=10,
            children=[self.icon_label, self.info_box, Box(h_expand=True), self.chevron],
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

    def connect_network(self):
        if self.in_use:
            return
        exec_shell_command_async(f"nmcli device wifi connect {shlex.quote(self.ssid)}")
        GLib.timeout_add_seconds(2, self.network_module.update_status)


class EthernetItem(Button):
    def __init__(self, device, connection_name, connected, network_module, **kwargs):
        super().__init__(
            name="network-item",
            on_clicked=lambda *_: self.toggle_ethernet(),
            **kwargs,
        )
        self.device = device
        self.connection_name = connection_name
        self.connected = connected
        self.network_module = network_module

        device_label = connection_name or device or "Ethernet"
        status_text = "Conectado" if connected else "Desconectado"

        self.icon_label = icons.image("world", widget_name="network-item-icon", size=20)
        self.name_label = Label(
            name="network-item-name",
            label=device_label,
            h_align="start",
            ellipsize="end",
        )
        self.status_label = Label(
            name="network-item-status",
            label=status_text,
            h_align="start",
            style_classes="dim",
        )
        self.chevron = icons.image("chevron_right", widget_name="network-item-arrow", size=18)

        self.info_box = Box(
            orientation="v",
            spacing=2,
            children=[self.name_label, self.status_label],
        )

        self.content_box = Box(
            orientation="h",
            spacing=10,
            children=[self.icon_label, self.info_box, Box(h_expand=True), self.chevron],
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

    def toggle_ethernet(self):
        if not self.device:
            return
        if self.connected:
            exec_shell_command_async(f"nmcli device disconnect {shlex.quote(self.device)}")
        else:
            exec_shell_command_async(f"nmcli device connect {shlex.quote(self.device)}")
        GLib.timeout_add_seconds(2, self.network_module.update_status)


class Network(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="network-menu",
            orientation="v",
            spacing=10,
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
            **kwargs,
        )
        self.notch = kwargs.get("notch")

        self.header = Box(
            name="network-header",
            orientation="h",
            spacing=10,
            children=[
                Button(
                    name="back-button",
                    child=icons.image("chevron_left", size=20),
                    on_clicked=lambda *_: (
                        self.notch.open_notch("dashboard"),
                        self.notch.dashboard.go_to_child(2),
                    ),
                ),
                Label(label="Rede", name="network-title", h_align="start"),
                Box(h_expand=True),
                Button(
                    name="scan-button",
                    child=icons.image("reload", size=20),
                    on_clicked=lambda *_: self.update_status(),
                ),
            ],
        )

        self.status_icon = icons.image("wifi_off", widget_name="network-status-icon", size=26)
        self.status_title = Label(name="network-status-title", label="Wi-Fi desligado", h_align="start")
        self.status_subtitle = Label(name="network-status-subtitle", label="Ative o Wi-Fi para buscar redes", h_align="start")

        self.status_box = Box(
            name="network-status-box",
            orientation="h",
            spacing=12,
            children=[
                self.status_icon,
                Box(
                    orientation="v",
                    spacing=2,
                    children=[self.status_title, self.status_subtitle],
                ),
            ],
        )

        self.network_list_box = Box(orientation="v", spacing=5)
        self.scrolled_window = ScrolledWindow(
            name="network-scrolled",
            child=self.network_list_box,
            h_expand=True,
            v_expand=False,
            min_content_size=(-1, 220),
        )
        self.scrolled_window.set_size_request(-1, 220)
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_propagate_natural_height(False)

        self.add(self.header)
        self.add(self.status_box)
        self.add(self.scrolled_window)

        self.update_status()
        GLib.timeout_add_seconds(8, self.update_status)

    def open_network(self):
        self.update_status()

    def update_status(self):
        threading.Thread(target=self._fetch_network_data, daemon=True).start()
        return True

    def _fetch_network_data(self):
        try:
            ethernet_device = None
            ethernet_connected = False
            ethernet_connection = None

            dev_status_out = subprocess.check_output(
                ["nmcli", "-t", "-f", "TYPE,DEVICE,STATE,CONNECTION", "device"],
                text=True,
            )
            for line in dev_status_out.splitlines():
                parts = line.split(":", 3)
                if len(parts) != 4:
                    continue
                dev_type, dev_name, dev_state, dev_connection = parts
                if dev_type != "ethernet":
                    continue
                ethernet_device = dev_name
                if dev_state == "connected":
                    ethernet_connected = True
                    ethernet_connection = dev_connection.strip()
                    break

            wifi_enabled = subprocess.check_output(
                ["nmcli", "radio", "wifi"], text=True
            ).strip().lower() == "enabled"

            current_ssid = None
            for line in dev_status_out.splitlines():
                parts = line.split(":", 3)
                if len(parts) == 4 and parts[0] == "wifi" and parts[2] == "connected":
                    current_ssid = parts[3]
                    break

            networks = []
            if wifi_enabled:
                wifi_out = subprocess.check_output(
                    ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "auto"],
                    text=True,
                )

                seen = set()
                for line in wifi_out.splitlines():
                    parts = line.split(":", 3)
                    if len(parts) < 4:
                        continue
                    in_use = parts[0].strip() == "*"
                    ssid = parts[1].replace("\\:", ":").strip()
                    signal = parts[2].strip()
                    security = parts[3].strip()
                    if not ssid or ssid in seen:
                        continue
                    seen.add(ssid)
                    networks.append((ssid, signal, security, in_use))

            networks.sort(key=lambda item: (not item[3], -(int(item[1]) if item[1].isdigit() else 0), item[0].lower()))
            idle_add(
                self._update_ui,
                wifi_enabled,
                current_ssid,
                networks,
                ethernet_device,
                ethernet_connected,
                ethernet_connection,
            )
        except Exception as err:
            print(f"Error fetching network data: {err}")
            idle_add(self._update_ui, False, None, [], None, False, None)

    def _update_ui(self, wifi_enabled, current_ssid, networks, ethernet_device, ethernet_connected, ethernet_connection):
        for child in self.network_list_box.get_children():
            self.network_list_box.remove(child)

        if current_ssid:
            icons.set_image(self.status_icon, "wifi_3")
            self.status_title.set_label(current_ssid)
            self.status_subtitle.set_label("Conectado")
        elif ethernet_connected:
            icons.set_image(self.status_icon, "world")
            self.status_title.set_label(ethernet_connection or "Rede cabeada")
            self.status_subtitle.set_label("Conectado via cabo")
        elif not wifi_enabled:
            icons.set_image(self.status_icon, "wifi_off")
            self.status_title.set_label("Wi-Fi desligado")
            self.status_subtitle.set_label("Ative o Wi-Fi no sistema")
        else:
            icons.set_image(self.status_icon, "world_off")
            self.status_title.set_label("Não conectado")
            self.status_subtitle.set_label("Escolha uma rede para conectar")

        if ethernet_device:
            self.network_list_box.add(
                EthernetItem(
                    ethernet_device,
                    ethernet_connection,
                    ethernet_connected,
                    self,
                )
            )

        if not wifi_enabled:
            self.network_list_box.add(Label(label="Wi-Fi desligado", style_classes="dim"))
        else:
            if not networks:
                self.network_list_box.add(Label(label="Nenhuma rede encontrada", style_classes="dim"))
            else:
                for ssid, signal, security, in_use in networks:
                    self.network_list_box.add(NetworkItem(ssid, signal, security, in_use, self))

        self.show_all()
