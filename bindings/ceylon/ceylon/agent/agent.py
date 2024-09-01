from ceylon.agent.common import AgentCommon
from ceylon.core.worker import Worker
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT, DEFAULT_WORKSPACE_IP, DEFAULT_CONF_FILE


class Agent(Worker, AgentCommon):
    agent_type = "AGENT"
    history_responses = []

    def __init__(self, name="admin",
                 conf_file=DEFAULT_CONF_FILE,
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_port=DEFAULT_WORKSPACE_PORT,
                 admin_ip=DEFAULT_WORKSPACE_IP,
                 admin_peer="",
                 role="worker"):
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_port=admin_port,
            admin_peer=admin_peer,
            admin_ip=admin_ip,
            role=role if role else name,
            conf_file=conf_file
        )
        AgentCommon.__init__(self)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        await self._on_message_handler(agent_id, data, time)
