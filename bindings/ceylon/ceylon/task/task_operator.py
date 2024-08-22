import abc
from typing import Dict, List, Any

from loguru import logger

from ceylon import Agent, on_message
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT
from ceylon.task import TaskAssignment, SubTaskResult
from ceylon.task.task_operation import TaskResultStatus


class TaskOperator(Agent, abc.ABC):
    agent_type = "TASK_OPERATOR"

    def __init__(self, name: str, role: str, workspace_id: str = DEFAULT_WORKSPACE_ID,
                 admin_port: int = DEFAULT_WORKSPACE_PORT, *args,
                 **kwargs):
        self.task_history = []
        self.exeuction_history = []
        self.history: Dict[str, List[SubTaskResult]] = {}
        super().__init__(name=name, role=role, workspace_id=workspace_id, admin_port=admin_port, *args, **kwargs)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name and data.task.id not in self.exeuction_history:
            self.exeuction_history.append(data.task.id)
            status = TaskResultStatus.IN_PROGRESS
            result = None
            try:
                logger.info(f"{self.details().name} received subtask: {data.task.description}")
                result = await self.get_result(data.task)
                status = TaskResultStatus.COMPLETED
                logger.info(f"{self.details().name} completed subtask: {data.task.description}")
            except Exception as e:
                logger.info(f"{self.details().name} failed subtask: {data.task.description}")
                for idx, task in enumerate(self.exeuction_history):
                    if task == data.task.id:
                        del self.exeuction_history[idx]
                        break
                logger.exception(e)
                result = str(e)
                status = TaskResultStatus.FAILED

            result_task = SubTaskResult(task_id=data.task.id,
                                        name=data.task.name,
                                        description=data.task.description,
                                        agent=self.details().name,
                                        parent_task_id=data.task.parent_task_id,
                                        result=result,
                                        status=status)
            # Update task history
            if status == TaskResultStatus.COMPLETED:
                await self.add_result_to_history(result_task)
            await self.broadcast_data(result_task)
            logger.info(f"{self.details().name} sent subtask result: {data.task.description}")

    @on_message(type=SubTaskResult)
    async def on_task_result(self, data: SubTaskResult):
        await self.add_result_to_history(data)

    async def add_result_to_history(self, data: SubTaskResult):
        if data.parent_task_id in self.history:
            # If the task result already exists, replace it
            for idx, result in enumerate(self.history[data.parent_task_id]):
                if result.task_id == data.task_id:
                    self.history[data.parent_task_id][idx] = data
                    return
            self.history[data.parent_task_id].append(data)
        else:
            self.history[data.parent_task_id] = [data]

    @abc.abstractmethod
    async def get_result(self, task) -> Any:
        pass
