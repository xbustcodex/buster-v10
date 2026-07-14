from buster.agents.builder import BuilderAgent
from buster.agents.tester import TesterAgent
from buster.agents.fixer import FixerAgent
from buster.agents.reviewer import ReviewerAgent
from buster.agents.verifier import VerifierAgent

class AgentTeam:
    def __init__(self, bus=None):
        self.agents = {
            "builder": BuilderAgent(bus),
            "tester": TesterAgent(bus),
            "fixer": FixerAgent(bus),
            "reviewer": ReviewerAgent(bus),
            "verifier": VerifierAgent(bus),
        }

    def delegate(self, agent_name, task):
        agent = self.agents.get(agent_name)
        if not agent:
            return f"No agent named {agent_name}."
        return agent.run(task)

    def snapshot(self):
        return {name.title(): {"progress": a.progress, "status": a.status, "task": a.current_task} for name, a in self.agents.items()}

    def summary(self):
        return ". ".join([f"{n.title()}: {a.status} {a.progress} percent" for n, a in self.agents.items()])
