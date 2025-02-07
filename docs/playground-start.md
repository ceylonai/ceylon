# Getting Started with Ceylon Playground

Ceylon is a distributed task processing framework that enables building scalable agent-based systems. This guide will walk you through creating your first Ceylon application using the Playground system.

## Core Concepts

- **Playground**: A central coordinator that manages workers and task distribution
- **ProcessWorker**: Handles specific types of tasks
- **Task**: A unit of work with optional dependencies
- **ProcessRequest/Response**: Communication protocol between playground and workers

## Basic Example: Text Processing System

Let's create a simple system that processes text. We'll build:
1. A text processor that multiplies input
2. An aggregator that combines results
3. A playground to coordinate them

```python
import asyncio
from ceylon.processor.agent import ProcessWorker, ProcessRequest
from ceylon.task.manager import Task
from ceylon.task.playground import TaskProcessingPlayground

class TextProcessor(ProcessWorker):
    """Processes text-based tasks."""
    
    async def _processor(self, request: ProcessRequest, time: int):
        data = request.data
        return data * 5

class AggregateProcessor(ProcessWorker):
    """Aggregates results from multiple tasks."""
    
    async def _processor(self, request: ProcessRequest, time: int):
        data = request.data or 0
        for d in request.dependency_data.values():
            data += d.output
        return data

async def main():
    # Initialize playground and workers
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
            name="Aggregate Results",
            processor="aggregate",
            dependencies={task1.id, task2.id}
        )

        # Execute tasks
        for task in [task1, task2, task3]:
            result = await active_playground.add_and_execute_task(
                task=task,
                wait_for_completion=True
            )
            print(f"Task: {task.name}, Result: {result.output}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Components Explained

### 1. ProcessWorker
- Base class for task processors
- Implements `_processor` method to handle specific task types
- Can access request data and metadata

```python
class CustomWorker(ProcessWorker):
    async def _processor(self, request: ProcessRequest, time: int) -> tuple[Any, dict]:
        result = process_data(request.data)
        metadata = {"processed_at": time}
        return result, metadata
```

### 2. TaskProcessingPlayground
- Manages worker connections
- Coordinates task execution
- Handles dependencies between tasks

```python
playground = TaskProcessingPlayground(name="my_playground", port=8888)
async with playground.play(workers=[worker1, worker2]) as active_playground:
    # Execute tasks here
```

### 3. Task
- Represents a unit of work
- Can specify dependencies on other tasks
- Contains input data and processor type

```python
task = Task(
    name="MyTask",
    processor="worker_role",  # Must match worker's role
    input_data={'key': 'value'},
    dependencies={other_task.id}  # Optional dependencies
)
```

## Advanced Features

### 1. Task Dependencies
Ceylon supports complex task dependencies:

```python
task_a = Task(name="A", processor="role_1", input_data={'data': 1})
task_b = Task(name="B", processor="role_2", input_data={'data': 2})
task_c = Task(
    name="C",
    processor="role_3",
    dependencies={task_a.id, task_b.id}
)
```

### 2. Error Handling
Workers can handle errors gracefully:

```python
async def _processor(self, request: ProcessRequest, time: int):
    try:
        result = process_data(request.data)
        return result, {"status": "success"}
    except Exception as e:
        raise Exception(f"Processing failed: {str(e)}")
```

### 3. Custom Metadata
Add metadata to track processing details:

```python
async def _processor(self, request: ProcessRequest, time: int):
    result = process_data(request.data)
    metadata = {
        "processing_time": time,
        "data_size": len(request.data),
        "processor_version": "1.0"
    }
    return result, metadata
```

## Best Practices

1. **Worker Design**
    - Keep workers focused on single responsibilities
    - Use meaningful role names
    - Include proper error handling

2. **Task Management**
    - Break complex operations into smaller tasks
    - Use clear naming conventions
    - Carefully manage dependencies

3. **Resource Handling**
    - Use async context managers for cleanup
    - Implement proper shutdown procedures
    - Monitor worker health

## Common Patterns

### 1. Pipeline Processing
```python
async def create_pipeline():
    task1 = Task(name="Extract", processor="extractor")
    task2 = Task(name="Transform", processor="transformer",
                 dependencies={task1.id})
    task3 = Task(name="Load", processor="loader",
                 dependencies={task2.id})
    return [task1, task2, task3]
```

### 2. Parallel Processing
```python
tasks = [
    Task(name=f"Process_{i}", processor="worker")
    for i in range(5)
]
results = await playground.execute_task_group(tasks)
```

## Debugging Tips

1. Enable detailed logging:
```python
from loguru import logger
logger.add("debug.log", level="DEBUG")
```

2. Monitor task states:
```python
task_status = playground.task_manager.get_task(task_id).status
print(f"Task {task_id} status: {task_status}")
```

3. Check worker connections:
```python
connected_workers = playground.llm_agents
print(f"Connected workers: {connected_workers}")
```

## Next Steps

- Explore more complex task dependencies
- Implement custom error handling strategies
- Add monitoring and metrics collection
- Scale your system with additional workers
- Implement custom task scheduling logic
