# Buster v7.5 AI Mode Manager

This pack centralizes AI prompts, generation settings, and mode behavior.

## What it adds

```text
buster/
└── brain/
    └── providers/
        ├── ai_modes.py
        ├── prompt_builder.py
        ├── mode_detector.py
        ├── provider_modes.py
        └── ollama.py
```

## Modes

| Mode | Purpose | Output |
|---|---|---|
| voice | Fast conversation | 2-5 sentences |
| coding | Code/build/fix tasks | Longer, precise |
| research | Research/current info | Detailed |
| default | General use | Balanced |

## Test

```bash
pytest
```

You should go from 65 tests to 72 tests.

## Manual use

Inside Python:

```python
from buster.brain.providers.ollama import OllamaProvider

ai = OllamaProvider()
print(ai.complete("how are you?", mode="voice"))
print(ai.complete("fix this pytest error", mode="coding"))
```

## Integration idea

When Buster hears a voice command, call Ollama with:

```python
provider.complete(text, context=context, mode="voice")
```

For coding commands:

```python
provider.complete(text, context=context, mode="coding")
```

For research/web commands:

```python
provider.complete(text, context=context, mode="research")
```
