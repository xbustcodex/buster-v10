try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None

from buster.workspace.mission_control_dashboard import MissionControlDashboard


class MissionControlWidget:
    """Small Tkinter-compatible Mission Control panel.

    This stays optional so Buster can still run headless and in tests.
    """

    def __init__(self, parent=None, data_dir: str = "data"):
        self.parent = parent
        self.dashboard = MissionControlDashboard(data_dir=data_dir)
        self.frame = None
        self.text = None
        if tk is not None and parent is not None:
            self.frame = ttk.Frame(parent) if ttk else tk.Frame(parent)
            self.text = tk.Text(self.frame, height=9, width=62)
            self.text.pack(fill="both", expand=True)
            self.refresh()

    def refresh(self):
        content = self.dashboard.render_text()
        if self.text is not None:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
        return content

    def pack(self, *args, **kwargs):
        if self.frame is not None:
            self.frame.pack(*args, **kwargs)
