import psutil
from fabric import Application
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.system_tray.widgets import SystemTray
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Language, ActiveWindow, Workspaces, WorkspaceButton
from fabric.utils import (
    FormattedString,
    bulk_replace,
    invoke_repeater,
    get_relative_path,
)

from utils import read_config
from widgets.battery import BatteryLabel
from widgets.paneltoggle import CommandSwitcher
from widgets.volume import AUDIO_WIDGET, VolumeWidget

config = read_config()


class StatusBar(Window):
    def __init__(
        self,
    ):
        super().__init__(
            name="bar",
            layer="top",
            anchor="left top right",
            margin="10px 10px -2px 10px",
            exclusivity="auto",
            visible=False,
            all_visible=False,
        )
        self.workspaces = Workspaces(
            name="workspaces",
            spacing=4,
            buttons=[WorkspaceButton(id=i, label=str(i)) for i in range(1, 11)],
            buttons_factory=lambda ws_id: WorkspaceButton(id=ws_id, label=str(ws_id)),
        )
        self.active_window = ActiveWindow(name="hyprland-window")
        self.language = Language(
            formatter=FormattedString(
                "{replace_lang(language)}",
                replace_lang=lambda lang: bulk_replace(
                    lang,
                    (r".*Eng.*", r".*Ar.*"),
                    ("ENG", "ARA"),
                    regex=True,
                ),
            ),
            name="hyprland-window",
        )
        self.date_time = DateTime(name="date-time")
        self.system_tray = SystemTray(name="system-tray", spacing=4)

        self.ram_progress_bar = CircularProgressBar(
            name="ram-progress-bar", pie=True, size=24, tooltip_text="ram"
        )

        hypersunset_config = config["hyprsunset"]
        hyperidle_config = config["hypridle"]
        battery_config = config["battery"]

        self.hyprsunset = CommandSwitcher(
            "hyprsunset -t 2800k",
            hypersunset_config["enabled_icon"],
            hypersunset_config["disabled_icon"],
            hypersunset_config["enable_label"],
            hypersunset_config["enable_tooltip"],
        )
        self.hypridle = CommandSwitcher(
            "hypridle",
            hyperidle_config["enabled_icon"],
            hyperidle_config["disabled_icon"],
            hyperidle_config["enable_label"],
            hyperidle_config["enable_tooltip"],
        )

        self.cpu_progress_bar = CircularProgressBar(
            name="cpu-progress-bar", pie=True, size=24, tooltip_text="cpu"
        )
        self.progress_bars_overlay = Overlay(
            child=self.ram_progress_bar,
            overlays=[
                self.cpu_progress_bar,
                Label("", style="margin: 0px 6px 0px 0px; font-size: 12px"),
            ],
        )

        self.status_container = Box(
            name="widgets-container",
            spacing=4,
            orientation="h",
            children=self.progress_bars_overlay,
        )
        self.status_container.add(VolumeWidget()) if AUDIO_WIDGET is True else None

        self.battery = BatteryLabel(
            battery_config["enable_label"],
            battery_config["enable_tooltip"],
        )

        self.children = CenterBox(
            name="bar-inner",
            start_children=Box(
                name="start-container",
                spacing=4,
                orientation="h",
                children=[
                    self.workspaces,
                    self.active_window,
                ],
            ),
            center_children=Box(
                name="center-container",
                spacing=4,
                orientation="h",
                children=self.date_time,
            ),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h",
                children=[
                    self.battery,
                    self.hypridle,
                    self.hyprsunset,
                    self.status_container,
                    self.system_tray,
                ],
            ),
        )

        invoke_repeater(1000, self.update_progress_bars)

        self.show_all()

    def update_progress_bars(self):
        self.ram_progress_bar.value = psutil.virtual_memory().percent / 100
        self.cpu_progress_bar.value = psutil.cpu_percent() / 100
        return True


if __name__ == "__main__":
    bar = StatusBar()
    app = Application("bar", bar)
    app.set_stylesheet_from_file(get_relative_path("main.css"))

    app.run()
