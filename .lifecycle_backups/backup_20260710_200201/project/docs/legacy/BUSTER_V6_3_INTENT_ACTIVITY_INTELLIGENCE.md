# Buster v6.3 Intent & Activity Intelligence

This release lets Buster infer what the user is likely trying to do from workspace signals.

## Adds

- Activity signals
- Intent hypotheses
- IntentActivityEngine
- InterruptPolicy
- MissionIntentRuntime
- Intent dashboard/widget

## Example

Signals:

```text
Android Studio active
ESP32 connected
PlatformIO project detected
```

Intent:

```text
Likely mixed Android and ESP32 hardware development session.
```

Companion response:

```text
It looks like you're working across Android and ESP32. I'll prepare both development contexts.
```
