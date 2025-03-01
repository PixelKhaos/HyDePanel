import datetime
import os
import re
import shutil
import subprocess
from typing import Dict, List, Literal

import psutil
from fabric.utils import (
    cooldown,
    exec_shell_command,
    exec_shell_command_async,
    get_relative_path,
)
from gi.repository import Gdk, GLib, Gtk
from loguru import logger

from utils.thread import run_in_thread

from .colors import Colors
from .constants import named_colors
from .icons import distro_text_icons


# Function to escape the markup
def parse_markup(text):
    return text


# support for multiple monitors
def for_monitors(widget):
    n = Gdk.Display.get_default().get_n_monitors() if Gdk.Display.get_default() else 1
    return [widget(i) for i in range(n)]


@run_in_thread
def copy_theme(theme: str):
    destination_file = get_relative_path("../styles/theme.scss")
    source_file = get_relative_path(f"../styles/themes/{theme}.scss")

    if not os.path.exists(source_file):
        logger.warning(
            f"{Colors.WARNING}Warning: The theme file '{theme}.scss' was not found. Using default theme."  # noqa: E501
        )
        source_file = get_relative_path("../styles/themes/catpuccin-mocha.scss")

    try:
        shutil.copyfile(source_file, destination_file)

    except FileNotFoundError:
        logger.error(
            f"{Colors.ERROR}Error: The theme file '{source_file}' was not found."
        )
        exit(1)


# Function to convert celsius to fahrenheit
def celsius_to_fahrenheit(celsius):
    fahrenheit = (celsius * 9 / 5) + 32
    return fahrenheit


# Merge the parsed data with the default configuration
def merge_defaults(data: dict, defaults: dict):
    return {**defaults, **data}


# Validate the widgets
def validate_widgets(parsed_data, default_config):
    """Validates the widgets defined in the layout configuration.

    Args:
        parsed_data (dict): The parsed configuration data
        default_config (dict): The default configuration data

    Raises:
        ValueError: If an invalid widget is found in the layout
    """
    layout = parsed_data["layout"]
    for section in layout:
        for widget in layout[section]:
            if widget.startswith("@group:"):
                # Handle module groups
                group_idx = widget.replace("@group:", "", 1)
                if not group_idx.isdigit():
                    raise ValueError(
                        "Invalid module group index "
                        f"'{group_idx}' in section {section}. Must be a number."
                    )
                idx = int(group_idx)
                groups = parsed_data.get("module_groups", [])
                if not isinstance(groups, list):
                    raise ValueError(
                        "module_groups must be an array when using @group references"
                    )
                if not (0 <= idx < len(groups)):
                    raise ValueError(
                        "Module group index "
                        f"{idx} is out of range. Available indices: 0-{len(groups) - 1}"
                    )
                # Validate widgets inside the group
                group = groups[idx]
                if not isinstance(group, dict) or "widgets" not in group:
                    raise ValueError(
                        f"Invalid module group at index {idx}. "
                        "Must be an object with 'widgets' array."
                    )
                for group_widget in group["widgets"]:
                    if group_widget not in default_config:
                        raise ValueError(
                            f"Invalid widget '{group_widget}' found in "
                            f"module group {idx}. Please check the widget name."
                        )
            elif widget not in default_config:
                raise ValueError(
                    f"Invalid widget '{widget}' found in section {section}. "
                    "Please check the widget name."
                )


# Function to exclude keys from a dictionary        )
def exclude_keys(d: Dict, keys_to_exclude: List[str]) -> Dict:
    return {k: v for k, v in d.items() if k not in keys_to_exclude}


# Function to format time in hours and minutes
def format_time(secs: int):
    mm, _ = divmod(secs, 60)
    hh, mm = divmod(mm, 60)
    return "%d h %02d min" % (hh, mm)


# Function to convert bytes to kilobytes, megabytes, or gigabytes
def convert_bytes(bytes: int, to: Literal["kb", "mb", "gb"], format_spec=".1f"):
    multiplier = 1

    if to == "mb":
        multiplier = 2
    elif to == "gb":
        multiplier = 3

    return f"{format(bytes / (1024**multiplier), format_spec)}{to.upper()}"


# Function to get the system uptime
def uptime():
    boot_time = psutil.boot_time()
    now = datetime.datetime.now()

    diff = now.timestamp() - boot_time

    # Convert the difference in seconds to hours and minutes
    hours, remainder = divmod(diff, 3600)
    minutes, _ = divmod(remainder, 60)

    return f"{int(hours):02}:{int(minutes):02}"


# Function to convert seconds to milliseconds
def convert_seconds_to_milliseconds(seconds: int):
    return seconds * 1000


# Function to check if an icon exists, otherwise use a fallback icon
def check_icon_exists(icon_name: str, fallback_icon: str) -> str:
    if Gtk.IconTheme.get_default().has_icon(icon_name):
        return icon_name
    return fallback_icon


# Function to play sound
@cooldown(1)
@run_in_thread
def play_sound(file: str):
    exec_shell_command_async(f"pw-play {file}", None)


def handle_power_action(operation: str):
    match operation:
        case "shutdown":
            exec_shell_command_async("systemctl poweroff")
        case "reboot":
            exec_shell_command_async("systemctl reboot")
        case "hibernate":
            exec_shell_command_async("systemctl hibernate")
        case "suspend":
            exec_shell_command_async("systemctl suspend")
        case "lock":
            exec_shell_command_async("loginctl lock-session")
        case "logout":
            exec_shell_command_async("loginctl terminate-user $USER")
    return True


# Function to get the distro icon
def get_distro_icon():
    distro_id = GLib.get_os_info("ID")

    # Search for the icon in the list
    return distro_text_icons.get(distro_id, "")


# Function to check if an executable exists
def executable_exists(executable_name):
    executable_path = shutil.which(executable_name)
    return bool(executable_path)


def send_notification(
    title: str,
    body: str,
    urgency: Literal["low", "normal", "critical"],
    icon=None,
    app_name="Application",
    timeout=None,
):
    """
    Sends a notification using the notify-send command.
    :param title: The title of the notification
    :param body: The message body of the notification
    :param urgency: The urgency of the notification ('low', 'normal', 'critical')
    :param icon: Optional icon for the notification
    :param app_name: The application name that is sending the notification
    :param timeout: Optional timeout in milliseconds (e.g., 5000 for 5 seconds)
    """
    # Base command
    command = [
        "notify-send",
        "--urgency",
        urgency,
        "--app-name",
        app_name,
        title,
        body,
    ]

    # Add icon if provided
    if icon:
        command.extend(["--icon", icon])

    if timeout is not None:
        command.extend(["-t", str(timeout)])

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to send notification: {e}")


# Function to get the relative time
def get_relative_time(mins: int) -> str:
    # Seconds
    if mins == 0:
        return "now"

    # Minutes
    if mins < 60:
        return f"{mins} minute{'s' if mins > 1 else ''} ago"

    # Hours
    if mins < 1440:
        hours = mins // 60
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    # Days
    days = mins // 1440
    return f"{days} day{'s' if days > 1 else ''} ago"


# Function to get the percentage of a value
def convert_to_percent(
    current: int | float, max: int | float, is_int=True
) -> int | float:
    if is_int:
        return int((current / max) * 100)
    else:
        return (current / max) * 100


# Function to ensure the directory exists
@run_in_thread
def ensure_dir_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


# Function to unique list
def unique_list(lst) -> List:
    return list(set(lst))


# Function to check if an app is running
def is_app_running(app_name: str) -> bool:
    return len(exec_shell_command(f"pidof {app_name}")) != 0


# Function to check if a color is valid
def is_valid_gjs_color(color: str) -> bool:
    color_lower = color.strip().lower()

    if color_lower in named_colors:
        return True

    hex_color_regex = r"^#(?:[a-fA-F0-9]{3,4}|[a-fA-F0-9]{6,8})$"
    rgb_regex = r"^rgb\(\s*(\d{1,3}%?\s*,\s*){2}\d{1,3}%?\s*\)$"
    rgba_regex = r"^rgba\(\s*(\d{1,3}%?\s*,\s*){3}(0|1|0?\.\d+)\s*\)$"

    if re.match(hex_color_regex, color):
        return True

    return bool(re.match(rgb_regex, color_lower) or re.match(rgba_regex, color_lower))
