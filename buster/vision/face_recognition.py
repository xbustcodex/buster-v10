import json
import math
from pathlib import Path

class FaceRecognizer:
    def __init__(self, db_dir="data/faces"):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.db_dir / "faces.json"
        self.known_faces = self._load()

    def _load(self):
        if not self.db_file.exists():
            return {}
        try:
            return json.loads(self.db_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self):
        self.db_file.write_text(json.dumps(self.known_faces, indent=2), encoding="utf-8")

    def _embedding(self, frame, box):
        try:
            import cv2, numpy as np
            x, y, w, h = box
            crop = frame[y:y+h, x:x+w]
            if crop.size == 0:
                return None
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (64, 64))
            arr = gray.astype("float32").flatten()
            arr = (arr - float(arr.mean())) / (float(arr.std()) or 1.0)
            arr = arr / (float(np.linalg.norm(arr)) or 1.0)
            return arr.tolist()
        except Exception:
            return None

    def learn(self, name, frame=None, faces=None):
        if frame is None:
            return "No camera frame available. Start vision first."
        if not faces:
            return "I cannot see a face clearly. Move closer to the webcam and try again."
        face = max(faces, key=lambda f: f.box[2] * f.box[3])
        emb = self._embedding(frame, face.box)
        if emb is None:
            return "I could not build a face profile from this frame."
        clean = (name or "Adam").strip()
        self.known_faces[clean] = {"embedding": emb, "samples": 1}
        self._save()
        return f"I learned this face as {clean}."

    def recognize(self, frame, faces):
        if frame is None or not faces or not self.known_faces:
            return faces
        for face in faces:
            emb = self._embedding(frame, face.box)
            if emb is None:
                continue
            name, score = self._best_match(emb)
            if name and score >= 0.72:
                face.label = name
                face.confidence = score
            else:
                face.label = "Unknown"
        return faces

    def identify_best(self, frame, faces):
        if frame is None:
            return "No camera frame available. Start vision first."
        if not faces:
            return "I cannot see a face clearly."
        if not self.known_faces:
            return "I do not know any faces yet. Say: learn my face."
        face = max(faces, key=lambda f: f.box[2] * f.box[3])
        emb = self._embedding(frame, face.box)
        if emb is None:
            return "I could not read the face clearly."
        name, score = self._best_match(emb)
        if name and score >= 0.72:
            return f"You look like {name}. Confidence {int(score * 100)} percent."
        return f"I see a face, but I do not recognize it. Best match was {name or 'none'} at {int(score * 100)} percent."

    def _best_match(self, emb):
        best_name = ""
        best_score = 0.0
        for name, data in self.known_faces.items():
            score = self._cosine(emb, data.get("embedding", []))
            if score > best_score:
                best_name = name
                best_score = score
        return best_name, best_score

    def _cosine(self, a, b):
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x*y for x, y in zip(a, b))
        na = math.sqrt(sum(x*x for x in a)) or 1.0
        nb = math.sqrt(sum(y*y for y in b)) or 1.0
        return dot / (na * nb)

    def status(self):
        return "No known faces saved." if not self.known_faces else "Known faces: " + ", ".join(sorted(self.known_faces.keys()))
