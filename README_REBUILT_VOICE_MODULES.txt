Buster rebuilt voice modules

Replace these project files:
buster/runtime/services/voice_service.py
buster/runtime/services/audio_backends/edge_tts_backend.py

These complete modules repair the broken class indentation and retain:
- Whisper warmup
- fast transcription support
- duplicate transcription protection
- Edge-TTS
- pygame interruptible playback
- pyttsx3 fallback
- VoiceService.stop_speaking()
- audio.tts.started/completed/interrupted events
- audio.tts.stop.requested handler

Recommended dependency:
pip install pygame

Then run:
python main.py
