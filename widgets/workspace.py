from fabric.hyprland.widgets import WorkspaceButton, Workspaces as HyperlandWorkspace
from fabric.widgets.box import Box


class WorkSpaces(Box):
    def __init__(self, occupied=True, count=8, **kwargs):
        super().__init__(name="workspaces-box", style_classes="bar-box", **kwargs)

        self.workspace = HyperlandWorkspace(
            name="workspaces",
            spacing=4,
            buttons=[WorkspaceButton(id=i, label=str(i)) for i in range(1, count + 1)]
            if not occupied
            else None,
            buttons_factory=lambda ws_id: WorkspaceButton(id=ws_id, label=str(ws_id)),
        )

        self.children = self.workspace
