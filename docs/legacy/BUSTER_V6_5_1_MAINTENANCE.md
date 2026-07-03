# Buster v6.5.1 Maintenance + Modernization

This release cleans the v6 platform foundation before live voice and deeper runtime work.

## Adds

- `buster.utils.datetime_utils`
- `buster.utils.json_utils`
- `buster.utils.logger`
- Modern UTC timestamp helpers
- Atomic JSON persistence helpers
- Shared logger helper
- DeprecationWarning test guard
- Source scan to prevent `datetime.utcnow()` coming back

## Goal

Keep Buster warning-free and Python 3.12+ ready before v6.6 Live Voice Companion.
