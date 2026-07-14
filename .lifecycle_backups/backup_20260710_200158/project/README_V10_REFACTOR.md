# Buster Desktop AI OS v10 Refactor

This is a clean refactor workspace generated from the existing Buster Desktop Companion project.

## Goal

Buster v10 should consolidate the project around:

- One runtime
- One service manager
- One event bus
- One agent framework
- Mission Control as a dashboard
- Lifecycle Manager as a core service
- Cleaner repository layout

## First checks

Run:

python run_lifecycle.py status
python run_lifecycle.py health
pytest

Do not delete the old project yet.
Use this folder as the v10 refactor workspace.
