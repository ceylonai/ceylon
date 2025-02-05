# Ceylon Task Processing Tutorial

This tutorial will guide you through using Ceylon's task processing system, demonstrating how to create workers, define
tasks, and manage task dependencies.

## Overview

Ceylon provides a flexible framework for distributed task processing with the following key components:

1. ProcessWorker - Base class for implementing task processors
2. Task - Represents a unit of work with optional dependencies
3. TaskProcessingPlayground - Manages task execution and dependencies

## Creating Workers

First, let's look at how to create task processors. A processor is responsible for executing specific types of tasks.

### Basic Worker Example

```python
from ceylon.processor.agent import ProcessWorker, ProcessRequest


class TextProcessor(ProcessWorker):
    """Worker that processes text-based tasks."""

    async def _processor(self, request: ProcessRequest, time: int):
        print(f"Processing text: {request}")
        data = request.data
        return data * 5
```

Key points about workers:

- Inherit from `ProcessWorker`
- Implement the `_processor` method
- Accept a `ProcessRequest` containing task data
- Return the processed result

### Worker with Dependencies

```python
class AggregateProcessor(ProcessWorker):
    """Worker that aggregates results from other tasks."""

    async def _processor(self, request: ProcessRequest, time: int):
        print(f"Aggregating text: {request}")
        data = request.data or 0
        for d in request.dependency_data.values():
            data += d.output
        return data
```

The `dependency_data` field in `ProcessRequest` contains results from dependent tasks.

## Defining Tasks

Tasks represent units of work to be processed. Here's how to create tasks:

```python
from ceylon.task.manager import Task

# Simple task
task1 = Task(
    name="Process Data 1",
    processor="multiply",  # Maps to worker role
    input_data={'data': 5}  # Data to be processed
)

# Task with dependencies
task3 = Task(
    name="Process Data 3",
    processor="aggregate",
    dependencies={task1.id, task2.id},  # Dependent task IDs
)
```

Key task attributes:

- name: Task identifier
- processor: Role of the worker to process this task
- input_data: Data to be processed
- dependencies: Set of task IDs this task depends on

## Setting Up the Playground

The playground orchestrates task execution:

```python
from ceylon.task.playground import TaskProcessingPlayground


async def main():
    # Create playground and workers
    playground = TaskProcessingPlayground()
    worker = TextProcessor("text_worker", role="multiply")
    aggregate_worker = AggregateProcessor("aggregate_worker", role="aggregate")

    # Start playground with workers
    async with playground.play(workers=[worker, aggregate_worker]) as active_playground:
# Execute tasks here
```

## Executing Tasks

Tasks can be executed individually or in groups:

```python
# Execute single task
task_result = await active_playground.add_and_execute_task(
    task=task1,
    wait_for_completion=True
)

print(f"Task: {task1.name}")
print(f"Result: {task_result.output}")
```

The playground handles:

- Task dependency resolution
- Worker assignment
- Result collection
- Error handling

## Complete Example

Here's a complete example demonstrating task processing with dependencies:

```python
import asyncio
from ceylon.processor.agent import ProcessWorker, ProcessRequest
from ceylon.task.manager import TaskResult, Task
from ceylon.task.playground import TaskProcessingPlayground


# Define workers
class TextProcessor(ProcessWorker):
    async def _processor(self, request: ProcessRequest, time: int):
        data = request.data
        return data * 5


class AggregateProcessor(ProcessWorker):
    async def _processor(self, request: ProcessRequest, time: int):
        data = request.data or 0
        for d in request.dependency_data.values():
            data += d.output
        return data


async def main():
    # Setup playground
    playground = TaskProcessingPlayground()
    worker = TextProcessor("text_worker", role="multiply")
    aggregate_worker = AggregateProcessor("aggregate_worker", role="aggregate")

    async with playground.play(workers=[worker, aggregate_worker]) as active_playground:
        # Create tasks
        task1 = Task(
            name="Process Data 1",
            processor="multiply",
            input_data={'data': 5}
        )

        task2 = Task(
            name="Process Data 2",
            processor="multiply",
            input_data={'data': 10}
        )

        task3 = Task(
            name="Process Data 3",
            processor="aggregate",
            dependencies={task1.id, task2.id},
        )

        # Execute tasks
        for task in [task1, task2, task3]:
            task_result = await active_playground.add_and_execute_task(
                task=task,
                wait_for_completion=True
            )
            print(f"\nTask: {task.name}")
            print(f"Result: {task_result.output}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

1. Error Handling
    - Workers should handle exceptions and return meaningful error messages
    - Use try/except blocks in processor implementations
    - Check task results for success/failure

2. Task Dependencies
    - Keep dependency chains manageable
    - Ensure no circular dependencies
    - Consider task execution order for efficiency

3. Resource Management
    - Use the async context manager (`async with`) for proper cleanup
    - Close workers and playground properly
    - Monitor resource usage in long-running tasks

4. Testing
    - Test workers independently
    - Verify dependency resolution
    - Test error handling scenarios
    - Validate task results

## Conclusion

Ceylon's task processing system provides a robust framework for distributed task execution with dependencies. Key
features include:

- Flexible worker implementation
- Automatic dependency management
- Asynchronous execution
- Error handling and recovery
- Resource cleanup

This system is particularly useful for:

- Data processing pipelines
- Multi-stage computations
- Distributed processing
- Workflow automation