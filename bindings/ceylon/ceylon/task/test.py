from loguru import logger

from ceylon.task import Task, SubTask
from task_coordinator import TaskCoordinator
from task_operator import TaskOperator


class DeveloperAgent(TaskOperator):
    async def get_result(self, task):
        # Simulate task execution
        logger.info(f"Developer agent executing task: {task.name}")
        return f"Completed {task.name}"


class QAAgent(TaskOperator):
    async def get_result(self, task):
        # Simulate task execution
        logger.info(f"QA agent executing task: {task.name}")
        return f"Tested {task.name}"


async def main():
    network_name = "localhost-task-coordinator"
    network_port = 8000
    # Create a task with subtasks
    web_app = Task.create_task(
        "Build Web App",
        "Create a simple web application",
        subtasks=[
            SubTask(name="setup", description="Set up the development environment", required_specialty="Developer",
                    executor="Alice"),
            SubTask(name="backend", description="Develop the backend API", depends_on={"setup"},
                    required_specialty="Developer",
                    executor="Alice"),
            SubTask(name="frontend", description="Develop the frontend UI", depends_on={"setup"},
                    required_specialty="Developer",
                    executor="Alice"),
            SubTask(name="testing", description="Perform unit and integration tests",
                    depends_on={"backend", "frontend"}, required_specialty="QA",
                    executor="Bob"),
        ]
    )

    # Create specialized agents
    developer = DeveloperAgent(name="Alice", role="Developer", workspace_id=network_name, admin_port=network_port)
    qa_engineer = QAAgent(name="Bob", role="QA", workspace_id=network_name, admin_port=network_port)

    # Create TaskCoordinator
    coordinator = TaskCoordinator(tasks=[web_app], agents=[developer, qa_engineer], name=network_name,
                                  port=network_port)

    # Run the task management process
    await coordinator.async_do(b"")

    # Print the final task status
    print("\nFinal task status:")
    print(web_app)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
