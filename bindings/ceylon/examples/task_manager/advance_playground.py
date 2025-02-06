#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid
from loguru import logger

# Task States
class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Data Models
@dataclass
class TaskResult:
    success: bool
    output: Any = None
    error: Optional[str] = None

@dataclass
class Task:
    name: str
    processor: str  # Role identifier for the worker
    input_data: Dict[str, Any]
    id: str = str(uuid.uuid4())
    dependencies: set[str] = None
    state: TaskState = TaskState.PENDING
    result: Optional[TaskResult] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = set()

# Task Processing Worker
from ceylon.processor.agent import ProcessWorker
from ceylon.processor.data import ProcessRequest, ProcessResponse, ProcessState

class TaskWorker(ProcessWorker):
    def __init__(self, name: str, role: str):
        super().__init__(name=name, role=role)

    async def _processor(self, request: ProcessRequest, time: int) -> tuple[Any, dict]:
        try:
            # Process based on role
            if self.role == "math":
                result = await self.process_math(request.data)
            elif self.role == "text":
                result = await self.process_text(request.data)
            else:
                result = await self.process_default(request.data)

            return result, {"worker": self.name, "time": time}
        except Exception as e:
            raise Exception(f"Processing error: {str(e)}")

    async def process_math(self, data: Dict[str, Any]) -> Any:
        operation = data.get("operation")
        numbers = data.get("numbers", [])

        if operation == "sum":
            return sum(numbers)
        elif operation == "multiply":
            result = 1
            for num in numbers:
                result *= num
            return result
        else:
            raise ValueError(f"Unknown math operation: {operation}")

    async def process_text(self, data: str) -> str:
        return data.upper()

    async def process_default(self, data: Any) -> Any:
        return str(data)

# Task Processing Playground
from ceylon.task.playground import TaskProcessingPlayground

class CustomTaskPlayground(TaskProcessingPlayground):
    def __init__(self, name: str = "custom_playground", port: int = 8888):
        super().__init__(name=name, port=port)

    async def execute_task_sequence(self, tasks: list[Task]) -> Dict[str, TaskResult]:
        results = {}

        # Add all tasks first
        for task in tasks:
            self.task_manager.add_task(task)

        # Execute tasks in order of dependencies
        while len(results) < len(tasks):
            ready_tasks = []

            for task in tasks:
                if task.id not in results and all(dep in results for dep in task.dependencies):
                    ready_tasks.append(task)

            if not ready_tasks:
                raise Exception("Circular dependency detected")

            # Execute ready tasks in parallel
            execution_tasks = [
                self.add_and_execute_task(task, wait_for_completion=True)
                for task in ready_tasks
            ]

            task_results = await asyncio.gather(*execution_tasks)

            # Store results
            for task, result in zip(ready_tasks, task_results):
                results[task.id] = result

        return results

# Example usage
async def main():
    # Create playground and workers
    playground = CustomTaskPlayground()
    math_worker = TaskWorker("math_worker", "math")
    text_worker = TaskWorker("text_worker", "text")

    async with playground.play(workers=[math_worker, text_worker]) as pg:
        # Create tasks
        task1 = Task(
            name="Calculate Sum",
            processor="math",
            input_data={
                "operation": "sum",
                "numbers": [1, 2, 3, 4, 5]
            }
        )

        task2 = Task(
            name="Process Text",
            processor="text",
            input_data="hello world"
        )

        task3 = Task(
            name="Final Calculation",
            processor="math",
            input_data={
                "operation": "multiply",
                "numbers": [10]
            },
            dependencies={task1.id}
        )

        # Execute task sequence
        results = await pg.execute_task_sequence([task1, task2, task3])

        # Print results
        for task_id, result in results.items():
            task = pg.task_manager.get_task(task_id)
            print(f"\nTask: {task.name}")
            print(f"Result: {result.output}")

        await pg.finish()

if __name__ == "__main__":
    asyncio.run(main())