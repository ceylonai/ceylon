import datetime
from typing import List, Optional, Tuple, Set, Dict
from uuid import uuid4

import networkx as nx
from pydantic import BaseModel
from pydantic import Field


class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parent_task_id: Optional[str] = Field(default=None)
    name: str = Field(description="the name of the subtask write in snake_case")
    description: str = Field(description="the description of the subtask, Explains the task in detail")
    required_specialty: str = Field(description="the required specialty of the subtask")
    depends_on: Set[str] = Field(default_factory=set)
    completed: bool = False
    completed_at: Optional[float] = None

    result: Optional[str] = None
    executor: Optional[str] = None

    def complete(self, result: Optional[str] = None):
        self.result = result
        self.completed_at = datetime.datetime.now().timestamp()
        self.completed = True

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"SubTask: {self.name} (ID: {self.id}) - {status} - Dependencies: {self.depends_on}"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    subtasks: Dict[str, SubTask] = Field(default_factory=dict)

    execution_order: List[str] = Field(default_factory=list)

    def add_subtask(self, subtask: SubTask):
        subtask.parent_task_id = self.id
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

    def validate_sub_tasks(self) -> bool:
        subtask_names = set(self.subtasks.keys())

        # Check if all dependencies are present
        for subtask in self.subtasks.values():
            if not subtask.depends_on.issubset(subtask_names):
                missing_deps = subtask.depends_on - subtask_names
                print(f"Subtask '{subtask.name}' has missing dependencies: {missing_deps}")
                return False

        # Check for circular dependencies
        try:
            self._validate_dependencies()
        except ValueError as e:
            print(f"Circular dependency detected: {str(e)}")
            return False

        return True

    def get_execution_order(self) -> List[str]:
        graph = self._create_dependency_graph()
        return list(nx.topological_sort(graph))

    def get_next_subtask(self) -> Optional[Tuple[str, SubTask]]:
        for subtask_name in self.execution_order:
            subtask = self.subtasks[subtask_name]
            if all(self.subtasks[dep].completed for dep in subtask.depends_on):
                return (subtask_name, subtask)
        return None

    def update_subtask_status(self, subtask_name: str, result: str):
        if subtask_name not in self.subtasks:
            raise ValueError(f"Subtask {subtask_name} not found")

        subtask = self.subtasks[subtask_name]
        if result is not None:
            subtask.complete(result)

        if subtask_name in self.execution_order:
            self.execution_order.remove(subtask_name)

    def update_subtask_executor(self, subtask_name: str, executor: str) -> SubTask:
        if subtask_name not in self.subtasks:
            raise ValueError(f"Subtask {subtask_name} not found")
        subtask = self.subtasks[subtask_name]
        subtask.executor = executor
        return subtask

    def get_sub_task_by_name(self, subtask_name: str) -> SubTask:
        if subtask_name not in self.subtasks:
            raise ValueError(f"Subtask {subtask_name} not found")

        return self.subtasks[subtask_name]

    def is_completed(self) -> bool:
        return all(subtask.completed for subtask in self.subtasks.values())

    @property
    def sub_tasks(self) -> List[SubTask]:
        tasks = list(self.subtasks.values())
        tasks.sort(key=lambda x: x.completed_at)
        return tasks

    @property
    def final_answer(self) -> Optional[str]:
        if not self.is_completed() or len(self.sub_tasks) == 0:
            return None
        return self.sub_tasks[-1].result

    def __str__(self):
        return f"Task: {self.name}\nSubtasks:\n" + "\n".join(f"\t{st}" for st in self.subtasks)

    @staticmethod
    def create_task(name: str, description: str, subtasks: List[SubTask] = None) -> 'Task':
        task = Task(name=name, description=description)
        if subtasks:
            for subtask in subtasks:
                task.add_subtask(subtask)
        return task


class TaskAssignment(BaseModel):
    task: SubTask
    assigned_agent: str


class TaskResult(BaseModel):
    task_id: str
    parent_task_id: str
    agent: str
    result: str
    name: str
    description: str


if __name__ == "__main__":
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


    # Create a task with initial subtasks
    web_app = Task.create_task("Build Web App", "Create a simple web application",
                               subtasks=[
                                   SubTask(name="setup", description="Set up the development environment",
                                           required_specialty="Knowledge about deployment and development tools"),
                                   SubTask(name="database", description="Set up the database",
                                           required_specialty="Knowledge about database management tools"),
                                   SubTask(name="testing", description="Perform unit and integration tests",
                                           depends_on={"backend", "frontend"},
                                           required_specialty="Knowledge about testing tools"),
                                   SubTask(name="frontend", description="Develop the frontend UI",
                                           depends_on={"setup", "backend"},
                                           required_specialty="Knowledge about frontend tools"),
                                   SubTask(name="backend", description="Develop the backend API",
                                           depends_on={"setup", "database"},
                                           required_specialty="Knowledge about backend tools"),
                                   SubTask(name="deployment", description="Deploy the application",
                                           depends_on={"testing", "qa"},
                                           required_specialty="Knowledge about deployment tools and CI tools"),
                                   SubTask(name="delivery", description="Deploy the application",
                                           depends_on={"deployment"},
                                           required_specialty="Knowledge about delivery tools"),
                                   SubTask(name="qa", description="Perform quality assurance",
                                           depends_on={"testing"},
                                           required_specialty="Knowledge about testing tools")
                               ])

    # Execute the task
    print("Execution order:", [web_app.subtasks[task_id].name for task_id in web_app.get_execution_order()])

    if web_app.validate_sub_tasks():
        print("Subtasks are valid")

        print("\nExecuting task:")
        execute_task(task=web_app)

        print("\nFinal task status:")
        print(web_app)
    else:
        print("Subtasks are invalid")

        # Serialization example
    print("\nSerialized Task:")
    print(web_app.model_dump_json(indent=2))
