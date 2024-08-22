from typing import Any

from ceylon.task import SubTask, Task
from ceylon.task.task_coordinator import TaskCoordinator
from ceylon.task.task_human_intractive_operator import TaskOperatorWithHumanInteractive
from ceylon.task.task_operator import TaskOperator


class TaskOperatorOne(TaskOperator):
    async def get_result(self, task) -> Any:
        return "Hello, World! From Task Operator One"


class TaskOperatorTwo(TaskOperator):
    async def get_result(self, task) -> Any:
        return "Hello, World! From Task Operator Two"


admin = TaskCoordinator()
admin.add_agents([
    TaskOperatorOne(name="TaskOperatorOne", role="TaskOperator One"),
    TaskOperatorTwo(name="TaskOperatorTwo", role="TaskOperator Two"),
    TaskOperatorWithHumanInteractive(name="TaskOperatorWithHumanInteractive", role="TaskOperator With Human Interactive")
])

# Create subtasks
subtasks = [
    SubTask(name="setup", description="Set up the development environment", executor="TaskOperatorOne"),
    SubTask(name="database", description="Set up the database", executor="TaskOperatorTwo"),
    SubTask(name="backend", description="Develop the backend API", depends_on={"setup", "database"},
            executor="TaskOperatorOne"),
    SubTask(name="frontend", description="Develop the frontend UI", depends_on={"setup"},
            executor="TaskOperatorTwo"),
    SubTask(name="testing", description="Perform unit and integration tests",
            depends_on={"backend", "frontend"}, executor="TaskOperatorTwo"),
    SubTask(name="title", description="Deploy the application", depends_on={"testing"},
            executor="TaskOperatorWithHumanInteractive"),
    SubTask(name="deployment", description="Deploy the application", depends_on={"testing"},
            executor="TaskOperatorOne")
]
task = Task.create_task(name="Build Web App", description="Create a simple web application", subtasks=subtasks)
admin.add_tasks([task])
admin.do()
