import abc
from typing import Any

from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT
from ceylon.task.task_operator import TaskOperator


class TaskOperatorWithHumanInteractive(TaskOperator, abc.ABC):
    agent_type = "TASK_OPERATOR_WITH_HUMAN_INTERACTIVE"

    def __init__(self, name: str, role: str = "Get Human Inputs from User", workspace_id: str = DEFAULT_WORKSPACE_ID,
                 admin_port: int = DEFAULT_WORKSPACE_PORT, *args, **kwargs):
        super().__init__(name, role, workspace_id, admin_port, *args, **kwargs)

    async def get_result(self, task) -> Any:
        # Get message from user
        message = input()
        return message
