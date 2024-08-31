import asyncio

from ceylon.ceylon import enable_log
from ceylon.task import TaskCoordinator

task_manager = TaskCoordinator(tasks=[], agents=[])

enable_log("INFO")
asyncio.run(task_manager.async_do())
