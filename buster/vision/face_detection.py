from buster.vision.types import Detection

class FaceDetector:
    def __init__(self):
        self.ready = False
        self.cascade = None
        try:
            import cv2
            self.cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            self.ready = not self.cascade.empty()
        except Exception:
            self.ready = False

    def process(self, frame):
        if not self.ready or frame is None:
            return []
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        return [Detection("face", "Face", (int(x), int(y), int(w), int(h)), 1.0) for (x, y, w, h) in faces]
