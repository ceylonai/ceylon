from typing import Any, Callable, Dict, List, Set, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import uuid
import logging
import asyncio


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TaskResult:
    success: bool
    output: Any = None
    error: str = None


@dataclass
class Task:
    name: str
    process: Callable[..., Coroutine]  # Updated to expect a coroutine
    input_data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: TaskResult = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.logger = logging.getLogger(__name__)

    def add_task(
            self,
            name: str,
            process: Callable[..., Coroutine],
            input_data: Dict[str, Any],
            dependencies: Set[str] = None
    ) -> str:
        """
        Add a new task to the task manager.

        Args:
            name: Name of the task
            process: Async callable that will process the task
            input_data: Dictionary of input data for the task
            dependencies: Set of task IDs that this task depends on

        Returns:
            str: ID of the created task
        """
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            process=process,
            input_data=input_data,
            dependencies=dependencies or set()
        )
        self.tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Task:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to be executed (dependencies completed)."""
        ready_tasks = []
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING and self._are_dependencies_completed(task):
                ready_tasks.append(task)
        return ready_tasks

    def _are_dependencies_completed(self, task: Task) -> bool:
        """Check if all dependencies of a task are completed."""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a single task asynchronously."""
        try:
            task.status = TaskStatus.RUNNING
            self.logger.info(f"Executing task: {task.name} ({task.id})")

            # Gather dependency outputs if needed
            dep_outputs = {}
            for dep_id in task.dependencies:
                dep_task = self.tasks[dep_id]
                if dep_task.result and dep_task.result.success:
                    dep_outputs[dep_id] = dep_task.result.output

            # Add dependency outputs to input data
            execution_data = {
                **task.input_data,
                'dependency_outputs': dep_outputs
            }

            # Execute the task process asynchronously
            output = await task.process(execution_data)

            result = TaskResult(success=True, output=output)
            task.status = TaskStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Task failed: {task.name} ({task.id}). Error: {str(e)}")
            result = TaskResult(success=False, error=str(e))
            task.status = TaskStatus.FAILED

        task.result = result
        return result

    async def execute_all_tasks(self) -> Dict[str, TaskResult]:
        """
        Execute all tasks in dependency order asynchronously.
        Returns a dictionary mapping task IDs to their results.
        """
        results = {}

        while True:
            ready_tasks = self.get_ready_tasks()
            if not ready_tasks:
                break

            # Execute ready tasks concurrently
            tasks = [self.execute_task(task) for task in ready_tasks]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for task, result in zip(ready_tasks, task_results):
                if isinstance(result, Exception):
                    results[task.id] = TaskResult(success=False, error=str(result))
                    task.status = TaskStatus.FAILED
                    self.logger.error(f"Task {task.name} failed. Stopping execution.")
                    return results
                results[task.id] = result

        return results


# Example usage
async def example_usage():
    # Create a task manager
    manager = TaskManager()

    # Define some example task processes
    async def process_data(input_data):
        data = input_data['data']
        # Simulate some async work
        await asyncio.sleep(1)
        return {'processed': data * 2}

    async def aggregate_results(input_data):
        dep_outputs = input_data['dependency_outputs']
        # Simulate some async work
        await asyncio.sleep(0.5)
        return {'total': sum(d['processed'] for d in dep_outputs.values())}

    # Add tasks
    task1_id = manager.add_task(
        name="Process Data 1",
        process=process_data,
        input_data={'data': 5}
    )

    task2_id = manager.add_task(
        name="Process Data 2",
        process=process_data,
        input_data={'data': 10}
    )

    task3_id = manager.add_task(
        name="Aggregate Results",
        process=aggregate_results,
        input_data={},
        dependencies={task1_id, task2_id}
    )

    # Execute all tasks
    results = await manager.execute_all_tasks()

    # Print results
    for task_id, result in results.items():
        task = manager.get_task(task_id)
        print(f"Task: {task.name}")
        print(f"Status: {task.status}")
        print(f"Result: {result.output}")
        print("---")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())