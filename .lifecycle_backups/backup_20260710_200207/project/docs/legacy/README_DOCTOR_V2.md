# Buster Doctor v2

This upgrades `scripts\doctor.bat` from a simple pytest runner into a full diagnostics command.

## Run

```bat
scripts\doctor.bat
```

## Faster run without tests

```bat
scripts\doctor.bat --no-tests
```

## Auto-create missing basic folders

```bat
scripts\doctor.bat --fix
```

## What it checks

- Python version
- Git version, branch, and working tree status
- Internet reachability
- Required Python modules
- Voice dependencies: SpeechRecognition and PyAudio
- Ollama installed models
- Ollama loaded models
- Core Buster v7.1-v7.6 files
- Core imports
- AI provider diagnostics
- Full pytest suite

## Expected result

```text
OVERALL: READY FOR DEVELOPMENT
```
