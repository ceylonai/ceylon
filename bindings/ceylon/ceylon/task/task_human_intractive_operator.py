import abc
from typing import Any

from ceylon.task.task_operator import TaskOperator


class TaskOperatorWithHumanInteractive(TaskOperator, abc.ABC):
    agent_type = "TASK_OPERATOR_WITH_HUMAN_INTERACTIVE"

    async def get_result(self, task) -> Any:
        # Get message from user
        message = input()
        return message
