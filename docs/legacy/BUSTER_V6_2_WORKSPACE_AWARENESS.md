# Buster v6.2 Continuous Workspace Awareness

This release lets Buster notice the development environment and respond through the SDK and Living Companion runtime.

## Adds

- WorkspaceAwarenessRuntime
- AppDetector
- ProjectContextDetector
- GitWatcher
- DeviceWatcher
- Workspace awareness dashboard
- Workspace awareness widget

## Example

Buster can now notice:

```text
Android Studio is active
ESP32 device detected
Project context detected: Python project
Git workspace has changed files
```

And respond with useful companion messages.
