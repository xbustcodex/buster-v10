Service vs. Agent Distinction
Buster draws a strict architectural boundary between Permanent Services and Transient Agents:

Services (services/): Long-running, permanent system capabilities (Voice, Vision, Git, Memory). They boot with the kernel and remain active until system shutdown.

Agents (agents/): Transient, task-oriented worker processes (Builder, Tester, Fixer, Reviewer, Verifier). They are instantiated on demand, assigned permission scopes, executed via the task scheduler, and cleaned up upon task completion.

                       ┌─────────────────────────┐
                       │  Buster Kernel Core     │
                       └────────────┬────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌─────────────────────┐                          ┌───────────────────────┐
│ Permanent Services  │                          │   Transient Agents    │
│ (Voice, Vision, Git)│                          │(Builder, Tester, Fixer)│
│  - Boot with OS     │                          │  - Spawned per task   │
│  - Always running   │                          │  - Ephemeral & scoped │
└─────────────────────┘                          └───────────────────────┘
Agent State Machine
[ REGISTERED ] ──> [ IDLE ] ──> [ WORKING ] ──> [ TERMINATED ]
                     ▲               │
                     └────[ PAUSED ]─┘
Registration Interface

from buster.kernel.agent_manager import AgentManager, AgentState

agent_mgr = AgentManager(permissions_mgr=kernel.permissions)

# Register a worker agent instance bound to a specific role
agent_mgr.register_agent(
    agent_id="builder-agent-01",
    agent_type="BuilderAgent",
    instance=builder_instance,
    role="builder"
)

