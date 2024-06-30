import asyncio
import pickle
from typing import List, Dict

from pydantic import BaseModel

from ceylon.ceylon import Workspace, WorkspaceConfig, uniffi_set_event_loop, AgentCore, AgentDefinition


class RunnerInput(BaseModel):
    request: dict
    agents: List[AgentDefinition]
    network: Dict[str, List[str]]

    class Config:
        arbitrary_types_allowed = True


class AgentRunner:
    agents = []
    config: WorkspaceConfig

    def __init__(self, workspace_name, workspace_host="/ip4/0.0.0.0/udp", workspace_port=8888):
        self.agents = []
        self.config = WorkspaceConfig(name=workspace_name, host=workspace_host, port=workspace_port)

    def register_agent(self, agent: AgentCore):
        self.agents.append(agent)

    async def run(self, inputs, network):
        uniffi_set_event_loop(asyncio.get_event_loop())
        workspace = Workspace(agents=self.agents, config=self.config)
        await workspace.run(pickle.dumps(
            RunnerInput(
                request=inputs, agents=[
                    await agent.definition() for agent in self.agents
                ],
                network=network
            )
        ))
