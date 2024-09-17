from loguru import logger

from ceylon import Agent, on_message
from ceylon.agent.admin import AgentDetails
from ceylon.auto.model import SubTaskRequest
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT, DEFAULT_WORKSPACE_IP


class TaskExecutorAgent(Agent):

    def __init__(self, name: str, role: str,
                 conf_file=None,
                 workspace_id: str = DEFAULT_WORKSPACE_ID,
                 admin_port: int = DEFAULT_WORKSPACE_PORT,
                 admin_ip: str = DEFAULT_WORKSPACE_IP,
                 *args,
                 **kwargs):
        super().__init__(name=name, role=role, workspace_id=workspace_id, admin_port=admin_port, admin_ip=admin_ip,
                         conf_file=conf_file,
                         *args, **kwargs)

    @on_message(AgentDetails)
    async def on_agent_details(self, data: AgentDetails):
        pass
        # logger.info(data)

    @on_message(SubTaskRequest)
    async def on_sub_task_request(self, sub_task_request):
        logger.info(sub_task_request)
