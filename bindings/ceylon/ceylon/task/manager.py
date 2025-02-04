from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from ceylon.task.data import Task, TaskResult, TaskStatus


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.logger = logging.getLogger(__name__)

    def add_task(
            self,
            task: Task,
    ) -> str:
        """
        Add a new task to the task manager.

        Args:
            task (Task): The task to be added.

        Returns:
            str: ID of the created task
        """
        self.tasks[task.id] = task
        return task.id

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
                if dep_id not in self.tasks:
                    raise ValueError(f"Dependency {dep_id} not found")
                dep_task = self.tasks[dep_id]
                if dep_task.result and dep_task.result.success:
                    dep_outputs[dep_id] = dep_task.result.output

            # Add dependency outputs to input data
            execution_data = {
                **task.input_data,
                'dependency_outputs': dep_outputs
            }

            # Execute the task process asynchronously
            output = await task.processor(execution_data)

            result = TaskResult(success=True, output=output)
            task.status = TaskStatus.COMPLETED

        except Exception as e:
            import traceback
            traceback.print_exc()
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
    task1_id = manager.add_task(Task(
        name="Process Data 1",
        processor=process_data,
        input_data={'data': 5}
    )
    )

    task2_id = manager.add_task(
        Task(
            name="Process Data 2",
            processor=process_data,
            input_data={'data': 10}
        )
    )

    task3_id = manager.add_task(
        Task(
            name="Aggregate Results",
            processor=aggregate_results,
            input_data={},
            dependencies={task1_id, task2_id}
        )
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
