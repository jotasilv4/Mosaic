#!/bin/bash
set -euo pipefail

REPO_URL="https://github.com/jotasilv4/Mosaic.git"
INSTALL_DIR="$HOME/.config/Mosaic"
BOOTSTRAP_PACKAGES=(
    base-devel
    git
)
PACKAGES_YAY=(
    fabric-cli-git
    python-fabric-git
    ttf-tabler-icons
    youtube-music-bin
)
PACKAGES_PACMAN=(
    picom
    unzip
    curl
    i3-wm
    xdg-utils
    matugen
    networkmanager
    bluez
    bluez-utils
    libpulse
    brightnessctl
    gtk3
    gtk2
    glib2
    gdk-pixbuf2
    vte3
    python-gobject
    python-cairo
    python-setproctitle
    python-i3ipc
    python-toml
    python-watchdog
    python-pillow
    python-ijson
    python-pyotp
    python-loguru
    python-pip
    noto-fonts-emoji
    libnotify
    playerctl
    alacritty
    xclip
    slop
    maim
    feh
    zbar
    hyprpicker
    gpu-screen-recorder
    tesseract
    tesseract-data-eng
    tesseract-data-por
    wl-clipboard
    fontconfig
)
PIP_PACKAGES=(
    pyzbar
)
REQUIRED_COMMANDS=(
    i3
    picom
    matugen
    playerctl
    nmcli
    bluetoothctl
    pactl
    brightnessctl
    xclip
    slop
    maim
    notify-send
    fc-cache
)
PYTHON_MODULES=(
    fabric
    gi
    PIL
    pyotp
    pyzbar
    i3ipc
    setproctitle
    toml
    watchdog
    ijson
    loguru
    cairo
)

# Evita executar como root
if [ "$(id -u)" -eq 0 ]; then
    echo "Por favor, não execute este script como root"
    exit 1
fi

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local answer

    if [ ! -t 0 ]; then
        [[ "$default" =~ ^[sSyY]$ ]]
        return
    fi

    read -r -p "$prompt" answer || answer="$default"
    answer="${answer:-$default}"
    [[ "$answer" =~ ^[sSyY]$ ]]
}

install_bootstrap_deps() {
    local missing_pkgs=()
    for pkg in "${BOOTSTRAP_PACKAGES[@]}"; do
        if ! pacman -Qi "$pkg" &>/dev/null; then
            missing_pkgs+=("$pkg")
        fi
    done

    if [ ${#missing_pkgs[@]} -gt 0 ]; then
        echo "Instalando dependências base: ${missing_pkgs[*]}"
        sudo pacman -S --needed --noconfirm "${missing_pkgs[@]}"
    fi
}

install_bootstrap_deps

aur_helper=""
if command -v yay &>/dev/null; then
    aur_helper="yay"
    echo $aur_helper
elif command -v paru &>/dev/null; then
    aur_helper="paru"
    echo $aur_helper
else
    echo "Installing yay-bin..."
    tmpdir=$(mktemp -d)
    git clone https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
    cd "$tmpdir/yay-bin"
    makepkg -si --noconfirm
    cd - > /dev/null
    rm -rf "$tmpdir"
    aur_helper="yay"
fi

# Função para verificar e instalar pacotes do pacman
install_pacman_deps() {
    local missing_pkgs=()
    for pkg in "${PACKAGES_PACMAN[@]}"; do
        if ! pacman -Qi "$pkg" &>/dev/null; then
            missing_pkgs+=("$pkg")
        fi
    done

    if [ ${#missing_pkgs[@]} -eq 0 ]; then
        echo "Todas as dependências do pacman já estão instaladas."
    else
        echo "Instalando dependências ausentes do pacman: ${missing_pkgs[*]}"
        sudo pacman -S --needed --noconfirm "${missing_pkgs[@]}"
    fi
}

# Função para verificar e instalar pacotes do AUR
install_aur_deps() {
    local missing_pkgs=()
    for pkg in "${PACKAGES_YAY[@]}"; do
        if ! $aur_helper -Qi "$pkg" &>/dev/null; then
            missing_pkgs+=("$pkg")
        fi
    done

    if [ ${#missing_pkgs[@]} -eq 0 ]; then
        echo "Todas as dependências do AUR já estão instaladas."
    else
        echo "Instalando dependências ausentes do AUR: ${missing_pkgs[*]}"
        $aur_helper -S --needed --noconfirm "${missing_pkgs[@]}"
    fi
}

install_pip_fallbacks() {
    local missing_pkgs=()
    for pkg in "${PIP_PACKAGES[@]}"; do
        if ! python - "$pkg" <<'PY' &>/dev/null
import importlib
import sys

importlib.import_module(sys.argv[1])
PY
        then
            missing_pkgs+=("$pkg")
        fi
    done

    if [ ${#missing_pkgs[@]} -gt 0 ]; then
        echo "Instalando módulos Python via pip --user: ${missing_pkgs[*]}"
        python -m pip install --user --break-system-packages "${missing_pkgs[@]}"
    fi
}

enable_core_services() {
    if prompt_yes_no "Ativar NetworkManager e Bluetooth agora? (S/n): " "s"; then
        sudo systemctl enable --now NetworkManager.service 2>/dev/null || true
        sudo systemctl enable --now bluetooth.service 2>/dev/null || true
        echo "Serviços principais ativados."
    else
        echo "Pulando ativação automática de serviços."
    fi
}

verify_runtime_deps() {
    local missing_commands=()
    for cmd in "${REQUIRED_COMMANDS[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -gt 0 ]; then
        echo "Aviso: comandos ainda ausentes: ${missing_commands[*]}"
    else
        echo "Comandos essenciais encontrados."
    fi

    python - "${PYTHON_MODULES[@]}" <<'PY'
import importlib
import sys

missing = []
for module in sys.argv[1:]:
    try:
        importlib.import_module(module)
    except Exception:
        missing.append(module)

if missing:
    print("Aviso: módulos Python ainda ausentes: " + ", ".join(missing))
else:
    print("Módulos Python essenciais encontrados.")
PY
}

# Clone or update the repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating Mosaic..."
    git -C "$INSTALL_DIR" pull --ff-only || echo "Não foi possível atualizar automaticamente; mantendo arquivos locais."
elif [ -d "$INSTALL_DIR" ]; then
    echo "$INSTALL_DIR já existe, mas não parece ser um repositório git. Mantendo diretório atual."
else
    echo "Cloning Mosaic..."
    git clone --depth=1 "$REPO_URL" "$INSTALL_DIR" -b dev
fi

# Primeira tentativa de instalação
echo "Iniciando instalação das dependências..."
install_pacman_deps
install_aur_deps
install_pip_fallbacks
enable_core_services

# Verificação e tentativa de correção
echo "Verificando integridade das dependências..."
install_pacman_deps
install_aur_deps
install_pip_fallbacks

# Instala o gray-git (caso especial)
if ! $aur_helper -Qi gray-git &>/dev/null; then
    echo "Instalando gray-git..."
    yes | $aur_helper -S --needed --confirm gray-git || true
fi
verify_runtime_deps

echo "Installing required fonts..."

FONT_URL="https://github.com/zed-industries/zed-fonts/releases/download/1.2.0/zed-sans-1.2.0.zip"
FONT_DIR="$HOME/.fonts/zed-sans"
TEMP_ZIP="/tmp/zed-sans-1.2.0.zip"

# Check if fonts are already installed
if [ ! -d "$FONT_DIR" ]; then
    echo "Downloading fonts from $FONT_URL..."
    curl -L -o "$TEMP_ZIP" "$FONT_URL"

    echo "Extracting fonts to $FONT_DIR..."
    mkdir -p "$FONT_DIR"
    unzip -o "$TEMP_ZIP" -d "$FONT_DIR"

    echo "Cleaning up..."
    rm "$TEMP_ZIP"
else
    echo "Fonts are already installed. Skipping download and extraction."
fi

# Copy local fonts if not already present
if [ ! -d "$HOME/.fonts/tabler-icons" ]; then
    echo "Copying local fonts to $HOME/.fonts/tabler-icons..."
    mkdir -p "$HOME/.fonts/tabler-icons"
    cp -r "$INSTALL_DIR/assets/fonts/"* "$HOME/.fonts/tabler-icons"
else
    echo "Local fonts are already installed. Skipping copy."
fi

echo "Updating font cache..."
fc-cache -f "$HOME/.fonts" >/dev/null 2>&1 || true

# Configuração para XFCE (opcional, se detectado)
if command -v xfconf-query &>/dev/null; then
    echo "Detectado XFCE. Aplicando configurações de sessão..."
    
    # Tenta desativar xfwm4 e xfce4-panel na sessão Failsafe
    xfconf-query -c xfce4-session -p /sessions/Failsafe/Client0_Command -t string -s "i3" -a 2>/dev/null || true
    xfconf-query -c xfce4-session -p /sessions/Failsafe/Client1_Command -t string -s "" -a 2>/dev/null || true
    
    # Cria arquivos de autostart para garantir que i3, nitrogen e picom iniciem com o XFCE
    mkdir -p "$HOME/.config/autostart"
    
    # Desativa o painel do XFCE via autostart (redundância)
    cat <<EOF > "$HOME/.config/autostart/xfce4-panel.desktop"
[Desktop Entry]
Type=Application
Name=XFCE Panel (Disabled)
Exec=true
Hidden=true
NoDisplay=true
EOF

    # Opcional: desativa o daemon de notificacoes do XFCE para evitar conflito com Mosaic
    if prompt_yes_no "Desativar xfce4-notifyd para usar notificacoes do Mosaic? (s/n): " "n"; then
        cat <<EOF > "$HOME/.config/autostart/xfce4-notifyd.desktop"
[Desktop Entry]
Type=Application
Name=XFCE Notify Daemon (Disabled)
Exec=true
Hidden=true
NoDisplay=true
EOF
        pkill xfce4-notifyd 2>/dev/null || true
        echo "xfce4-notifyd desativado para evitar conflito com Mosaic."
    else
        echo "Mantendo xfce4-notifyd ativo."
    fi

    # Adiciona i3 ao Autostart
    cat <<EOF > "$HOME/.config/autostart/i3.desktop"
[Desktop Entry]
Type=Application
Name=i3 Window Manager
Exec=i3
OnlyShowIn=XFCE;
RunHook=0
EOF

    # Adiciona Picom ao Autostart
    cat <<EOF > "$HOME/.config/autostart/picom.desktop"
[Desktop Entry]
Type=Application
Name=Picom
Exec=picom -b --config $HOME/.config/Mosaic/config/components/picom/picom.conf
OnlyShowIn=XFCE;
RunHook=0
EOF

    echo "Configurações de sessão do XFCE concluídas."
fi

if [ -f "$INSTALL_DIR/config/components/systemboot" ]; then
    chmod +x "$INSTALL_DIR/config/components/systemboot"
fi
if [ -d "$INSTALL_DIR/scripts" ]; then
    chmod +x "$INSTALL_DIR"/scripts/*.sh 2>/dev/null || true
fi
mkdir -p "$HOME/.config/i3"
mkdir -p "$HOME/.config/alacritty" && cp "$HOME/.config/Mosaic/config/components/alacritty/alacritty.toml" "$HOME/.config/alacritty/alacritty.toml"

python "$INSTALL_DIR/config/config.py" --generate

echo "Starting Mosaic..."
killall mosaic 2>/dev/null || true
#python "$INSTALL_DIR/main.py" > /dev/null &

echo "Please execute this key combination Super+Shift+R"

echo "Installation complete."

# Pergunta se deseja reiniciar o sistema
if prompt_yes_no "Deseja reiniciar o sistema agora? (s/n): " "n"; then
    echo "Reiniciando o sistema..."
    sudo reboot
else
    echo "Instalação finalizada. Lembre-se de reiniciar manualmente depois."
fi
