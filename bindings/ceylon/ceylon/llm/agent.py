from loguru import logger

from ceylon import Agent, on_message
from ceylon.llm.data_types import TaskAssignment, TaskResult


class SpecializedAgent(Agent):
    def __init__(self, name: str, specialty: str):
        self.specialty = specialty
        super().__init__(name=name, workspace_id="openai_task_management", admin_peer="TaskManager", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.subtask.description}")
            # Simulate task execution
            # await asyncio.sleep(2)
            result = f"{self.details().name} completed the subtask: {data.subtask.description}"
            await self.broadcast_data(
                TaskResult(task_id=data.task.id, subtask_id=data.subtask.id, agent=self.details().name, result=result))

    @on_message(type=TaskResult)
    async def other_agents_results(self, result: TaskResult):
        logger.info(
            f"Received result for subtask {result.subtask_id} of task {result.task_id} from {result.agent}: {result.result}")
