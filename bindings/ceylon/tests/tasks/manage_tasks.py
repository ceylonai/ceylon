import networkx as nx
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from ceylon.core.admin import Admin
from ceylon.core.worker import Worker


class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias='_id')
    name: str
    description: str
    depends_on: Set[str] = Field(default_factory=set)
    completed: bool = False

    def complete(self):
        self.completed = True

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"SubTask: {self.name} (ID: {self.id}) - {status} - Dependencies: {self.depends_on}"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias='_id')
    name: str
    description: str
    subtasks: Dict[str, SubTask] = Field(default_factory=dict)

    def add_subtask(self, subtask: SubTask):
        if subtask.name in self.subtasks:
            raise ValueError(f"Subtask with id {subtask.name} already exists")

        self.subtasks[subtask.name] = subtask
        self._validate_dependencies()

    def _validate_dependencies(self):
        graph = self._create_dependency_graph()
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("The dependencies create a cycle")

    def _create_dependency_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for subtask in self.subtasks.values():
            graph.add_node(subtask.name)
        return graph

    def get_execution_order(self) -> List[str]:
        graph = self._create_dependency_graph()
        return list(nx.topological_sort(graph))

    def execute(self):
        execution_order = self.get_execution_order()
        for subtask_id in execution_order:
            subtask = self.subtasks[subtask_id]
            if not subtask.completed:
                print(f"Executing: {subtask}")
                subtask.complete()

    def __str__(self):
        return f"Task: {self.name}\nSubtasks:\n" + "\n".join(str(st) for st in self.subtasks.values())


class TaskManager(BaseModel):
    tasks: Dict[str, Task] = Field(default_factory=dict)

    def create_task(self, name: str, description: str, subtasks: List[SubTask] = None) -> Task:
        task = Task(name=name, description=description)
        if subtasks:
            for subtask in subtasks:
                task.add_subtask(subtask)
        self.tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def list_tasks(self):
        for task in self.tasks.values():
            print(task)
            print()


class TaskWorker(Worker):
    pass


class TaskAdmin(Admin):
    pass


# Example usage
if __name__ == "__main__":
    manager = TaskManager()

    # Create subtasks
    subtasks = [
        SubTask(name="setup", description="Set up the development environment"),
        SubTask(name="database", description="Set up the database"),
        SubTask(name="testing", description="Perform unit and integration tests",
                depends_on={"backend", "frontend"}),
        SubTask(name="frontend", description="Develop the frontend UI", depends_on={"setup", "backend"}),
        SubTask(name="backend", description="Develop the backend API", depends_on={"setup", "database"}),
        SubTask(name="deployment", description="Deploy the application", depends_on={"testing"})
    ]

    # Create a task with initial subtasks
    web_app = manager.create_task("Build Web App", "Create a simple web application", subtasks=subtasks)

    # Execute the task
    print("Execution order:", [web_app.subtasks[task_id].name for task_id in web_app.get_execution_order()])
    print("\nExecuting task:")
    web_app.execute()

    print("\nFinal task status:")
    print(web_app)

    # Serialization example
    print("\nSerialized Task:")
    print(web_app.model_dump_json(indent=2))
