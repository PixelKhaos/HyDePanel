from typing import List

from fabric import Signal
from fabric.notifications import Notification, Notifications

from utils.config import widget_config


class CustomNotifications(Notifications):
    """A custom notification service."""

    def __init__(self):
        super().__init__()
        self.all_notifications = []
        self._count = 0
        self._dont_disturb = False

    def cache_notification(self, data: Notification):
        """Cache the notification."""
        flattened_apps = widget_config["notification"].get("flattened_apps", [])

        # Remove old notifications if this is a flattened app
        if data.app_name in flattened_apps:
            self.all_notifications = [
                n for n in self.all_notifications
                if n.app_name != data.app_name
            ]

        # Add the new notification
        self.all_notifications.append(data)
        self._count = len(self.all_notifications)
        self.emit("notification_count", self._count)

    def get_deserialized(self) -> List[Notification]:
        """Get all notifications."""
        return self.all_notifications

    @property
    def count(self) -> int:
        """Get the number of notifications."""
        return self._count

    @property
    def dont_disturb(self) -> bool:
        """Return the do not disturb status."""
        return self._dont_disturb

    @dont_disturb.setter
    def dont_disturb(self, value: bool):
        """Set the do not disturb status."""
        self._dont_disturb = value
        self.emit("dnd", value)

    def clear_all_notifications(self):
        """Clear all notifications."""
        self.all_notifications = []
        self._count = 0
        self.emit("notification_count", self._count)
        self.emit("clear_all", True)

    def remove_notification(self, id: int):
        """Remove the notification of given id."""
        self.all_notifications = [n for n in self.all_notifications if n.id != id]
        self._count = len(self.all_notifications)
        self.emit("notification_count", self._count)
        if self._count == 0:
            self.emit("clear_all", True)

    @Signal
    def clear_all(self, value: bool) -> None:
        """Signal emitted when notifications are emptied."""
        # Implement as needed for your application

    @Signal
    def notification_count(self, value: int) -> None:
        """Signal emitted when a new notification is added."""
        # Implement as needed for your application

    @Signal
    def dnd(self, value: bool) -> None:
        """Signal emitted when dnd is toggled."""
        # Implement as needed for your application
