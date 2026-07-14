# Buster AI OS Architecture

Buster is evolving from a desktop companion into a Jarvis-level AI operating environment.

## Core Layers

- Brain: conversation, providers, planner, intent handling.
- Intelligence: confidence, risk analysis, reasoning, scoring and strategy selection.
- Memory: long-term facts and knowledge.
- Learning: what worked, what failed and reusable patterns.
- Experience: engineering outcomes, project experience, skills and user overrides.
- Autonomy: next actions, job awareness and self-directed recommendations.
- Event Bus: shared communication channel for subsystems.
- Plugin OS: installable capabilities without growing the core into one huge file.
- Mission Control: unified dashboard showing system health, confidence, agents, jobs, plugins, learning, experience and skills.

## Design Rule

Buster should become smarter over time without becoming one massive file.

Every new capability should be one of:

1. Core subsystem
2. Agent
3. Plugin
4. Dashboard/widget
5. Data store

## v3.9 Goal

Mission Control becomes the main AI OS view.
It does not replace the existing dashboard yet; it provides a clean backend and optional widget that can be integrated into the existing UI.
