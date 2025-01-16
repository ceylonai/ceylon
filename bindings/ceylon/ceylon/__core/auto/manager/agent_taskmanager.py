from ceylon import CoreAdmin
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT


class AgentTaskManager(CoreAdmin):
    name = DEFAULT_WORKSPACE_ID

    def __init__(self, name=DEFAULT_WORKSPACE_ID,
                 port=DEFAULT_WORKSPACE_PORT,
                 *args,
                 **kwargs):
        self.name = name
        self.agents = []
        super().__init__(name=name, port=port, *args, **kwargs)

    def register_agent(self, agent):
        self.agents.append(agent)

    def do(self, inputs: bytes = b''):
        self.run_admin(inputs, self.agents)

    async def async_do(self, inputs: bytes = b''):
        await self.arun_admin(inputs, self.agents)
