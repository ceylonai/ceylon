import queue

from pydantic.dataclasses import dataclass

from ceylon.ceylon import AgentDefinition


@dataclass
class Task:
    task: str
    order_id: int
    executor_id: str


class TaskManager:
    def __init__(self):
        self.tasks = queue.Queue()
        self.agents = {}

    def register_agent(self, id: str, definition: AgentDefinition):
        self.agents[id] = definition

    def add_task(self, task: Task):
        self.tasks.put(task)
