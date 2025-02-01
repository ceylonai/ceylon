import asyncio
from typing import List, Optional
from datetime import datetime

from loguru import logger


class Task:
    def __init__(self, name: str, description: str = "", duration: float = 0):
        self.name = name
        self.description = description
        self.duration = duration  # Duration in seconds
        self.subtasks: List[Task] = []
        self.completed = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def add_subtask(self, subtask: 'Task'):
        """Add a subtask to the current task"""
        self.subtasks.append(subtask)

    async def execute(self):
        """Execute the task and its subtasks"""
        if self.completed:
            return

        self.start_time = datetime.now()

        # Execute all subtasks first
        if self.subtasks:
            await asyncio.gather(*(subtask.execute() for subtask in self.subtasks))

        # Simulate task execution with sleep
        if self.duration > 0:
            await asyncio.sleep(self.duration)

        self.completed = True
        self.end_time = datetime.now()

    async def get_status(self):
        """Get the current status of the task and its subtasks"""
        status = f"Task: {self.name} - {'Completed' if self.completed else 'Pending'}"
        if self.start_time:
            status += f"\n  Started: {self.start_time}"
        if self.end_time:
            status += f"\n  Ended: {self.end_time}"

        if self.subtasks:
            status += "\n  Subtasks:"
            for subtask in self.subtasks:
                subtask_status = await subtask.get_status()
                status += "\n    " + "\n    ".join(subtask_status.split("\n"))
        return status


class AsyncTaskManager:
    def __init__(self):
        self.tasks: List[Task] = []

    async def create_task(self, name: str, description: str = "", duration: float = 0) -> Task:
        """Create a new task and add it to the task list"""
        task = Task(name, description, duration)
        self.tasks.append(task)
        return task

    async def execute_all(self):
        """Execute all tasks in parallel"""
        await asyncio.gather(*(task.execute() for task in self.tasks))

    async def get_all_tasks_status(self):
        """Get the status of all tasks"""
        statuses = [await task.get_status() for task in self.tasks]
        return "\n\n".join(statuses)


# Example usage:
async def main():
    # Create a task manager
    manager = AsyncTaskManager()

    # Create a main task
    main_task = await manager.create_task("Build Website", "Create a company website", 1)

    # Create and add subtasks
    frontend = Task("Frontend Development", duration=2)
    backend = Task("Backend Development", duration=3)
    await main_task.add_subtask(frontend)
    await main_task.add_subtask(backend)

    # Add sub-subtasks
    ui_design = Task("Design UI", duration=1)
    implement_html = Task("Implement HTML/CSS", duration=1.5)
    await frontend.add_subtask(ui_design)
    await frontend.add_subtask(implement_html)

    # Print initial status
    logger.info("Initial Status:")
    logger.info(await manager.get_all_tasks_status())
    logger.info("\n")

    # Execute all tasks
    logger.info("Executing tasks...")
    await manager.execute_all()

    logger.info("\nFinal Status:")
    logger.info(await manager.get_all_tasks_status())


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())