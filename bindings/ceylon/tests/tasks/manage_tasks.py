from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

import networkx as nx
from pydantic import BaseModel, Field

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

    execution_order: List[str] = Field(default_factory=list)

    def add_subtask(self, subtask: SubTask):
        if subtask.name in self.subtasks:
            raise ValueError(f"Subtask with id {subtask.name} already exists")

        self.subtasks[subtask.name] = subtask
        self._validate_dependencies()
        self.execution_order = self.get_execution_order()

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

    def get_next_subtask(self) -> Optional[Tuple[str, SubTask]]:
        for subtask_name in self.execution_order:
            subtask = self.subtasks[subtask_name]
            if all(self.subtasks[dep].completed for dep in subtask.depends_on):
                return (subtask_name, subtask)
        return None

    def update_subtask_status(self, subtask_name: str, result: bool):
        if subtask_name not in self.subtasks:
            raise ValueError(f"Subtask {subtask_name} not found")

        subtask = self.subtasks[subtask_name]
        if result:
            subtask.complete()

        if subtask_name in self.execution_order:
            self.execution_order.remove(subtask_name)

    def is_completed(self) -> bool:
        return all(subtask.completed for subtask in self.subtasks.values())

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


def execute_task(task: Task) -> None:
    while True:
        # Get the next subtask
        next_subtask: Optional[tuple[str, SubTask]] = task.get_next_subtask()

        # If there are no more subtasks, break the loop
        if next_subtask is None:
            break

        subtask_name, subtask = next_subtask
        print(f"Executing: {subtask}")

        # Here you would actually execute the subtask
        # For this example, we'll simulate execution with a simple print statement
        print(f"Simulating execution of {subtask_name}")

        # Simulate a result (in a real scenario, this would be the outcome of the subtask execution)
        result = True

        # Update the subtask status
        task.update_subtask_status(subtask_name, result)

        # Check if the entire task is completed
        if task.is_completed():
            print("All subtasks completed successfully!")
            break

    # Final check to see if all subtasks were completed
    if task.is_completed():
        print("Task execution completed successfully!")
    else:
        print("Task execution incomplete. Some subtasks may have failed.")


# Example usage
if __name__ == "__main__":
    manager = TaskManager()
    # Create a task with initial subtasks
    web_app = manager.create_task("Build Web App", "Create a simple web application",
                                  subtasks=[
                                      SubTask(name="setup", description="Set up the development environment"),
                                      SubTask(name="database", description="Set up the database"),
                                      SubTask(name="testing", description="Perform unit and integration tests",
                                              depends_on={"backend", "frontend"}),
                                      SubTask(name="frontend", description="Develop the frontend UI",
                                              depends_on={"setup", "backend"}),
                                      SubTask(name="backend", description="Develop the backend API",
                                              depends_on={"setup", "database"}),
                                      SubTask(name="deployment", description="Deploy the application",
                                              depends_on={"testing", "qa"}),
                                      SubTask(name="delivery", description="Deploy the application",
                                              depends_on={"deployment"})
                                  ])

    # Execute the task
    print("Execution order:", [web_app.subtasks[task_id].name for task_id in web_app.get_execution_order()])
    print("\nExecuting task:")
    execute_task(task=web_app)

    print("\nFinal task status:")
    print(web_app)

    # Serialization example
    print("\nSerialized Task:")
    print(web_app.model_dump_json(indent=2))
