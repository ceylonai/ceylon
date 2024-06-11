import asyncio

from ceylon.ceylon import Workspace, WorkspaceConfig, uniffi_set_event_loop, AgentCore


class AgentRunnerError(Exception):
    pass


class AgentRunnerNotLeaderError(AgentRunnerError):
    pass


class AgentRunnerCannotHaveMultipleLeadersError(AgentRunnerError):
    pass


class AgentRunner:
    agents = []
    config: WorkspaceConfig
    leader_agent = None

    def __init__(self, workspace_name, workspace_host="/ip4/0.0.0.0/tcp", workspace_port=8888):
        self.agents = []
        self.config = WorkspaceConfig(name=workspace_name, host=workspace_host, port=workspace_port)

    def register_agent(self, agent: AgentCore):
        # Not accepting multiple leaders
        if self.leader_agent is None and agent.is_leader():
            self.leader_agent = agent
        elif agent.is_leader() and self.leader_agent is not None:
            raise AgentRunnerCannotHaveMultipleLeadersError()
        self.agents.append(agent)

    async def run(self, inputs):
        if self.leader_agent is None:
            raise AgentRunnerNotLeaderError()
        uniffi_set_event_loop(asyncio.get_event_loop())
        workspace = Workspace(agents=self.agents, config=self.config)
        await workspace.run(inputs)
