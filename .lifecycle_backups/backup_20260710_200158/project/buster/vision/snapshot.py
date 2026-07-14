from pathlib import Path
from datetime import datetime

class SnapshotManager:
    def __init__(self, snapshots_dir):
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def save(self, frame):
        if frame is None:
            return ""
        import cv2
        file = self.snapshots_dir / f"vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(str(file), frame)
        return str(file)
