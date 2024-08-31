import asyncio
from typing import Any

from ceylon.ceylon import enable_log
from ceylon.task import TaskCoordinator, TaskOperator

task_manager = TaskCoordinator(tasks=[], agents=[])

enable_log("INFO")
asyncio.run(task_manager.async_do())
