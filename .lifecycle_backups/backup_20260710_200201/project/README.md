# Buster Desktop Companion v6.3 Developer Edition

Clean rebuild of Buster with a stable architecture.

This version avoids patch-on-patch problems. It is generated as one consistent project.

## Core features

- PySide6 desktop UI
- Event bus
- Service container
- Thread pool
- Service manager
- Performance monitor
- AI provider manager
- Local rules AI
- Ollama provider
- LM Studio provider
- OpenRouter provider
- Async brain execution
- Application manager
- Voice TTS
- Microphone input
- Conversation mode
- Vision engine
- Lazy webcam loading
- YOLO object detection
- Face detection
- Face learning
- Face recognition
- QR/barcode scanner
- Snapshot saving
- Desktop automation
- Agent team
- Plugin framework
- Memory database
- Diagnostics

## Install

```bat
cd buster_desktop_companion_v3_0_developer_edition
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Commands to try

```text
performance
services
thread status
ai status
use local
ask what can you do
open my browser
listen once
start conversation
start vision
vision status
detect objects
detect faces
learn my face
who am i
take photo
scan qr
agents
builder create a calculator
system status
diagnostics
```

## Optional Ollama

```bat
ollama pull llama3.2
```

Then in Buster:

```text
use ollama
ask write me a simple Python function
```

## Optional OpenRouter

```bat
setx OPENROUTER_API_KEY "your_key_here"
```

Restart terminal, then:

```text
use openrouter
```
