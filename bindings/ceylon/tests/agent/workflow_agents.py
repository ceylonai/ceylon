import asyncio
import pickle
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from ceylon import Admin, Worker, on, AgentDetail


# Define task message types
@dataclass
class TaskRequest:
    task_id: str
    data: bytes

@dataclass
class TaskResult:
    task_id: str
    result: bytes
    success: bool

class TaskCoordinator(Admin):
    def __init__(self, name="task_coordinator", port=8888):
        super().__init__(name=name, port=port)
        self.pending_tasks = {}
        self.completed_tasks = {}

    @on(TaskResult)
    async def handle_task_result(self, data: TaskResult, time: int, agent: AgentDetail):
        if data.task_id in self.pending_tasks:
            logger.info(f"Task {data.task_id} completed by {agent.name} - Success: {data.success}")
            self.completed_tasks[data.task_id] = data
            del self.pending_tasks[data.task_id]

    async def submit_task(self, task_data: bytes) -> str:
        # Generate task ID and submit task
        task_id = f"task_{len(self.pending_tasks) + 1}"
        task = TaskRequest(task_id=task_id, data=task_data)
        self.pending_tasks[task_id] = task
        return task_id

    async def assign_task(self, task_id: str, worker_id: str):
        if task_id in self.pending_tasks:
            task = self.pending_tasks[task_id]
            await self.send_message(worker_id, pickle.dumps(task))
            logger.info(f"Assigned task {task_id} to worker {worker_id}")
            return True
        return False

class TaskWorker(Worker):
    def __init__(self, name: str, processing_time: float = 2.0):
        super().__init__(name=name, role="worker")
        self.processing_time = processing_time
        self.current_task: Optional[TaskRequest] = None

    @on(TaskRequest)
    async def handle_task(self, data: TaskRequest, time: int, agent: AgentDetail):
        if self.current_task:
            logger.warning(f"Worker {self.name} is busy")
            return

        self.current_task = data
        logger.info(f"Worker {self.name} starting task {data.task_id}")

        # Simulate task processing
        await asyncio.sleep(self.processing_time)

        # Create result
        result = TaskResult(
            task_id=data.task_id,
            result=f"Processed by {self.name}".encode(),
            success=True
        )

        await self.broadcast_message(pickle.dumps(result))
        self.current_task = None

async def main():
    # Create coordinator
    coordinator = TaskCoordinator(port=5555)

    # Create workers
    workers = [
        TaskWorker("worker1", processing_time=2.0),
        TaskWorker("worker2", processing_time=1.5),
        TaskWorker("worker3", processing_time=3.0)
    ]

    # Start the system
    await coordinator.start_agent(b"", workers)

    # Submit some tasks
    task_ids = []
    for i in range(5):
        task_data = f"Task data {i}".encode()
        task_id = await coordinator.submit_task(task_data)
        task_ids.append(task_id)
        logger.info(f"Submitted task {task_id}")

    # Wait a moment for workers to connect
    await asyncio.sleep(1)

    # Get connected workers
    connected_workers = await coordinator.get_connected_agents()

    # Assign tasks to workers round-robin
    for i, task_id in enumerate(task_ids):
        worker = connected_workers[i % len(connected_workers)]
        await coordinator.assign_task(task_id, worker.id)

    # Wait for all tasks to complete
    while coordinator.pending_tasks:
        await asyncio.sleep(0.5)

    # Print results
    for task_id, result in coordinator.completed_tasks.items():
        logger.info(f"Task {task_id} result: {result}")

    # Cleanup
    await coordinator.stop()

if __name__ == "__main__":
    asyncio.run(main())