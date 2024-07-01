import asyncio
import pickle
from typing import List, Dict

from pydantic import BaseModel

from .ceylon import AgentDefinition, WorkspaceConfig, AgentCore, Workspace
from ceylon.ceylon.ceylon import uniffi_set_event_loop


class RunnerInput(BaseModel):
    request: dict
    agents: List[AgentDefinition]
    network: Dict[str, List[str]]

    class Config:
        arbitrary_types_allowed = True


class AgentRunner:
    agents = []
    config: WorkspaceConfig

    def __init__(self, workspace_name, workspace_host="0.0.0.0", workspace_port=0):
        self.agents = []
        self.config = WorkspaceConfig(name=workspace_name, host=workspace_host, port=workspace_port)

    def register_agent(self, agent: AgentCore):
        self.agents.append(agent)

    async def run(self, inputs, network: Dict[str, List[str]] = None):
        uniffi_set_event_loop(asyncio.get_event_loop())
        workspace = Workspace(agents=self.agents, config=self.config)
        await workspace.run(pickle.dumps(
            RunnerInput(
                request=inputs, agents=[
                    await agent.definition() for agent in self.agents
                ],
                network=network if network else {}
            )
        ))
