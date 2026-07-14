# Buster v7.3 AI Provider Auto-Model Manager

This fixes the issue where Buster tries to use `llama3.2` even when only another Ollama model is installed.

## What it adds

```text
buster/
└── brain/
    └── providers/
        ├── ollama.py
        ├── ollama_models.py
        └── provider_diagnostics.py
```

## What it does

- Detects installed Ollama models.
- Uses the preferred model if installed.
- Otherwise prefers coder models like `qwen2.5-coder:3b`.
- Otherwise uses the first installed model.
- Gives clearer errors if a model is missing.
- Gives a better provider status report.

## Test

```bash
pytest
```

You should go from 56 tests to 62 tests.

## Manual test

```bash
ollama list
```

Then in Buster:

```text
use ollama
ai status
```

You should see Buster using your installed model, such as:

```text
qwen2.5-coder:3b
```
