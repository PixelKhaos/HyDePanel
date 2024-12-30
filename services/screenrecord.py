import datetime
import subprocess

from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command, exec_shell_command_async
from gi.repository import Gio, GLib
from loguru import logger

import utils.functions as helpers
from utils.widget_config import BarConfig


class ScreenRecorder(Service):
    """Service to handle screen recording and screenshots"""

    @Signal
    def recording(self, value: bool) -> None: ...

    def __init__(self, widget_config: BarConfig, **kwargs):
        if not helpers.executable_exists("wf-recorder"):
            raise helpers.ExecutableNotFoundError("wf-recorder")

        self.config = widget_config["recorder"]
        self.screenshot_path = f"{GLib.get_home_dir()}/{self.config["photos"]}"
        self.screenrecord_path = f"{GLib.get_home_dir()}/{self.config["videos"]}"

        helpers.ensure_dir_exists(self.screenshot_path)
        helpers.ensure_dir_exists(self.screenrecord_path)

        super().__init__(**kwargs)

    def screenshot(self, fullscreen=False, save_copy=True):
        time = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = f"{self.screenshot_path}/{time}.png"
        command = (
            ["grimblast", "copysave", "screen", file_path]
            if save_copy
            else ["grimblast", "copy" "screen"]
        )
        if not fullscreen:
            command[2] = "area"
        try:
            subprocess.run(command, check=True)
            self.send_screenshot_notification(
                file_path=file_path if file_path else None,
            )
        except Exception:
            logger.error(f"[SCREENSHOT] Failed to run command: {command}")

    def screencast_start(self, fullscreen=False):
        if self.is_recording:
            logger.error(
                "[SCREENRECORD] Another instance of wf-recorder is already running"
            )
            return
        time = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = f"{self.screenrecord_path}/{time}.mp4"

        self._current_screencast_path = file_path
        area = "" if fullscreen else f"-g '{exec_shell_command('slurp')}'"
        command = f"wf-recorder --file={file_path} --pixel-format yuv420p {area}"
        exec_shell_command_async(command)
        self.emit("recording", True)

    def screencast_stop(self):
        exec_shell_command_async("killall -INT wf-recorder")
        self.emit("recording", False)
        self.send_screencast_notification(self._current_screencast_path)

    def send_screencast_notification(self, file_path):
        cmd = ["notify-send"]
        cmd.extend(
            [
                "-A",
                "files=Show in Files",
                "-A",
                "view=View",
                "-i",
                "camera-video-symbolic",
                "-a",
                "HyDePanel Screenshot Utility",
                "Screencast Saved",
                f"Saved Screencast at {file_path}",
            ]
        )

        proc: Gio.Subprocess = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE)

        def do_callback(process: Gio.Subprocess, task: Gio.Task):
            try:
                _, stdout, stderr = process.communicate_utf8_finish(task)
            except Exception:
                logger.error(
                    f"[SCREENCAST] Failed read notification action with error {stderr}"
                )
                return

            match stdout.strip("\n"):
                case "files":
                    exec_shell_command_async(f"xdg-open {self.screenrecord_path}")
                case "view":
                    exec_shell_command_async(f"xdg-open {file_path}")

        proc.communicate_utf8_async(None, None, do_callback)

    def send_screenshot_notification(self, file_path=None):
        cmd = ["notify-send"]
        cmd.extend(
            [
                "-A",
                "files=Show in Files",
                "-A",
                "view=View",
                "-A",
                "edit=Edit",
                "-i",
                "camera-photo-symbolic",
                "-a",
                "HyDePanel Screenshot Utility",
                "-h",
                f"STRING:image-path:{file_path}",
                "Screenshot Saved",
                f"Saved Screenshot at {file_path}",
            ]
            if file_path
            else ["Screenshot Sent to Clipboard"]
        )

        proc: Gio.Subprocess = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE)

        def do_callback(process: Gio.Subprocess, task: Gio.Task):
            try:
                _, stdout, stderr = process.communicate_utf8_finish(task)
            except Exception:
                logger.error(
                    f"[SCREENSHOT] Failed read notification action with error {stderr}"
                )
                return

            match stdout.strip("\n"):
                case "files":
                    exec_shell_command_async(f"xdg-open {self.screenshot_path}")
                case "view":
                    exec_shell_command_async(f"xdg-open {file_path}")
                case "edit":
                    exec_shell_command_async(f"swappy -f {file_path}")

        proc.communicate_utf8_async(None, None, do_callback)

    @Property(bool, "readable", default_value=False)
    def is_recording(self):
        return helpers.is_app_running("wf-recorder")
