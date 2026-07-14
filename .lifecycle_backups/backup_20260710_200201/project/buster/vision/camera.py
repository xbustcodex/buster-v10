class Camera:
    def __init__(self, index=0, width=640, height=480):
        self.index = index
        self.width = width
        self.height = height
        self.capture = None

    def open(self):
        import cv2
        self.capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.index)
        if not self.capture.isOpened():
            return False
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return True

    def read(self):
        if not self.capture:
            return None
        ok, frame = self.capture.read()
        return frame if ok else None

    def close(self):
        if self.capture:
            self.capture.release()
            self.capture = None
