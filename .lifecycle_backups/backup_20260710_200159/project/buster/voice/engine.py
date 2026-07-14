import queue
import threading
import time

class VoiceEngine:
    def __init__(self, wake_word, bus):
        self.wake_word = wake_word.lower()
        self.bus = bus
        self.tts_queue = queue.Queue()
        self.ready = False
        self.conversation_mode = False
        self.last_heard = ""
        self.last_error = ""
        self.recognizer = None
        self.microphone = None
        threading.Thread(target=self._tts_worker, daemon=True).start()
        self._init_stt()

    def speak(self, text):
        if text:
            self.tts_queue.put(text)

    def _tts_worker(self):
        try:
            import pythoncom; pythoncom.CoInitialize()
        except Exception: pass
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            engine.setProperty("volume", 1.0)
            self.ready = True
        except Exception as exc:
            self.last_error = str(exc)
            return
        while True:
            text = self.tts_queue.get()
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                self.last_error = str(exc)

    def _init_stt(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.microphone = sr.Microphone()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def listen_once(self, timeout=5, phrase_time_limit=8):
        if not self.recognizer or not self.microphone:
            if not self._init_stt():
                return ""
        try:
            import speech_recognition as sr
            with self.microphone as source:
                self.bus.emit("voice_status", status="calibrating")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                self.bus.emit("voice_status", status="listening")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            self.bus.emit("voice_status", status="recognizing")
            try:
                text = self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                text = ""; self.last_error = "Could not understand audio."
            except sr.RequestError as exc:
                text = ""; self.last_error = f"Speech recognition request failed: {exc}"
            self.last_heard = text
            self.bus.emit("voice_status", status="standby")
            return text
        except Exception as exc:
            self.last_error = str(exc)
            self.bus.emit("voice_status", status="error")
            return ""

    def listen_once_async(self):
        threading.Thread(target=self._listen_once_worker, daemon=True).start()
        return "Listening once. Speak now."

    def _listen_once_worker(self):
        text = self.listen_once()
        self.bus.emit("voice_command", text=text or "")

    def start_conversation(self):
        if self.conversation_mode:
            return "Conversation mode is already running."
        self.conversation_mode = True
        threading.Thread(target=self._conversation_loop, daemon=True).start()
        return f"Conversation mode started. Say {self.wake_word}, then your command."

    def stop_conversation(self):
        self.conversation_mode = False
        self.bus.emit("voice_status", status="stopped")
        return "Conversation mode stopped."

    def _conversation_loop(self):
        self.bus.emit("voice_status", status="conversation")
        while self.conversation_mode:
            text = self.listen_once(timeout=8, phrase_time_limit=8)
            if not self.conversation_mode:
                break
            if not text:
                time.sleep(0.2); continue
            low = text.lower().strip()
            if "stop listening" in low or "stop conversation" in low:
                self.conversation_mode = False
                self.bus.emit("voice_command", text="stop conversation")
                break
            if low.startswith(self.wake_word):
                command = text[len(self.wake_word):].strip()
                if command: self.bus.emit("voice_command", text=command)
                else: self.speak("Yes?")
            elif self.wake_word in low:
                command = low.split(self.wake_word, 1)[1].strip()
                if command: self.bus.emit("voice_command", text=command)
            time.sleep(0.2)
        self.bus.emit("voice_status", status="standby")

    def status(self):
        mic = "ready" if self.microphone else "not ready"
        tts = "ready" if self.ready else "starting"
        mode = "conversation" if self.conversation_mode else "standby"
        heard = f" Last heard: {self.last_heard}" if self.last_heard else ""
        err = f" Error: {self.last_error}" if self.last_error else ""
        return f"Voice TTS {tts}. Microphone {mic}. Wake word: {self.wake_word}. Mode: {mode}.{heard}{err}"
