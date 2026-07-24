\# Buster v13.1 Development Roadmap



\## Milestone



\*\*Buster v13.1 — Persistent Proactive Intelligence\*\*



v13.0 established the proactive goal pipeline:



```text

Observation

→ Curiosity Signal

→ Autonomous Goal Runtime

→ Strategy Planner

→ Sandbox Execution

→ PAV Verification

→ Learning

v13.1 will make that pipeline persistent, governed, visible and reliable
across runtime restarts.

Architectural Rules
BusterRuntimeCore remains the only application runtime owner.
Curiosity produces signals, not executable actions.
GoalService decides which signals become goals.
GoalService never performs automation directly.
Approved goals are delegated to the existing Strategy Planner.
Execution must use the existing sandbox and verification systems.
Privileged capabilities require policy approval.
Goal state changes must be auditable.
Runtime-generated state must not become source architecture.
No duplicate goal runtime, scheduler or event bus may be introduced.
v13.1.1 — Persistent Goal Registry
 Add GoalRegistry
 Add persistent goal storage
 Restore goals after runtime restart
 Track complete goal status history
 Add deterministic goal deduplication
 Add goal cooldown support
 Add parent and child goal relationships
 Add registry tests

Target files:

buster/autonomy/goals/
    registry.py
    storage.py
    models.py
    goal_service.py

Initial storage format:

data/autonomy/goals.json
data/autonomy/goal_history.jsonl
v13.1.2 — Curiosity Runtime Integration
 Run curiosity observation during controlled runtime ticks
 Add minimum idle interval
 Add detector cooldowns
 Prevent duplicate signals
 Convert eligible signals into goal proposals
 Publish curiosity events
 Add runtime integration tests

Initial detectors:

StaleProjectIndexDetector
RepeatedFailureDetector
UnreviewedChangesDetector
DocumentationGapDetector
MemoryBacklogDetector
RuntimeHealthDetector
v13.1.3 — Capability-Based Governance
 Add capability enum
 Add per-capability approval rules
 Add custom user policy storage
 Add risk escalation
 Add policy decision explanations
 Add policy audit records
 Add governance tests

Initial capabilities:

READ_FILES
WRITE_FILES
DELETE_FILES
RUN_TESTS
RUN_SHELL
GIT_COMMIT
GIT_PUSH
BROWSER_CONTROL
DESKTOP_CONTROL
NETWORK_ACCESS
PLUGIN_INSTALL
HARDWARE_CONTROL
EXTERNAL_COMMUNICATION

Default policy:

Read-only analysis       Auto approve
Repository indexing      Auto approve
Test execution           Auto approve
File modification        Ask
File deletion            Always ask
Git commit               Ask
Git push                 Always ask
Desktop interaction      Ask
External communication   Always ask
Plugin installation      Always ask
Hardware interaction     Always ask
v13.1.4 — Mission Compiler
 Translate approved goals into structured missions
 Validate success criteria
 Resolve required capabilities
 Generate reversible execution steps
 Delegate plans to Strategy Planner
 Reject incomplete or unsafe missions
 Add mission compiler tests

Required separation:

Goal Runtime
    decides WHAT should be considered

Mission Compiler
    converts the goal into an executable mission

Strategy Planner
    decides HOW the mission should be completed
v13.1.5 — Autonomous Goals UI
 Add Autonomous Goals panel
 Display proposed goals
 Display goals awaiting approval
 Display active and completed goals
 Show evidence and scoring
 Add Approve and Reject controls
 Add Pause and Cancel controls
 Add autonomy-level selector
 Add goal-history view

Each goal must display:

Reason
Evidence
Expected value
Confidence
Estimated cost
Risk
Required capabilities
Proposed actions
Success criteria
Current status
Verification result
Learning outcome
v13.1.6 — Memory Synthesis
 Summarize completed goal outcomes
 Record successful strategies
 Record failed approaches
 Store reusable repair patterns
 Link learning records to goal IDs
 Prevent duplicate learning records
 Add synthesis tests
v13.1.7 — Idle Brain Status
 Add visible runtime cognition status
 Display observation activity
 Display curiosity scans
 Display proposed opportunities
 Display policy decisions
 Display idle and paused states
 Avoid fake or uncontrolled continuous reasoning

Example statuses:

Idle
Observing repository
Checking runtime health
Evaluating opportunity
Awaiting approval
Planning approved goal
Verifying outcome
Synthesizing learning
Autonomy paused
Canonical Events
curiosity.signal_detected
curiosity.signal_suppressed

goal.proposed
goal.deduplicated
goal.evaluated
goal.approval_requested
goal.approved
goal.rejected
goal.scheduled
goal.started
goal.progress
goal.verification_started
goal.completed
goal.failed
goal.blocked
goal.cancelled

goal.registry_loaded
goal.registry_saved

mission.compiled
mission.rejected

autonomy.level_changed
autonomy.policy_decision

learning.goal_synthesized


Definition of Done

Buster v13.1 is complete when:

 Goals survive application restarts
 Duplicate goals are suppressed
 Curiosity runs safely during runtime ticks
 Every executable goal has a policy decision
 Privileged actions cannot bypass approval
 Approved goals use the existing planning pipeline
 Execution remains sandboxed
 Outcomes are verified before completion
 Learning records reference their originating goals
 Mission Control exposes full goal governance
 The complete test suite passes
 No second runtime, event bus or scheduler is created
First Development Task

Implement:

v13.1.1 — Persistent Goal Registry

Required first end-to-end scenario:

Create goal proposal
→ save registry
→ restart GoalService
→ reload goal
→ update status
→ append history record
→ reject duplicate proposal
