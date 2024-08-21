from typing import List, Dict

from loguru import logger

from ceylon import CoreAdmin, on_message
from ceylon.ceylon import AgentDetail
from ceylon.task import Task, SubTaskResult, TaskAssignment, SubTask
from ceylon.task.task_operation import TaskResultStatus, TaskResult
from ceylon.task.task_operator import TaskOperator


class TaskCoordinator(CoreAdmin):
    tasks: List[Task] = []
    agents: List[TaskOperator] = []
    results: Dict[str, List[SubTaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[TaskOperator], name="ceylon_agent_stack", port=8888, *args,
                 **kwargs):
        self.tasks = tasks
        self.agents = agents
        super().__init__(name=name, port=port, *args, **kwargs)

    async def update_task(self, idx: int, task: Task) -> Task:
        return task

    async def get_task_executor(self, task: SubTask) -> str:
        return task.executor

    async def run(self, inputs: bytes):
        for idx, task in enumerate(self.tasks):
            task = await self.update_task(idx, task)
            logger.info(f"Validating task {task.name}")
            if task.validate_sub_tasks():
                logger.info(f"Task {task.name} is valid")
            else:
                logger.info(f"Task {task.name} is invalid")
                del self.tasks[idx]

        await self.run_tasks()

    async def run_tasks(self):
        if len(self.tasks) == 0:
            logger.info("No tasks found")
            return
        for task in self.tasks:
            self.results[task.id] = []
            sub_task = task.get_next_subtask()
            if sub_task is None:
                continue
            subtask_name, subtask_ = sub_task
            assigned_agent = await self.get_task_executor(subtask_)
            subtask_ = task.update_subtask_executor(subtask_name, assigned_agent)
            logger.debug(f"Assigned agent {subtask_.executor} to subtask {subtask_name}")
            await self.broadcast_data(
                TaskAssignment(task=subtask_, assigned_agent=subtask_.executor))

    @on_message(type=SubTaskResult)
    async def on_task_result(self, result: SubTaskResult):
        logger.info(f"Received task result: {result}")
        if result.status == TaskResultStatus.COMPLETED:
            for idx, task in enumerate(self.tasks):
                sub_task = task.get_next_subtask()
                print(result.task_id, sub_task[1].id, result.task_id == sub_task[1].id)
                if sub_task is None or result.task_id != sub_task[1].id:
                    continue
                if result.task_id == sub_task[1].id:
                    task.update_subtask_status(sub_task[1].name, result.result)
                    break

            # Task is completed
            for task in self.tasks:
                if task.is_completed():
                    if task.id == result.task_id:
                        await self.broadcast_data(TaskResult(task_id=task.id, result=result.result))

            if self.all_tasks_completed():
                await self.end_task_management()

        await self.run_tasks()

    def all_tasks_completed(self) -> bool:
        for task in self.tasks:
            subtask_completed_status = [st.completed for st in task.subtasks.values()]
            if not all(subtask_completed_status):
                return False
        return True

    async def end_task_management(self):
        logger.info("All tasks completed. Results:")
        for task in self.tasks:
            logger.info(f"Task {task.id} results:")
            for result in self.results[task.id]:
                logger.info(f"  Subtask {result.subtask_id}: {result.result}")
        await self.stop()

    def do(self, inputs: bytes) -> List[Task]:
        self.run_admin(inputs, self.agents)
        return self.tasks

    async def async_do(self, inputs: bytes) -> List[Task]:
        await self.arun_admin(inputs, self.agents)
        return self.tasks

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        await super().on_agent_connected(topic, agent)
        logger.info(f"Agent connected: {agent}")
        await self.run_tasks()
