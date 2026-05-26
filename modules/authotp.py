import os, json, time, math
import subprocess
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.entry import Entry
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.revealer import Revealer
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import GLib, Gdk, Gtk
import modules.icons as icons
import config.data as data
from services.qrcode import (
    read_and_save_to_json,
    CodeOTP,
    parse_otpauth_uri,
    create_otp_entry,
    create_otp_entry_from_uri,
    is_microsoft_authenticator_activation_uri,
)

class AuthOtp(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="auth-otp",
            orientation="v",
            visible=True,
            v_expand=True,
            h_expand=True,
            **kwargs,
        )

        self.notch = kwargs["notch"]
        self.selected_index = -1
        self.codes_path = f"{data.CACHE_DIR}/otp/otp_codes.json"
        self.manual_form_visible = False

        # Header para Pesquisar
        self.button_manual = Button(
            name="button-otp-action",
            style_classes="manual",
            can_focus=False,
            v_align="center",
            h_align="center",
            on_clicked=lambda *_: self.toggle_manual_form(),
            child=icons.image("add", widget_name="button-otp-action-label", size=22)
        )
        self.button_manual.connect("enter_notify_event", self.on_button_enter)
        self.button_manual.connect("leave_notify_event", self.on_button_leave)

        self.button_qrcode = Button(
            name="button-otp-action",
            style_classes="qrcode",
            can_focus=False,
            v_align="center",
            h_align="center",
            on_clicked=lambda *_: self.read_qrcode(),
            child=icons.image("qrcode", widget_name="button-otp-action-label", size=22)
        )
        self.button_qrcode.connect("enter_notify_event", self.on_button_enter)
        self.button_qrcode.connect("leave_notify_event", self.on_button_leave)

        self.search_otp = Entry(
            name="search-otp",
            placeholder="Search OTP...",
            h_expand=True,
            h_align="fill",
        )
        self.search_otp.props.xalign = 0.5
        self.search_otp.connect("notify::text", self.on_search_text_changed)

        self.header = CenterBox(
            name="auth-otp-header",
            orientation="h",
            h_align="fill",
            v_align="center",
            h_expand=True,
            visible=True,
            spacing=5,
            start_children=self.search_otp,
            end_children=Box(
                name="otp-header-actions",
                orientation="h",
                spacing=6,
                children=[
                    self.button_manual,
                    self.button_qrcode
                ]
            )
        )

        self.manual_issuer = Entry(
            name="manual-otp-entry",
            placeholder="Issuer (ex: Azure)",
            h_expand=True,
            h_align="fill",
        )
        self.manual_account = Entry(
            name="manual-otp-entry",
            placeholder="Account (optional)",
            h_expand=True,
            h_align="fill",
        )
        self.manual_secret = Entry(
            name="manual-otp-entry",
            placeholder="Azure key or otpauth:// URI",
            h_expand=True,
            h_align="fill",
        )
        self.manual_period = Entry(
            name="manual-otp-entry",
            placeholder="Period",
            h_expand=True,
            h_align="fill",
        )
        self.manual_period.set_text("30")
        self.manual_digits = Entry(
            name="manual-otp-entry",
            placeholder="Digits",
            h_expand=True,
            h_align="fill",
        )
        self.manual_digits.set_text("6")
        self.manual_status = Label(
            name="manual-otp-status",
            label="Paste the Azure manual key, or an otpauth:// URI.",
            h_align="start",
        )
        self.manual_save = Button(
            name="manual-otp-button",
            style_classes="save",
            h_align="center",
            child=Label(label="Add OTP"),
            on_clicked=lambda *_: self.save_manual_otp()
        )
        self.manual_cancel = Button(
            name="manual-otp-button",
            style_classes="cancel",
            h_align="center",
            child=Label(label="Cancel"),
            on_clicked=lambda *_: self.hide_manual_form()
        )
        self.manual_save.connect("enter_notify_event", self.on_button_enter)
        self.manual_save.connect("leave_notify_event", self.on_button_leave)
        self.manual_cancel.connect("enter_notify_event", self.on_button_enter)
        self.manual_cancel.connect("leave_notify_event", self.on_button_leave)

        self.manual_form = Box(
            name="manual-otp-form",
            orientation="v",
            h_align="fill",
            h_expand=True,
            spacing=8,
            children=[
                Box(
                    name="manual-otp-row",
                    orientation="h",
                    h_align="fill",
                    h_expand=True,
                    spacing=8,
                    children=[
                        self.manual_issuer,
                        self.manual_account
                    ]
                ),
                Box(
                    name="manual-otp-row",
                    orientation="h",
                    h_align="fill",
                    h_expand=True,
                    spacing=8,
                    children=[
                        self.manual_secret,
                        self.manual_period,
                        self.manual_digits
                    ]
                ),
                Box(
                    name="manual-otp-footer",
                    orientation="h",
                    h_align="fill",
                    h_expand=True,
                    spacing=8,
                    children=[
                        self.manual_status,
                        self.manual_cancel,
                        self.manual_save
                    ]
                )
            ]
        )
        self.manual_revealer = Revealer(
            name="manual-otp-revealer",
            child_revealed=False,
            transition_type="slide-down",
            transition_duration=220,
            child=self.manual_form,
        )

        #Viewport Otps
        self.viewport = Box(name="viewport-otp", h_align="start", spacing=10, orientation="v")
        self.scrolled_window = ScrolledWindow(
            name="scrolled-window-otp",
            spacing=8,
            min_content_size=(500, 150),
            max_content_size=(500, 150),
            child=self.viewport,
            h_align="center"
        )

        self.resize_viewport()

        self.children = Box(
            name="auth-otp-content",
            orientation="v",
            h_align="center",
            v_align="fill",
            h_expand=True,
            v_expand=True,
            visible=True,
            spacing=10,
            children=[
                self.header,
                self.manual_revealer,
                self.scrolled_window
            ]
        )
        self.show_all()

    def close_otp(self):
        self.viewport.children = []
        self.selected_index = -1

    def open_otp(self):
        self.arrange_viewport()

    def read_qrcode(self):
        success = read_and_save_to_json()
        # Se o QR code foi lido e salvo com sucesso, atualize o viewport
        if success:
            # Limpa a caixa de pesquisa (se houver) para mostrar todos os OTPs, incluindo o novo
            if hasattr(self, 'search_otp'):
                self.search_otp.set_text("")
            
            # Atualiza o viewport para mostrar todos os OTPs, incluindo o recém-adicionado
            self.arrange_viewport()

    def toggle_manual_form(self):
        self.manual_form_visible = not self.manual_form_visible
        self.manual_revealer.set_reveal_child(self.manual_form_visible)

        if self.manual_form_visible:
            self.manual_status.set_label("Paste the Azure manual key, or an otpauth:// URI.")
            GLib.idle_add(lambda: self.manual_issuer.grab_focus())

    def hide_manual_form(self):
        self.manual_form_visible = False
        self.manual_revealer.set_reveal_child(False)
        self.clear_manual_form()

    def clear_manual_form(self):
        self.manual_issuer.set_text("")
        self.manual_account.set_text("")
        self.manual_secret.set_text("")
        self.manual_period.set_text("30")
        self.manual_digits.set_text("6")
        self.manual_status.set_label("Paste the Azure manual key, or an otpauth:// URI.")

    def save_manual_otp(self):
        issuer = self.manual_issuer.get_text().strip()
        account_name = self.manual_account.get_text().strip()
        secret_or_uri = self.manual_secret.get_text().strip()
        period = self.manual_period.get_text().strip() or "30"
        digits = self.manual_digits.get_text().strip() or "6"

        if not secret_or_uri:
            self.manual_status.set_label("Azure key or otpauth URI is required.")
            return

        if is_microsoft_authenticator_activation_uri(secret_or_uri):
            self.manual_status.set_label("This Microsoft QR cannot generate OTP. Use Azure's manual key.")
            return

        try:
            if secret_or_uri.lower().startswith("otpauth://"):
                entry = create_otp_entry_from_uri(secret_or_uri)
            else:
                entry = create_otp_entry(secret_or_uri, issuer or "Azure", account_name, period, digits)
        except Exception as error:
            print(f"Manual OTP failed: {error}")
            self.manual_status.set_label("Invalid Azure key or otpauth URI.")
            return

        if entry is None:
            self.manual_status.set_label("Invalid OTP data.")
            return

        try:
            os.makedirs(os.path.dirname(self.codes_path), exist_ok=True)
            with open(self.codes_path, "r") as file:
                otps = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            otps = []

        otps.append(entry)
        with open(self.codes_path, "w") as file:
            json.dump(otps, file, indent=4)

        self.search_otp.set_text("")
        self.arrange_viewport()
        self.clear_manual_form()
        self.manual_form_visible = False
        self.manual_revealer.set_reveal_child(False)
        exec_shell_command_async('notify-send -a "Mosaic" "OTP Added" "Manual OTP has been added successfully."')
    
    def arrange_viewport(self, query: str = ""):
        self.otps_path = self.codes_path
        if os.path.exists(self.otps_path):
            with open(self.otps_path, "r") as f:
                self.otps_history = json.load(f)
        else:
            self.otps_history = []

        # Limpar timers anteriores para evitar vazamentos de memória
        if hasattr(self, "reload_timers"):
            for timer_id in self.reload_timers:
                GLib.source_remove(timer_id)
        self.reload_timers = []
        
        # Filtrar OTPs com base na consulta
        filtered_otps = list(enumerate(self.otps_history))
        if query:
            query = query.lower()
            filtered_otps = [
                (index, otp) for index, otp in enumerate(self.otps_history)
                if query in str(otp.get("issuer") or "").lower() or
                query in str(otp.get("account_name") or "").lower()
            ]
        
        # Limpar o viewport
        self.viewport.children = []
        
        # Verificar se há OTPs para mostrar
        if not filtered_otps:
            # Criar uma mensagem de estado vazio
            empty_icon = icons.image("qrcode", widget_name="empty-state-icon", size=34, h_align="center")
            
            empty_description = Label(
                name="empty-state-description",
                label="Scan a QR code or add your first OTP manually",
                h_align="center"
            )
            
            empty_state = Box(
                name="empty-state-container",
                orientation="v",
                spacing=10,
                v_align="center",
                h_align="center",
                h_expand=True,
                v_expand=True,
                children=[
                    empty_icon,
                    empty_description
                ]
            )
            
            self.viewport.add(empty_state)
        else:
            # Adicionar OTPs filtrados
            for original_index, otp in filtered_otps:
                callback = self.bake_otp_slot(otp, index=original_index)
                timer_id = GLib.timeout_add(1000, callback["reload"])
                self.reload_timers.append(timer_id)
                self.viewport.add(callback["button"])

    def on_search_text_changed(self, entry, *_):
        query = entry.get_text()
        # Ignorar se começar com "=" (parece ser algum caso especial no seu código)
        if not query.startswith("="):
            self.arrange_viewport(query)
        
    def resize_viewport(self):
        self.scrolled_window.set_min_content_width(
            self.viewport.get_allocation().width  # type: ignore
        )
        return False

    def bake_otp_slot(self, otp, **kwargs) -> dict:
        index = kwargs["index"]
        
        otp_data = parse_otpauth_uri(otp["qr_data"]) or {}
        try:
            period = int(otp.get("period") or otp_data.get("period") or 30)
        except (TypeError, ValueError):
            period = 30
        issuer = otp.get("issuer") or otp_data.get("issuer") or "OTP"
        
        bars_horizontal = Box(name="otp-slot-bars-h")
        dot_label = Label(name="otp-slot-dot", label="•")

        bar_reload = CircularProgressBar(
            name="otp-slot-reload",
            value=period,
            max_value=period,
            size=28,
            line_width=4,
        )
        box_reload = Box(
            name="otp-slot-reload-box",
            v_align="center",
            h_align="center",
            children=bar_reload
        )

        issuer_label = Label(name="otp-slot-label-issuer", label=issuer)
        code_label = Label(name="otp-slot-label-code", label=str(CodeOTP(otp["qr_data"])))

        code_revealer = Revealer(
            name="otp-slot-label-stack",
            child_revealed=True,
            transition_type="crossfade",
            transition_duration=200,
            h_align="center",
            v_align="center",
            child=code_label
        )

        box_labels = Box(
            name="otp-slot-label-box",
            orientation="h",
            v_align="center",
            h_align="fill",
            h_expand=True,
            spacing=5,
            children=[
                issuer_label,
                dot_label,
                code_revealer
            ]
        )

        # Resto do código permanece o mesmo até reload_otp
        
        button_trash = Button(
            name="otp-slot-button",
            style_classes="trash",
            h_align="center",
            v_align="center",
            child=icons.image("trash_bold", size=20),
            on_clicked=lambda *_: self.otp_delete(index)
        )
        button_trash.connect("enter_notify_event", self.on_button_enter)
        button_trash.connect("leave_notify_event", self.on_button_leave)

        button_otp = Button(
            name="otp-slot-button",
            on_clicked=lambda *_: self.copy_text_to_clipboard(code_label.get_label()),
            child=Box(
                name="otp-slot-box",
                orientation="h",
                h_align="fill",
                h_expand=True,
                children=[
                    box_reload,
                    bars_horizontal,
                    box_labels
                ]
            )
        )
        button_otp.connect("enter_notify_event", self.on_button_enter)
        button_otp.connect("leave_notify_event", self.on_button_leave)
        
        # Função para calcular o tempo restante com base no timestamp atual
        def get_remaining_time():
            current_timestamp = int(time.time())
            # Calcula quanto tempo falta para o próximo intervalo
            elapsed_in_period = current_timestamp % period
            remaining = period - elapsed_in_period
            return remaining
        
        # Inicializa o valor da barra com o tempo restante
        initial_remaining = get_remaining_time()
        bar_reload.value = initial_remaining
        
        # Closure para manter o estado local para cada instância
        def reload_otp():
            remaining = get_remaining_time()
            
            # Atualiza o valor da barra de progresso
            bar_reload.value = remaining
            
            # Se chegou a 0 ou 1, atualiza o código OTP
            if remaining <= 1:
                # Esconder o código atual com animação
                code_revealer.set_reveal_child(False)
                
                # Usar GLib.timeout_add para esperar a transição terminar
                def update_and_show_code():
                    # Atualizar o código OTP
                    new_code = str(CodeOTP(otp["qr_data"]))
                    code_label.set_label(new_code)
                    
                    # Mostrar o novo código com animação
                    code_revealer.set_reveal_child(True)
                    return False
                
                # Esperar para a transição terminar antes de mostrar o novo código
                GLib.timeout_add(250, update_and_show_code)
            
            return True  # Continuar o temporizador

        button = Box(
            name="otp-slot-button2",
            children=Box(
                name="otp-slot-box2",
                orientation="h",
                h_align="center",
                h_expand=True,
                spacing=10,
                children=[
                    button_otp,
                    button_trash
                ]
            )
        )
        
        return {"button": button, "reload": reload_otp}

    def otp_delete(self, index):
        # Carrega os dados atuais do arquivo JSON
        try:
            with open(self.codes_path, "r") as file:
                otps = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            otps = []  # Arquivo não existe ou está vazio/inválido
        
        # Verifica se o índice é válido
        if 0 <= index < len(otps):
            # Remove o OTP com o índice especificado
            removed_otp = otps.pop(index)
            
            # Salva os dados atualizados de volta no arquivo
            with open(self.codes_path, "w") as file:
                json.dump(otps, file, indent=4)
            
            # Atualiza o viewport para refletir a mudança
            self.arrange_viewport()
            
            # Opcional: Mostra uma notificação de confirmação
            exec_shell_command_async('notify-send -a "Mosaic" "OTP Removed" "OTP has been removed successfully."')

    def copy_text_to_clipboard(self, text: str):
        copy_text = text
        try:
            subprocess.run(["xclip", "-selection", "clipboard"], input=copy_text.encode(), check=True)
            exec_shell_command_async('notify-send -a "Mosaic" "OTP Copied" "OTP copied successfully."')
        except subprocess.CalledProcessError as e:
            print(f"Clipboard copy failed: {e}")

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)
