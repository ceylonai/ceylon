import asyncio
from dataclasses import dataclass
from typing import List
from ceylon.processor.agent import ProcessWorker
from ceylon.task.playground import TaskProcessingPlayground
from ceylon.processor.data import ProcessRequest, ProcessResponse, ProcessState
from ceylon.task.manager import Task, TaskResult


@dataclass
class WorkTask:
    id: int
    description: str
    difficulty: int


class WorkerProcessor(ProcessWorker):
    def __init__(self, name: str, skill_level: int):
        super().__init__(name=name, role="worker")
        self.skill_level = skill_level

    async def _processor(self, request: ProcessRequest, time: int) -> tuple[bool, dict]:
        task = request.data
        await asyncio.sleep(task.difficulty/10)
        success = self.skill_level >= task.difficulty
        return success, {
            "task_id": task.id,
            "worker": self.name,
            "difficulty": task.difficulty
        }


async def main():
    # Create tasks
    tasks = [
        WorkTask(id=1, description="Simple calculation", difficulty=2),
        WorkTask(id=2, description="Data analysis", difficulty=5),
        WorkTask(id=3, description="ML model training", difficulty=8),
    ]

    # Create playground and workers
    playground = TaskProcessingPlayground(name="task_playground", port=8000)
    workers = [
        WorkerProcessor("Junior", skill_level=3),
        WorkerProcessor("Intermediate", skill_level=6),
        WorkerProcessor("Senior", skill_level=9),
    ]

    async with playground.play(workers=workers) as active_playground:
        # Create tasks for each work item
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
            result: TaskResult = await active_playground.add_and_execute_task(
                task=task,
                wait_for_completion=True
            )
            results.append(result)

        # Calculate and display results
        success_count = sum(1 for r in results if r.success)
        success_rate = success_count / len(results)
        print(f"\nResults:")
        for task, result in zip(tasks, results):
            worker_name = result.output[1].get("worker")
            print(f"Task {task.id} processed by {worker_name} - "
                  f"{'Success' if result.success else 'Failure'}")
        print(f"\nSuccess rate: {success_rate:.2%}")


if __name__ == "__main__":
    asyncio.run(main())
