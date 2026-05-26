import os
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.stack import Stack
from fabric.widgets.eventbox import EventBox
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.widgets.x11 import X11Window as Window
from utils.i3 import ActiveWindows
from fabric.utils.helpers import FormattedString, truncate, exec_shell_command_async
from gi.repository import GLib, Gdk, Gtk, Pango, GdkPixbuf
from modules.corners import MyCorner
import modules.icons as icons
import config.data as data
from modules.notifications import NotificationContainer
from modules.launcher import AppLauncher
from modules.power import PowerMenu
from modules.dashboard import Dashboard
from modules.emoji import EmojiPicker
from modules.authotp import AuthOtp
from modules.tools import Toolbox
from modules.bluetooth import Bluetooth
from modules.audio import Audio
from modules.network import Network
import subprocess
import hashlib
from urllib.parse import unquote
from urllib.request import urlopen

class Notch(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="notch",
            layer="top",
            geometry="top",
            type_hint="normal",
            margin="-8px -4px -8px -4px",
            visible=True,
            all_visible=True,
        )

        #self.bar = kwargs.get("bar", None)

        # Primero inicializamos NotificationContainer
        self.notification = NotificationContainer(notch=self)
        self.notification_history = self.notification.history

        self.launcher = AppLauncher(notch=self)
        self.power = PowerMenu(notch=self)
        self.dashboard = Dashboard(notch=self)
        self.emoji = EmojiPicker(notch=self)
        self.authotp = AuthOtp(notch=self)
        self.bluetooth = Bluetooth(notch=self)
        self.audio = Audio(notch=self)
        self.network = Network(notch=self)

        self.user_label = Label(name="compact-user", label=f"{data.USERNAME}@{data.HOSTNAME}")
        self.active_windows = ActiveWindows(notch=self)
        self.media_cover = Image(
            name="compact-media-cover",
            icon_name="audio-x-generic-symbolic",
            icon_size=24,
        )
        self.media_sound = Label(name="compact-media-sound", label="")
        self.media_status = Box(
            name="compact-media",
            orientation="h",
            h_align="fill",
            h_expand=True,
            v_align="center",
            children=[
                self.media_cover,
                Box(h_expand=True),
                self.media_sound,
            ],
        )
        self.media_status.set_hexpand(True)
        self.media_sound.set_halign(Gtk.Align.END)
        self._media_visible = False
        self._media_is_playing = False
        self._media_art_url = None
        self._media_title = ""
        self._media_sound_frames = ["▁▂▃", "▂▅▂", "▃▇▃", "▂▆▅", "▁▃▆", "▃▅▂"]
        self._media_sound_frame_idx = 0
        self._media_cover_cache_dir = f"/tmp/{data.APP_NAME}/media-covers"
        os.makedirs(self._media_cover_cache_dir, exist_ok=True)

        # Create a stack to hold the three views:
        self.compact_stack = Stack(
            name="notch-compact-stack",
            v_expand=True,
            h_expand=True,
            transition_type="slide-up-down",
            transition_duration=100,
            children=[
                self.user_label,
                self.active_windows
            ]
        )
        self.compact_stack.set_visible_child(self.active_windows)
        GLib.timeout_add_seconds(2, self._refresh_media_status)
        GLib.timeout_add(180, self._animate_media_sound)
        # Create the compact button and set the stack as its child
        self.compact = Gtk.EventBox(name="notch-compact")
        self.compact.set_visible(True)
        self.compact.add(self.compact_stack)
        # Se agrega el mask de smooth scroll junto a scroll y button press.
        self.compact.add_events(
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.compact.connect("scroll-event", self._on_compact_scroll)
        self.compact.connect("button-press-event", lambda widget, event: (self.open_notch("dashboard"), False)[1])
        # Add cursor change on hover.
        self.compact.connect("enter-notify-event", self.on_button_enter)
        self.compact.connect("leave-notify-event", self.on_button_leave)
        
        self.tools = Toolbox(notch=self)
        self.stack = Stack(
            name="notch-content",
            v_expand=True,
            h_expand=True,
            transition_type="crossfade",
            transition_duration=100,
            children=[
                self.compact,
                self.launcher,
                self.power,
                self.dashboard,
                self.emoji,
                self.authotp,
                self.tools,
                self.bluetooth,
                self.audio,
                self.network,
            ]
        )

        self.button_left = Button(
            name="button-bar",
            style_classes="notch",
            child=icons.image(
                "media",
                widget_name="button-bar-label",
                size=20,
                h_align="center",
                v_align="center",
            )
        )
        self.button_left.connect("clicked", lambda _: self.player_music())
        self.button_left.connect("enter_notify_event", self.on_button_enter)
        self.button_left.connect("leave_notify_event", self.on_button_leave)
        
        self.button_right = Button(
            name="button-bar",
            style_classes="notch",
            child=icons.image(
                "authcode",
                widget_name="button-bar-label",
                size=20,
                h_align="center",
                v_align="center",
            )
        )
        self.button_right.connect("clicked", lambda _: self.open_notch("authotp"))
        self.button_right.connect("enter_notify_event", self.on_button_enter)
        self.button_right.connect("leave_notify_event", self.on_button_leave)
        
        # Criar os reveladores para animar os botões
        self.left_revealer = Revealer(
            name="notch-left-revealer",
            transition_type="crossfade",
            transition_duration=150,
            reveal_child=True,
            child=self.button_left
        )
        
        self.right_revealer = Revealer(
            name="notch-right-revealer",
            transition_type="crossfade",
            transition_duration=150,
            reveal_child=True,
            child=self.button_right
        )
        
        # Caixas para posicionar os reveladores próximo ao notch
        self.left_button_container = Box(
            name="notch-left-button-container",
            orientation="h",
            h_align="start",
            v_align="center",
            children=[self.left_revealer]
        )
        
        self.right_button_container = Box(
            name="notch-right-button-container",
            orientation="h",
            h_align="end",
            v_align="center",
            children=[self.right_revealer]
        )
        
        # Ajustar a posição para ficarem mais próximos do notch
        # Você pode ajustar estes valores conforme necessário
        self.left_button_container.set_margin_start(20)
        self.right_button_container.set_margin_end(20)

        self.left_revealer.set_reveal_child(True)
        self.right_revealer.set_reveal_child(True)

        self.corner_left = Box(
            name="notch-corner-left",
            orientation="v",
            h_align="start",
            children=[
                MyCorner("top-right"),
                Box(),
            ]
        )

        self.corner_left.set_margin_start(56)

        self.corner_right = Box(
            name="notch-corner-right",
            orientation="v",
            h_align="end",
            children=[
                MyCorner("top-left"),
                Box(),
            ]
        )

        self.corner_right.set_margin_end(56)

        self.notch_box = CenterBox(
            name="notch-box",
            orientation="h",
            h_align="center",
            v_align="center",
            center_children=self.stack,
        )

        self.notch_overlay = Overlay(
            name="notch-overlay",
            h_expand=True,
            h_align="fill",
            child=self.notch_box,
            overlays=[
                self.corner_left,
                self.corner_right,
                self.left_button_container,   # Adicionar o container do botão esquerdo
                self.right_button_container,  # Adicionar o container do botão direito
            ],
        )

        self.notch_overlay.set_overlay_pass_through(self.corner_left, True)
        self.notch_overlay.set_overlay_pass_through(self.corner_right, True)

        self.notification_revealer = Revealer(
            name="notification-revealer",
            transition_type="slide-down",
            transition_duration=250,
            child_revealed=False,
        )

        self.popup_title = Label(name="notch-popup-title", label="")
        self.popup_body = Label(name="notch-popup-body", label="", max_chars_width=48, ellipsization="end")
        self.popup_close_button = Button(
            name="notch-popup-close",
            child=icons.image("cancel", size=18),
            on_clicked=lambda *_: self.hide_popup(),
        )
        self.popup_close_button.connect("enter-notify-event", self.on_button_enter)
        self.popup_close_button.connect("leave-notify-event", self.on_button_leave)

        self.popup_card = Box(
            name="notch-popup-card",
            orientation="h",
            spacing=10,
            children=[
                Box(
                    orientation="v",
                    spacing=2,
                    h_expand=True,
                    children=[self.popup_title, self.popup_body],
                ),
                self.popup_close_button,
            ],
        )
        self.popup_revealer = Revealer(
            name="notch-popup-revealer",
            transition_type="slide-down",
            transition_duration=220,
            reveal_child=False,
            child=self.popup_card,
        )
        self.popup_revealer.set_no_show_all(True)
        self.popup_revealer.hide()
        self.popup_host = Box(
            name="notch-popup-host",
            orientation="v",
            h_align="center",
            v_align="start",
            children=[self.popup_revealer],
        )
        self.popup_host.set_margin_top(54)
        self.popup_host.set_no_show_all(True)
        self.popup_host.hide()
        self.notch_overlay.add_overlay(self.popup_host)
        self._popup_timeout_id = None

        self.boxed_notification_revealer = Box(
            name="boxed-notification-revealer",
            orientation="v",
            children=[
                self.notification_revealer,
            ]
        )

        self.notch_complete = Box(
            name="notch-complete",
            orientation="v",
            children=[
                self.notch_overlay,
                self.boxed_notification_revealer
            ]
        )

        self.hidden = False
        self._is_notch_open = False  # Add a flag to track notch open state
        self._scrolling = False

        self.add(self.notch_complete)
        self.show_all()

        #self._show_overview_children(False)
        self.add_keybinding("Escape", lambda *_: self.close_notch())

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def player_music(self):
        exec_shell_command_async("youtube-music")
        print("Player Youtbe Music")
    
    def colorpicker(self):
        self.open_notch("emoji")
        print("ColorPicker")

    def close_notch(self):
        self.left_revealer.set_reveal_child(True)
        self.right_revealer.set_reveal_child(True)

        self._is_notch_open = False

        if self.hidden:
            self.notch_box.remove_style_class("hideshow")
            self.notch_box.add_style_class("hidden")

        for widget in [self.launcher, self.power, self.dashboard, self.emoji, self.authotp, self.tools, self.bluetooth, self.audio, self.network]:
            widget.remove_style_class("open")
        for style in ["launcher", "power", "dashboard", "emoji", "authotp", "tools", "notification", "bluetooth", "audio", "network"]:
            self.stack.remove_style_class(style)

        self.authotp.close_otp()

        self.stack.set_visible_child(self.compact)

    def open_notch(self, widget):
        self.left_revealer.set_reveal_child(False)
        self.right_revealer.set_reveal_child(False)

        widgets = {
            "launcher": self.launcher,
            "power": self.power,
            "dashboard": self.dashboard,
            "emoji": self.emoji,
            "authotp": self.authotp,
            "tools": self.tools,
            "bluetooth": self.bluetooth,
            "audio": self.audio,
            "network": self.network,
        }

        if self.hidden:
            self.notch_box.remove_style_class("hidden")
            self.notch_box.add_style_class("hideshow")

        for style in ["launcher", "power", "dashboard", "emoji", "authotp", "tools", "notification", "bluetooth", "audio", "network"]:
            self.stack.remove_style_class(style)
        for w in widgets.values():
            w.remove_style_class("open")

        if widget in widgets:
            self.active_windows.update_window_label(truncate("Mosaic", 24))
            #if widget != "dashboard": # Avoid adding dashboard class again if switching from bluetooth
            #   self.stack.add_style_class(widget)
            self.stack.add_style_class(widget)
            self.stack.set_visible_child(widgets[widget])
            widgets[widget].add_style_class("open")

            self.present()

            if widget == "launcher":
                self.launcher.open_launcher()
                self.launcher.search_entry.set_text("")
                GLib.idle_add(lambda: self.launcher.search_entry.grab_focus())

            if widget == "authotp":
                self.authotp.open_otp()
                self.authotp.search_otp.set_text("")
                GLib.idle_add(lambda: self.authotp.search_otp.grab_focus())

            if widget == "emoji":
                self.emoji.open_picker()
                self.emoji.search_entry.set_text("")
                GLib.idle_add(lambda: self.emoji.search_entry.grab_focus())
            
            if widget == "bluetooth":
                self.bluetooth.open_bluetooth()
            
            if widget == "audio":
                self.audio.open_audio()

            if widget == "network":
                self.network.open_network()
        else:
            self.stack.set_visible_child(self.dashboard)

        self._is_notch_open = True # Set notch state to open

    # def _show_overview_children(self, show_children):
    #     for child in self.overview.get_children():
    #         if show_children:
    #             child.set_visible(show_children)
    #             self.overview.add_style_class("show")
    #         else:
    #             child.set_visible(show_children)
    #             self.overview.remove_style_class("show")
    #     return False  # Esto evita que el timeout se repita

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.notch_box.add_style_class("hidden")
        else:
            self.notch_box.remove_style_class("hidden")

    def _on_compact_scroll(self, widget, event):
        if self._scrolling:
            return True

        children = self.compact_stack.get_children()
        current = children.index(self.compact_stack.get_visible_child())
        new_index = current

        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < -0.1:
                new_index = (current - 1) % len(children)
            elif event.delta_y > 0.1:
                new_index = (current + 1) % len(children)
            else:
                return False
        elif event.direction == Gdk.ScrollDirection.UP:
            new_index = (current - 1) % len(children)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            new_index = (current + 1) % len(children)
        else:
            return False

        self.compact_stack.set_visible_child(children[new_index])
        self._scrolling = True
        GLib.timeout_add(250, self._reset_scrolling)
        return True

    def _reset_scrolling(self):
        self._scrolling = False
        return False

    def _set_media_cover(self, art_url):
        if art_url == self._media_art_url:
            return

        self._media_art_url = art_url
        if not art_url:
            self.media_cover.set_from_icon_name("audio-x-generic-symbolic", Gtk.IconSize.MENU)
            return

        local_path = None
        if art_url.startswith("file://"):
            local_path = unquote(art_url[7:])
        elif art_url.startswith("/"):
            local_path = art_url
        elif art_url.startswith("http://") or art_url.startswith("https://"):
            extension = os.path.splitext(art_url.split("?", 1)[0])[1] or ".img"
            file_hash = hashlib.sha1(art_url.encode("utf-8")).hexdigest()
            local_path = os.path.join(self._media_cover_cache_dir, f"{file_hash}{extension}")
            if not os.path.exists(local_path):
                try:
                    with urlopen(art_url, timeout=1.5) as response:
                        with open(local_path, "wb") as image_file:
                            image_file.write(response.read())
                except Exception:
                    local_path = None

        if local_path and os.path.exists(local_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(local_path, 28, 28, True)
                self.media_cover.set_from_pixbuf(pixbuf)
                return
            except Exception:
                pass

        self.media_cover.set_from_icon_name("audio-x-generic-symbolic", Gtk.IconSize.MENU)

    def _get_playing_media(self):
        try:
            result = subprocess.run(
                [
                    "playerctl",
                    "--all-players",
                    "metadata",
                    "--format",
                    "{{status}}|{{playerName}}|{{artist}}|{{title}}|{{mpris:artUrl}}",
                ],
                capture_output=True,
                text=True,
                timeout=0.8,
                check=False,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        fallback_media = None
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) != 5:
                continue
            status, player_name, artist, title, art_url = parts
            if status.lower() != "playing":
                continue
            if (player_name or "").lower() == "playerctld":
                continue

            song_title = title or ""
            song_artist = artist or ""
            media_data = None
            if song_title:
                media_data = {
                    "text": song_title,
                    "art_url": art_url,
                }
            elif song_artist:
                media_data = {
                    "text": song_artist,
                    "art_url": art_url,
                }
            else:
                media_data = {
                    "text": "Tocando...",
                    "art_url": art_url,
                }

            if art_url:
                return media_data
            if fallback_media is None:
                fallback_media = media_data

        return fallback_media

    def _refresh_media_status(self):
        media = self._get_playing_media()

        if media:
            self._media_title = media["text"] or "Tocando..."
            self.media_cover.set_tooltip_text(self._media_title)
            self.media_status.set_tooltip_text(self._media_title)
            self._set_media_cover(media["art_url"])
            self._media_is_playing = True
            if not self._media_visible:
                self.compact_stack.add(self.media_status)
                self._media_visible = True
                if self.stack.get_visible_child() == self.compact:
                    self.compact_stack.set_visible_child(self.media_status)
        elif self._media_visible:
            self._media_is_playing = False
            if self.compact_stack.get_visible_child() == self.media_status:
                self.compact_stack.set_visible_child(self.active_windows)
            self.compact_stack.remove(self.media_status)
            self._media_visible = False
            self._set_media_cover(None)
            self._media_title = ""
            self.media_cover.set_tooltip_text(None)
            self.media_status.set_tooltip_text(None)
        else:
            self._media_is_playing = False

        return True

    def _animate_media_sound(self):
        if self._media_is_playing and self._media_visible:
            self._media_sound_frame_idx = (self._media_sound_frame_idx + 1) % len(self._media_sound_frames)
            self.media_sound.set_label(self._media_sound_frames[self._media_sound_frame_idx])
        else:
            self.media_sound.set_label("")
        return True

    def restore_label_properties(self):
        label = self.active_window.get_children()[0]
        if isinstance(label, Gtk.Label):
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_hexpand(True)
            label.set_halign(Gtk.Align.FILL)
            label.queue_resize()

    def show_popup(self, title="Notificacao", message="", timeout_ms=3500):
        if self._popup_timeout_id is not None:
            GLib.source_remove(self._popup_timeout_id)
            self._popup_timeout_id = None

        self.popup_title.set_label(title or "Notificacao")
        self.popup_body.set_label(message or "")
        self.popup_host.show()
        self.popup_revealer.show()
        self.popup_revealer.set_reveal_child(True)
        self.popup_revealer.show_all()
        self._popup_timeout_id = GLib.timeout_add(timeout_ms, self.hide_popup)

    def hide_popup(self):
        if self._popup_timeout_id is not None:
            GLib.source_remove(self._popup_timeout_id)
            self._popup_timeout_id = None
        self.popup_revealer.set_reveal_child(False)
        GLib.timeout_add(self.popup_revealer.get_transition_duration(), self._hide_popup_widget)
        return False

    def _hide_popup_widget(self):
        self.popup_revealer.hide()
        self.popup_host.hide()
        return False