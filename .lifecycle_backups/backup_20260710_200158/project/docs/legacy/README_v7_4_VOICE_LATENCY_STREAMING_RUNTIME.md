# Buster v7.4 Voice Latency + Streaming Runtime

This pack focuses on making Buster feel faster in voice mode.

## What it adds

```text
buster/
├── voice/
│   ├── latency_config.py
│   ├── fast_listener.py
│   └── voice_pipeline.py
│
├── brain/
│   └── providers/
│       ├── ollama.py
│       └── ollama_streaming.py
│
└── conversation_os/
    └── fast_voice_runtime.py
```

## What it improves

- Lower speech recognition delay.
- `timeout` and `phrase_time_limit` support.
- Queued voice pipeline so AI response does not block listener/UI.
- Ollama `keep_alive` support to reduce cold starts.
- Streaming-capable Ollama method: `complete_stream()`.
- Ollama warmup method: `warmup()`.

## Test

```bash
pytest
```

You should go from 62 tests to 65 tests.

## Manual integration ideas

### Warm Ollama when switching provider

In your AI provider manager, after setting Ollama active:

```python
provider = self.providers["ollama"]
if hasattr(provider, "warmup"):
    provider.warmup()
```

### Use faster listen call inside VoiceEngine

Where your voice engine currently does:

```python
audio = recognizer.listen(source)
```

replace it with:

```python
audio = recognizer.listen(source, timeout=2, phrase_time_limit=6)
```

Also set:

```python
recognizer.pause_threshold = 0.55
recognizer.non_speaking_duration = 0.25
```

### Streaming response

Use:

```python
provider.complete_stream(prompt, context, on_chunk=print)
```

Later you can send chunks to the UI or speech system.
