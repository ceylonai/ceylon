import abc
from typing import Dict, List, Any

from loguru import logger

from ceylon import Agent, on_message
from ceylon.task import TaskAssignment, TaskResult


class TaskOperator(Agent, abc.ABC):
    def __init__(self, name: str, role: str, *args, **kwargs):
        self.task_history = []
        self.exeuction_history = []
        self.history: Dict[str, List[TaskResult]] = {}
        super().__init__(name=name, role=role, *args, **kwargs)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name and data.task.id not in self.exeuction_history:
            self.exeuction_history.append(data.task.id)
            logger.info(f"{self.details().name} received subtask: {data.task.description}")
            result = await self.get_result(data.task)
            result_task = TaskResult(task_id=data.task.id,
                                     name=data.task.name,
                                     description=data.task.description,
                                     agent=self.details().name,
                                     parent_task_id=data.task.parent_task_id,
                                     result=result)
            # Update task history
            await self.add_result_to_history(result_task)
            await self.broadcast_data(result_task)

    @on_message(type=TaskResult)
    async def on_task_result(self, data: TaskResult):
        await self.add_result_to_history(data)

    async def add_result_to_history(self, data: TaskResult):
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
