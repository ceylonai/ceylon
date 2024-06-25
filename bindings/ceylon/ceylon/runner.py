import asyncio
import pickle
import threading
from asyncio import AbstractEventLoop
from typing import List, Dict

from pydantic import BaseModel

from ceylon.ceylon import Workspace, WorkspaceConfig, uniffi_set_event_loop, AgentCore, AgentDefinition, \
    agent_runner_multi_thread, agent_run_single


class RunnerInput(BaseModel):
    request: dict
    agents: List[AgentDefinition]
    network: Dict[str, List[str]]

    class Config:
        arbitrary_types_allowed = True


class AgentRunnerError(Exception):
    pass


class AgentRunnerNotLeaderError(AgentRunnerError):
    pass


class AgentRunnerCannotHaveMultipleLeadersError(AgentRunnerError):
    pass


# Function to run the event loop
def run_event_loop(loop):
    uniffi_set_event_loop(loop)
    asyncio.set_event_loop(loop)
    loop.run_forever()
    print("Event loop stopped")


class AgentRunner:
    agents: List[AgentCore] = []
    config: WorkspaceConfig
    leader_agent = None

    def __init__(self, workspace_name, workspace_port=8888):
        self.agents = []
        self.config = WorkspaceConfig(name=workspace_name, port=workspace_port)

    def register_agent(self, agent: AgentCore):
        # Not accepting multiple leaders
        if self.leader_agent is None and agent.definition().is_leader:
            self.leader_agent = agent
        elif agent.definition().is_leader and self.leader_agent is not None:
            raise AgentRunnerCannotHaveMultipleLeadersError()
        self.agents.append(agent)

    async def run_in_multi_thread(self, request: dict[str, str], network: Dict[str, List[str]] = None):
        agent_tasks = []
        for agent in self.agents:
            def run_agent(agent, loop: AbstractEventLoop):
                uniffi_set_event_loop(loop)
                loop.run_until_complete(agent_run_single(
                    agent=agent,
                    topic="ceylon-ai",
                    inputs=pickle.dumps(
                        RunnerInput(request=request, agents=[agent.definition() for agent in self.agents],
                                    network=network)),
                    workspace_id=self.config.name
                ))

            t = threading.Thread(target=run_agent, args=(agent, asyncio.new_event_loop()))
            t.start()
            agent_tasks.append(t)

        for t in agent_tasks:
            t.join()

    async def run_in_single_thread(self, request: dict[str, str], network: Dict[str, List[str]] = None):
        await agent_runner_multi_thread(
            agents=self.agents,
            topic="ceylon-ai",
            inputs=pickle.dumps(
                RunnerInput(request=request, agents=[agent.definition() for agent in self.agents],
                            network=network)),
            workspace_id=self.config.name
        )

    def leader(self):
        if self.leader_agent is None:
            raise AgentRunnerNotLeaderError()
        return self.leader_agent
