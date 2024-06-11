import asyncio

from ceylon.ceylon import Workspace, WorkspaceConfig, uniffi_set_event_loop


class AgentRunner:
    agents = []
    config: WorkspaceConfig

    def __init__(self, workspace_name, workspace_host="/ip4/0.0.0.0/tcp", workspace_port=8888):
        self.agents = []
        self.config = WorkspaceConfig(name=workspace_name, host=workspace_host, port=workspace_port)

    def register_agent(self, agent):
        self.agents.append(agent)

    async def run(self, inputs):
        uniffi_set_event_loop(asyncio.get_event_loop())
        workspace = Workspace(agents=self.agents, config=self.config)
        await workspace.run(inputs)
