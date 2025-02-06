# Building Distributed Task Processing Systems with Ceylon

This tutorial demonstrates how to build a distributed task processing system using Ceylon's TaskProcessingPlayground. We'll create a system where multiple workers process tasks based on their skill levels.

## Core Concepts

### TaskProcessingPlayground
- Central coordinator for distributed task processing
- Manages task distribution and execution
- Handles worker coordination and result collection

### ProcessWorker
- Individual processing units
- Implements specific task logic
- Can maintain internal state and configurations

### Task
- Represents a unit of work
- Contains input data and processing instructions
- Can have dependencies on other tasks

## Message Passing

````mermaid
sequenceDiagram
    participant TM as TaskManager
    participant W1 as Junior(skill=3)
    participant W2 as Intermediate(skill=6)
    participant W3 as Senior(skill=9)
    
    Note over TM,W3: Connection Phase
    W1->>TM: Connect
    W2->>TM: Connect
    W3->>TM: Connect
    
    Note over TM,W3: Task Assignment Phase
    TM->>W1: TaskAssignment(Task 1, difficulty=2)
    TM->>W2: TaskAssignment(Task 2, difficulty=5)
    TM->>W3: TaskAssignment(Task 3, difficulty=8)
    
    Note over TM,W3: Task Processing Phase
    par Process Tasks
        W1-->>TM: TaskResult(id=1, success=true)
        W2-->>TM: TaskResult(id=2, success=true)
        W3-->>TM: TaskResult(id=3, success=true)
    end
    
    Note over TM: Calculate Success Rate
    Note over TM: End Task Management
````
The diagram illustrates a distributed task management system where a central TaskManager coordinates with multiple worker agents. Each worker has a different skill level (3, 6, and 9) and can handle tasks of varying difficulty (2, 5, and 8). The workflow begins with workers connecting to the TaskManager, followed by task assignments based on availability. Workers process their assigned tasks in parallel, with success determined by whether their skill level exceeds the task's difficulty. Once all tasks are complete, the TaskManager calculates the overall success rate before shutting down.
## Implementation Guide

### 1. Define Your Task Structure

```python
@dataclass
class WorkTask:
    id: int
    description: str
    difficulty: int
```

This structure defines what information each task contains. Customize fields based on your needs.

### 2. Create a Worker Processor

```python
class WorkerProcessor(ProcessWorker):
    def __init__(self, name: str, skill_level: int):
        super().__init__(name=name, role="worker")
        self.skill_level = skill_level

    async def _processor(self, request: ProcessRequest, time: int) -> tuple[bool, dict]:
        task = request.data
        await asyncio.sleep(task.difficulty)  # Simulate work
        success = self.skill_level >= task.difficulty
        return success, {
            "task_id": task.id,
            "worker": self.name,
            "difficulty": task.difficulty
        }
```

Key points:
- Inherit from ProcessWorker
- Initialize with worker-specific attributes
- Implement _processor method to handle tasks
- Return results and metadata

### 3. Set Up the Playground

```python
playground = TaskProcessingPlayground(name="task_playground", port=8000)
workers = [
    WorkerProcessor("Junior", skill_level=3),
    WorkerProcessor("Intermediate", skill_level=6),
    WorkerProcessor("Senior", skill_level=9),
]
```

### 4. Create and Execute Tasks

```python
async with playground.play(workers=workers) as active_playground:
    ceylon_tasks = [
        Task(
            name=f"Task {task.id}",
            processor="worker",
            input_data={'data': task}
        )
        for task in tasks
    ]

    results = []
    for task in ceylon_tasks:
        result = await active_playground.add_and_execute_task(
            task=task,
            wait_for_completion=True
        )
        results.append(result)
```

## Advanced Features

### Task Dependencies

```python
task3 = Task(
    name="Aggregate Results",
    processor="aggregator",
    dependencies={task1.id, task2.id}
)
```

Dependencies ensure tasks execute in the correct order.

### Error Handling

```python
try:
    result = await active_playground.add_and_execute_task(task)
    if not result.success:
        print(f"Task failed: {result.error}")
except Exception as e:
    print(f"Error executing task: {e}")
```

### Parallel Processing

TaskProcessingPlayground automatically handles parallel execution of independent tasks.

## Best Practices

1. **Task Granularity**
    - Keep tasks focused and atomic
    - Avoid overly complex task dependencies
    - Consider breaking large tasks into smaller units

2. **Worker Design**
    - Make workers stateless when possible
    - Handle errors gracefully in _processor
    - Include relevant metadata in results

3. **Resource Management**
    - Use async context manager for cleanup
    - Monitor worker load and task distribution
    - Implement appropriate timeouts

4. **Error Handling**
    - Implement retries for transient failures
    - Log errors with sufficient context
    - Have fallback strategies for critical tasks

## Example: Task Pipeline

Here's an example of a more complex task pipeline:

```python
async def create_pipeline(playground):
    # Data preparation task
    prep_task = Task(
        name="Data Preparation",
        processor="prep_worker",
        input_data={'raw_data': data}
    )

    # Processing task depending on prep
    process_task = Task(
        name="Data Processing",
        processor="process_worker",
        dependencies={prep_task.id}
    )

    # Final aggregation
    aggregate_task = Task(
        name="Result Aggregation",
        processor="aggregator",
        dependencies={process_task.id}
    )

    # Execute pipeline
    tasks = [prep_task, process_task, aggregate_task]
    results = []

    for task in tasks:
        result = await playground.add_and_execute_task(task)
        results.append(result)

    return results
```

## Debugging Tips

1. Enable detailed logging:
```python
from loguru import logger
logger.enable("ceylon")
```

2. Monitor task states:
```python
task_status = playground.task_manager.get_task(task_id)
print(f"Task status: {task_status.status}")
```

3. Inspect worker connections:
```python
connected_workers = playground.llm_agents
print(f"Connected workers: {connected_workers}")
```

## Common Patterns

### Worker Pool
```python
workers = [
    WorkerProcessor(f"Worker-{i}", skill_level=5)
    for i in range(num_workers)
]
```

### Task Batching
```python
task_batch = [
    Task(name=f"Batch-{i}", processor="worker", input_data={'batch_id': i})
    for i in range(batch_size)
]
results = await asyncio.gather(*[
    playground.add_and_execute_task(task) for task in task_batch
])
```

### Result Aggregation
```python
async def aggregate_results(results):
    success_count = sum(1 for r in results if r.success)
    success_rate = success_count / len(results)
    return {
        'success_rate': success_rate,
        'total_tasks': len(results),
        'successful_tasks': success_count
    }
```

## Conclusion

Ceylon's TaskProcessingPlayground provides a robust framework for distributed task processing. Key benefits include:
- Built-in task dependency management
- Automatic parallel processing
- Clean worker abstraction
- Error handling and retries
- Resource management

Remember to:
- Design tasks and workers for your specific use case
- Implement proper error handling
- Monitor system performance
- Scale workers based on load

For more details, refer to the Ceylon documentation and example implementations.