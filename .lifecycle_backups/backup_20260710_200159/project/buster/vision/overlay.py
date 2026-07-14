class OverlayRenderer:
    def draw(self, frame, result):
        if frame is None:
            return frame
        import cv2
        for item in result.faces:
            x, y, w, h = item.box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 200, 255), 2)
            cv2.putText(frame, item.label, (x, max(20, y-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        for item in result.objects:
            x, y, w, h = item.box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 160, 0), 2)
            cv2.putText(frame, f"{item.label} {int(item.confidence*100)}%", (x, max(20, y-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 160, 0), 2)
        for qr in result.qr_codes:
            x, y, w, h = qr.get("box", (0, 0, 0, 0))
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 80), 2)
            cv2.putText(frame, qr.get("text", "QR")[:24], (x, max(20, y-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 80), 2)
        cv2.putText(frame, f"FPS: {result.fps:.1f}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
        return frame
