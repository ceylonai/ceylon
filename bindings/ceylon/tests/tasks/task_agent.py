from uuid import UUID, uuid4
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
import networkx as nx
from ceylon import Agent, CoreAdmin, on_message


# Data Models
class SubTask(BaseModel):
    id: str
    name: str
    description: str
    depends_on: Set[str] = Field(default_factory=set)
    completed: bool = False

    def complete(self):
        self.completed = True

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"SubTask: {self.name} (ID: {self.id}) - {status}"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias='_id')
    name: str
    description: str
    subtasks: Dict[str, SubTask] = Field(default_factory=dict)

    def add_subtask(self, subtask: SubTask):
        if subtask.id in self.subtasks:
            raise ValueError(f"Subtask with id {subtask.id} already exists")
        self.subtasks[subtask.id] = subtask
        self._validate_dependencies()

    def _validate_dependencies(self):
        graph = self._create_dependency_graph()
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("The dependencies create a cycle")

    def _create_dependency_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for subtask in self.subtasks.values():
            graph.add_node(subtask.id)
            for dependency_id in subtask.depends_on:
                if dependency_id not in self.subtasks:
                    raise ValueError(f"Dependency {dependency_id} does not exist")
                graph.add_edge(dependency_id, subtask.id)
        return graph

    def get_execution_order(self) -> List[str]:
        graph = self._create_dependency_graph()
        return list(nx.topological_sort(graph))

    def __str__(self):
        return f"Task: {self.name}\nSubtasks:\n" + "\n".join(str(st) for st in self.subtasks.values())


# Messages
class TaskAssignment(BaseModel):
    task_id: str
    subtask_id: str


class SubTaskCompletion(BaseModel):
    task_id: str
    subtask_id: str


# Admin Agent
class TaskManagerAdmin(CoreAdmin):
    tasks: Dict[str, Task] = {}
    in_progress: Dict[str, Set[str]] = {}

    def __init__(self):
        super().__init__(name="task_manager", port=8000)

    def create_task(self, name: str, description: str, subtasks: List[SubTask] = None) -> Task:
        task = Task(name=name, description=description)
        if subtasks:
            for subtask in subtasks:
                task.add_subtask(subtask)
        print(f"Created task: {task}")
        self.tasks[task.id] = task
        self.in_progress[task.id] = set()
        return task

    async def execute_task(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            print(f"Task with id {task_id} not found")
            return

        execution_order = task.get_execution_order()
        for subtask_id in execution_order:
            subtask = task.subtasks[subtask_id]
            if not subtask.completed and subtask_id not in self.in_progress[task_id]:
                self.in_progress[task_id].add(subtask_id)
                await self.broadcast_data(TaskAssignment(task_id=task_id, subtask_id=subtask_id))

    @on_message(type=SubTaskCompletion)
    async def on_subtask_completion(self, data: SubTaskCompletion):
        task = self.tasks.get(data.task_id)
        if not task:
            print(f"Task with id {data.task_id} not found")
            return

        subtask = task.subtasks.get(data.subtask_id)
        if not subtask:
            print(f"Subtask with id {data.subtask_id} not found in task {data.task_id}")
            return

        subtask.complete()
        self.in_progress[data.task_id].remove(data.subtask_id)
        print(f"Subtask {subtask.name} completed")

        # Check if all subtasks are completed
        if all(st.completed for st in task.subtasks.values()):
            print(f"Task {task.name} completed")
        else:
            # Continue executing remaining subtasks
            await self.execute_task(data.task_id)


# Worker Agent
class WorkerAgent(Agent):
    def __init__(self, name: str):
        super().__init__(name=name, workspace_id="task_manager", admin_peer="TaskManagerAdmin", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        print(f"{self.details().name} received subtask assignment: {data.subtask_id}")
        # Simulate work by waiting for a short time
        await asyncio.sleep(2)
        print(f"{self.details().name} completed subtask: {data.subtask_id}")
        await self.broadcast_data(SubTaskCompletion(task_id=data.task_id, subtask_id=data.subtask_id))


# Example usage
async def main():
    admin = TaskManagerAdmin()
    workers = [WorkerAgent(f"Worker-{i}") for i in range(3)]

    # Create subtasks
    subtasks = [
        SubTask(id="setup", name="Setup", description="Set up the development environment"),
        SubTask(id="database", name="Database", description="Set up the database"),
        SubTask(id="backend", name="Backend", description="Develop the backend API", depends_on={"setup", "database"}),
        SubTask(id="frontend", name="Frontend", description="Develop the frontend UI", depends_on={"setup"}),
        SubTask(id="testing", name="Testing", description="Perform unit and integration tests",
                depends_on={"backend", "frontend"}),
        SubTask(id="deployment", name="Deployment", description="Deploy the application", depends_on={"testing"})
    ]

    # Create a task with initial subtasks
    web_app = admin.create_task("Build Web App", "Create a simple web application", subtasks=subtasks)

    print("Execution order:", [web_app.subtasks[task_id].name for task_id in web_app.get_execution_order()])
    print("\nStarting task execution:")

    await admin.arun_admin(
        inputs=pickle.dumps({"task_id": web_app.id}),
        workers=workers
    )


if __name__ == "__main__":
    import asyncio
    import pickle

    asyncio.run(main())
