class QRScanner:
    def __init__(self):
        self.ready = False
        self.pyzbar = None
        try:
            from pyzbar import pyzbar
            self.pyzbar = pyzbar
            self.ready = True
        except Exception:
            self.ready = False

    def scan(self, frame):
        if frame is None or not self.ready:
            return []
        try:
            results = []
            for code in self.pyzbar.decode(frame):
                rect = code.rect
                results.append({
                    "text": code.data.decode("utf-8", errors="ignore"),
                    "type": code.type,
                    "box": (rect.left, rect.top, rect.width, rect.height),
                })
            return results
        except Exception:
            return []
