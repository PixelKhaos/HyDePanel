#!/bin/bash
# shellcheck source=/dev/null

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error
set -o pipefail  # Prevent errors in a pipeline from being masked

INSTALL_DIR="$HOME/.config/hydepanel"
WRAPPER_PATH="/usr/local/bin/hydepanel"
PID_FILE="$INSTALL_DIR/hydepanel.pid"

mkdir -p "$INSTALL_DIR"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🖥 System Checks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if ! grep -q "arch" /etc/os-release; then
	echo "This script is designed to run on Arch Linux."
	exit 1
fi

if ! command -v sudo &> /dev/null; then
    echo -e "\e[31mError: sudo is required but not installed. Cannot proceed.\e[0m"
    exit 1
fi

if ! command -v gum &> /dev/null; then
    echo -e "\e[1;34mInstalling gum for interactive selection...\e[0m"
    sudo pacman -S --noconfirm --needed gum
fi

# Ensure AUR helper exists
if command -v yay &> /dev/null; then
    AUR_HELPER="yay"
elif command -v paru &> /dev/null; then
    AUR_HELPER="paru"
else
    echo -e "\e[31mError: No AUR helper (yay/paru) found. Please install one manually.\e[0m"
    exit 1
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 Display ASCII Header
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
clear
echo -e "\e[1;36m"
cat << "EOF"

 __ __  __ __  ___      ___  ____   ____  ____     ___  _
|  |  ||  |  ||   \    /  _]|    \ /    ||    \   /  _]| |
|  |  ||  |  ||    \  /  [_ |  o  )  o  ||  _  | /  [_ | |
|  _  ||  ~  ||  D  ||    _]|   _/|     ||  |  ||    _]| |___
|  |  ||___, ||     ||   [_ |  |  |  _  ||  |  ||   [_ |     |
|  |  ||     ||     ||     ||  |  |  |  ||  |  ||     ||     |
|__|__||____/ |_____||_____||__|  |__|__||__|__||_____||_____|
EOF
echo -e "\e[1;36m  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ━━━━ ━━ ━\e[0m"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 Global Package Lists
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# TODO: clean up what's actually required and not, and leverage the optional packages better

REQUIRED_PKGS_PACMAN=(
    pipewire playerctl dart-sass power-profiles-daemon networkmanager brightnessctl
    pkgconf wf-recorder kitty python pacman-contrib gtk3 cairo gtk-layer-shell libgirepository
    gobject-introspection gobject-introspection-runtime python-pip python-gobject python-psutil
    python-dbus python-cairo python-loguru python-setproctitle
)

REQUIRED_PKGS_AUR=(
    gray-git python-fabric gnome-bluetooth-3.0 python-rlottie-python python-pytomlpp slurp
    imagemagick tesseract tesseract-data-eng
)

OPTIONAL_PKGS=(
    "pacman-contrib:Check for updates using pacman"
    "cava:Audio visualizer in media module"
    "power-profiles-daemon:Power profile switching"
    "wf-recorder:Screen recording (with slurp)"
    "slurp:Screen region selection"
    "hyprsunset:Hyprland’s native blue light filter"
    "hypridle:Hyprland’s native idle inhibitor"
    "playerctl:Media controls in quick settings"
    "tesseract:OCR engine for text recognition"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 Check Installed Packages with Loading Spinner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

check_installed() {
    local package=$1
    if pacman -Q "$package" &>/dev/null || $AUR_HELPER -Q "$package" &>/dev/null; then
        echo "$package"
    fi
}

gum spin --spinner dot --title "Checking for installed packages..." -- sleep 1

installed_packages=()
mapfile -t installed_packages < <(
    for pkg in "${OPTIONAL_PKGS[@]}"; do
        PACKAGE_NAME=$(echo "$pkg" | awk -F: "{print \$1}")
        if pacman -Q "$PACKAGE_NAME" &>/dev/null || '"$AUR_HELPER"' -Q "$PACKAGE_NAME" &>/dev/null; then
            echo "$PACKAGE_NAME"
        fi
    done
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 Full Install Function (With Uninstall Option)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

full_install() {
	gum style --foreground 10 --border-foreground 10 --border rounded --align left \
	--width 60 --margin "0 0" --padding "0 1" "HydePanel Installer - Optional Packages"

    OPTIONS=()
    SELECTED_FLAGS=()

    for item in "${OPTIONAL_PKGS[@]}"; do
        PACKAGE_NAME=$(echo "$item" | awk -F: '{print $1}')
        OPTIONS+=("$PACKAGE_NAME")
        if [[ " ${installed_packages[*]} " =~ " $PACKAGE_NAME " ]]; then
            SELECTED_FLAGS+=(--selected "$PACKAGE_NAME")
        fi
    done

    SELECTED=$(printf "%s\n" "${OPTIONS[@]}" | gum choose  --cursor.foreground "#edbbbb" --item.foreground "#888896" --selected.foreground "#edbbbb" \
    --cursor-prefix "[•] " --selected-prefix "[✓] " --unselected-prefix "[×] " \
     --header "Toggle selection (deselect to uninstall)" --no-limit "${SELECTED_FLAGS[@]}")
    clear

    # Ensure SELECTED is not unbound
    SELECTED=${SELECTED:-""}

    # Identify removed packages
    REMOVED_PKGS=()
    for pkg in "${installed_packages[@]}"; do
        if ! echo "$SELECTED" | grep -q "$pkg"; then
            REMOVED_PKGS+=("$pkg")
        fi
    done

    # Confirm removal
    if [ ${#REMOVED_PKGS[@]} -gt 0 ]; then
        gum style --border rounded --border-foreground 9 --margin "1 0" --padding "1 2" "⚠ Some previously installed packages are not selected."
        if gum confirm "Do you want to remove them?" --selected.foreground "#111" --selected.background "#edbbbb" --unselected.background "#888896" --prompt.foreground "#edbbbb"; then
            echo "${REMOVED_PKGS[@]}" | xargs $AUR_HELPER -Rns
        fi
    fi

	# TODO: Add optional sub-dependencies, i.e language packs for OCR (tesseract)
    # So if tesseract is selected for example, install user gets another prompt to select language packs

    # Install required packages
    clear
    gum style --foreground 10 --border-foreground 10 --border rounded \
    --margin "1 0" --padding "1 2" "Installing HydePanel packages"

    quick_install

    # Install selected optional packages
	if [ -n "$SELECTED" ]; then
		gum spin --spinner dot --title "📦 Installing selected optional packages..." -- sleep 2


		# Run installation **without --noconfirm** so the user is prompted for conflicts
        # maybe add somehow filter out packages that are already installed and up-to-date?
		if ! $AUR_HELPER -S --needed $SELECTED; then
			echo -e "\e[31m⚠ Package installation encountered an issue. Please check above.\e[0m"
			exit 1
		fi

		echo -e "\e[32m✔ Packages installed.\e[0m"
	fi

}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 Quick Install Function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

quick_install() {

    gum spin --spinner dot --title "Checking system for missing dependencies..." -- sleep 1
        MISSING_PKGS=()
        for pkg in "${REQUIRED_PKGS_PACMAN[@]}"; do
            if ! pacman -Q "$pkg" &>/dev/null; then
                MISSING_PKGS+=("$pkg")
            fi
        done

        #install missing packages from aur
        MISSING_AUR_PKGS=()
        for pkg in "${REQUIRED_PKGS_AUR[@]}"; do
            if ! $AUR_HELPER -Q "$pkg" &>/dev/null; then
                MISSING_AUR_PKGS+=("$pkg")
            fi
        done


    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo -e "\e[33m⚠ Installing missing required packages from pacman...\e[0m"
        sudo pacman -S --noconfirm --needed "${MISSING_PKGS[@]}" &>/dev/null
        echo -e "\e[32m✔ Required pacman packages installed successfully.\e[0m"
    else
        echo -e "\e[32m✔ All required pacman packages are already installed.\e[0m"
    fi

    if [ ${#MISSING_AUR_PKGS[@]} -gt 0 ]; then
        echo -e "\e[33m⚠ Installing missing required packages from AUR...\e[0m"
        $AUR_HELPER -S --needed --noconfirm "${MISSING_AUR_PKGS[@]}" &>/dev/null
        echo -e "\e[32m✔ Required AUR packages installed successfully.\e[0m"
    else
        echo -e "\e[32m✔ All required AUR packages are already installed.\e[0m"
    fi
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛠 Run Install
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_packages() {
    MODE=$(gum choose --cursor.foreground "#111" --cursor.background "#edbbbb" \
        --item.foreground "#edbbbb" \
     --header "📦 Select Install Mode" "Quick Install" "Full/Edit Install" "Cancel")
    clear

    case $MODE in
        "Quick Install") quick_install ;;
        "Full/Edit Install") full_install ;;
        "Cancel") exit 0 ;;
    esac
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✨ Final Steps & Instructions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

finish_install() {
    clear

    gum style \
        --foreground 10 --border-foreground 10 --border rounded \
        --align center --width 60 --margin "1 0" --padding "1 2" \
        "✅ HydePanel Installation Complete!" "Run 'hydepanel start' to launch."
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛠 Create CLI Wrapper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
create_wrapper() {
    sudo bash -c "cat > $WRAPPER_PATH << 'EOF'
#!/bin/bash
INSTALL_DIR=\"$HOME/.config/hydepanel\"
PID_FILE=\"\$INSTALL_DIR/hydepanel.pid\"

case \"\$1\" in
    start)
        bash \"$INSTALL_DIR/init.sh\" -start
        ;;
    stop)
        if [ -f \"\$PID_FILE\" ]; then
            PID=\$(cat \"\$PID_FILE\")
            echo \"Stopping HydePanel (PID: \$PID)...\"
            kill \"\$PID\" && rm -f \"\$PID_FILE\"
        else
            echo \"HydePanel is not running.\"
        fi
        ;;
    restart)
        bash \"$INSTALL_DIR/init.sh\" -stop
        bash \"$INSTALL_DIR/init.sh\" -start & disown
        ;;
    install)
        bash \"$INSTALL_DIR/init.sh\" -install
        ;;
    update)
        git -C \"$INSTALL_DIR\" pull
        ;;
    status)
        if [ -f \"\$PID_FILE\" ]; then
            echo \"HydePanel is running (PID: \$(cat \"\$PID_FILE\"))\"
        else
            echo \"HydePanel is not running.\"
        fi
        ;;
    *)
        echo \"Usage: hydepanel {start|stop|restart|install|status}\"
        ;;
esac
EOF"
    sudo chmod +x "$WRAPPER_PATH"
}



case "$1" in
    -start)
        cd "$INSTALL_DIR" || {
            echo -e "\033[31mError: Directory $INSTALL_DIR does not exist.\033[0m\n"
            exit 1
        }

        VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "Unknown Version")

        # Check if the virtual environment exists, if not, create it
        if [ ! -d .venv ]; then
            echo -e "\033[32m  venv does not exist. Creating venv...\033[0m\n"
            python3 -m venv .venv

            if [ $? -ne 0 ]; then
                echo -e "\033[31m  Failed to create virtual environment. Exiting...\033[0m\n"
                exit 1
            fi

            source .venv/bin/activate

            if [ $? -ne 0 ]; then
                echo -e "\033[31m  Failed to activate venv. Exiting...\033[0m\n"
                exit 1
            fi

            echo -e "\033[32m  Installing python dependencies, brace yourself.\033[0m\n"
            pip install -r requirements.txt

            if [ $? -ne 0 ]; then
                echo -e "\033[31mFailed to install packages from requirements.txt. Exiting...\033[0m\n"
                exit 1
            fi
            echo -e "\033[32m  All done, starting bar.\033[0m\n"
        else
            echo -e "\033[32m  Using existing venv.\033[0m\n"
            source .venv/bin/activate
        fi

        echo -e "\e[32mUsing python:\e[0m \e[34m$(which python)\e[0m\n"

        # Start the application in the background and store the PID
        python3 main.py & echo $! > "$INSTALL_DIR/hydepanel.pid"

        echo -e "\033[32mHydePanel started with PID: $(cat "$INSTALL_DIR/hydepanel.pid")\033[0m\n"
        ;;


    -install)
        install_packages
        create_wrapper
		finish_install
        ;;
    -update)
        # git pull origin
        ;;
    *)
        echo -e "\033[31mUnknown command. Use \033[32m'-start'\033[33m, \033[32m'-install'\033[33m, \033[32m'-update'\033[31m.\033[0m\n"
        exit 1
        ;;
esac
