import datetime
import enum
from typing import List, Optional, Tuple, Set, Dict
from uuid import uuid4

import networkx as nx
from loguru import logger
from pydantic import BaseModel
from pydantic import Field
import asyncio


class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parent_task_id: Optional[str] = Field(default=None)
    name: str = Field(description="the name of the subtask write in snake_case")
    description: str = Field(description="the description of the subtask, Explains the task in detail")
    required_specialty: str = Field(description="the required specialty of the subtask", default="")
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


class TaskDeliverable(BaseModel):
    objective: str = Field(
        description="The main objective of the task",
        default=""
    )
    deliverable: str = Field(
        description="The single, primary deliverable for the task",
        default=""
    )
    key_features: List[str] = Field(
        description="Key features of the deliverable",
        default=[]
    )
    considerations: List[str] = Field(
        description="Important considerations or constraints for the deliverable",
        default=[]
    )

    def __str__(self):
        return f"TaskDeliverable: {self.deliverable} - Key Features: {self.key_features} - Considerations: {self.considerations} - Objective: {self.objective}"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    subtasks: Dict[str, SubTask] = Field(default_factory=dict)

    execution_order: List[str] = Field(default_factory=list)

    metadata: Dict[str, str] = Field(default_factory=dict, alias="metadata", description="metadata")
    task_deliverable: TaskDeliverable = Field(default=None)

    max_subtasks: int = Field(default=5, description="max number of subtasks")

    def add_subtask(self, subtask: SubTask):
        subtask.parent_task_id = self.id
        self.subtasks[subtask.name] = subtask
        self._validate_dependencies()
        self.execution_order = self.get_execution_order()

    def set_deliverable(self, task_deliverable: TaskDeliverable):
        self.task_deliverable = task_deliverable

    def _validate_dependencies(self):
        graph = self._create_dependency_graph()
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("The dependencies create a cycle")

    def _create_dependency_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for subtask in self.subtasks.values():
            graph.add_node(subtask.name)
            for dep in subtask.depends_on:
                if dep in self.subtasks:
                    graph.add_edge(dep, subtask.name)
        return graph

    def validate_sub_tasks(self) -> bool:
        subtask_names = set(self.subtasks.keys())

        for subtask in self.subtasks.values():
            if not subtask.depends_on.issubset(subtask_names):
                missing_deps = subtask.depends_on - subtask_names
                logger.info(f"Subtask '{subtask.name}' has missing dependencies: {missing_deps}")
                return False

        try:
            self._validate_dependencies()
        except ValueError as e:
            print(f"Circular dependency detected: {str(e)}")
            return False

        return True

    def get_execution_order(self) -> List[str]:
        graph = self._create_dependency_graph()
        return list(nx.topological_sort(graph))

    def get_ready_subtasks(self) -> List[Tuple[str, SubTask]]:
        ready_subtasks = []
        for subtask_name in self.execution_order:
            subtask = self.subtasks[subtask_name]
            if not subtask.completed and all(self.subtasks[dep].completed for dep in subtask.depends_on):
                ready_subtasks.append((subtask_name, subtask))
        return ready_subtasks

    def update_subtask_status(self, subtask_name: str, result: str):
        if subtask_name not in self.subtasks:
            raise ValueError(f"Subtask {subtask_name} not found")

        subtask = self.subtasks[subtask_name]
        if result is not None:
            subtask.complete(result)

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
        return f"Task: {self.name}\nSubtasks:\n" + "\n".join(f"\t{st}" for st in self.subtasks.values())

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


class TaskResultStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SubTaskResult(BaseModel):
    task_id: str
    parent_task_id: str
    agent: str
    result: str
    name: str
    description: str
    status: TaskResultStatus


class TaskResult(BaseModel):
    task_id: str
    final_answer: str


async def execute_subtask(subtask_name: str, subtask: SubTask) -> str:
    print(f"Executing: {subtask}")
    # Simulate subtask execution with a delay
    await asyncio.sleep(1)
    return f"Success: {subtask_name}"


async def execute_task(task: Task) -> None:
    while not task.is_completed():
        ready_subtasks = task.get_ready_subtasks()
        print(f"Ready subtasks: {ready_subtasks}")

        if not ready_subtasks:
            await asyncio.sleep(0.1)
            continue

        # Execute ready subtasks in parallel
        subtask_coroutines = [execute_subtask(name, subtask) for name, subtask in ready_subtasks]
        results = await asyncio.gather(*subtask_coroutines)

        # Update task status
        for (subtask_name, _), result in zip(ready_subtasks, results):
            task.update_subtask_status(subtask_name, result)
            print(f"Completed: {subtask_name}")

    print("All subtasks completed successfully!")


if __name__ == "__main__":
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
                                   SubTask(name="qa_test_cases", description="Perform unit and integration tests",
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
                                           depends_on={"testing", "qa_test_cases"},
                                           required_specialty="Knowledge about testing tools")
                               ])

    print("Execution order:", [web_app.subtasks[task_id].name for task_id in web_app.get_execution_order()])

    if web_app.validate_sub_tasks():
        print("Subtasks are valid")

        print("\nExecuting task:")
        asyncio.run(execute_task(task=web_app))

        print("\nFinal task status:")
        print(web_app)
    else:
        print("Subtasks are invalid")

    # Serialization example
    print("\nSerialized Task:")
    print(web_app.model_dump_json(indent=2))
