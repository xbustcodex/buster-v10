# Buster v7.6 Unified Intelligence Orchestrator

This pack starts connecting the subsystems together.

## What it adds

```text
buster/
├── brain/
│   ├── orchestrator.py
│   ├── unified_agent_loop.py
│   ├── router_explainer.py
│   └── conversation_runtime.py
│
└── web/
    └── research_memory_bridge.py
```

## What it does

Buster now has one central decision layer that chooses:

- route: `web`, `project`, `agent`, or `local`
- AI mode: `voice`, `coding`, `research`, or `default`
- context source: web/project/agent/local
- provider prompt mode

## Test

```bash
pytest
```

You should go from 72 tests to 79 tests.

## Manual usage

```python
from buster.brain.providers.ollama import OllamaProvider
from buster.brain.unified_agent_loop import UnifiedAgentLoop

provider = OllamaProvider()
loop = UnifiedAgentLoop(provider)

print(loop.run("how are you?", voice=True))
print(loop.run("latest Python release"))
print(loop.run("build me a calculator app"))
```

## Integration target

Eventually route all UI, keyboard, and voice requests through:

```python
UnifiedConversationRuntime(ai_provider).ask(text, voice=True_or_false)
```

That gives Buster one shared brain path instead of separate behavior for voice, GUI, and commands.
