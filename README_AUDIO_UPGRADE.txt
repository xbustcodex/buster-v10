Copy the included buster folder over the project root.

Install dependencies:
pip install faster-whisper edge-tts webrtcvad-wheels playsound3

Then run:
python main.py

Registered runtime service names:
voice
audio
local_stt
whisper
vad
edge_tts

Fixes included:
- Converts en-US/en_AU locale values to Whisper code en.
- Ignores duplicate transcription requests for the same WAV file.
- Reports transcription errors through audio.error without an uncaught thread traceback.

Inline playback fix:
- Removed os.startfile; Windows Media Player is never launched.
- Uses playsound3 inside Buster.
- Supports pygame and legacy playsound as fallbacks.
- Falls back to pyttsx3 if Edge-TTS playback is not configured.

Streaming STT upgrade:
- Adds runtime StreamingSTTService.
- Adds Live Listen toggle to VoicePanel.
- Uses 16 kHz microphone frames and the existing VAD backend.
- Sends completed utterances to the existing Faster-Whisper backend.
- Publishes audio.streaming.* events and chat.voice_input.

Wake Word upgrade:
- Adds runtime WakeWordService.
- Adds the Hey Buster toggle to VoicePanel.
- Reuses Streaming STT; no second microphone stream.
- Supports same-sentence and two-step wake commands.
- Gates chat.voice_input while wake-word mode is enabled.

Low-latency threading upgrade:
- Whisper model warms in a background thread during startup.
- Streaming capture, VAD, and transcription run independently.
- End-of-speech silence reduced from 900 ms to 450 ms.
- Faster-Whisper uses beam_size=1 and best_of=1 for voice commands.
- condition_on_previous_text is disabled to reduce delay.
- Transcription backlog is capped to keep commands responsive.

Phase 1 Voice State Machine:
- Restores the known-good low-latency VoiceService.
- Adds VoiceStateMachine as a separate runtime service.
- Adds voice.state.changed events.
- Updates VoicePanel status and face state from the state machine.
- Does not yet modify playback or add barge-in.

Phase 2 Interruptible TTS:
- Adds VoiceService.stop_speaking().
- Adds audio.tts.stop.requested.
- Adds audio.tts.interrupted.
- Uses pygame for interruptible in-process MP3 playback.
- Does not yet wire VAD speech detection to stop playback.
