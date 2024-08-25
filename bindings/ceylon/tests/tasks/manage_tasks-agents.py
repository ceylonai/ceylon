from langchain_community.chat_models import ChatOllama

from ceylon.llm import LLMTaskCoordinator, LLMTaskOperator
from ceylon.task import Task, SubTask
from ceylon.task.task_operation import TaskDeliverable

# Example usage
if __name__ == "__main__":
    # Create a task with initial subtasks
    web_app = Task.create_task("Build Web App", "Create a simple web application",
                               subtasks=[
                                   SubTask(name="setup", description="Set up the development environment",
                                           required_specialty="Knowledge about deployment and development tools"),
                                   SubTask(name="database", description="Set up the database",
                                           required_specialty="Knowledge about database management tools"),
                                   SubTask(name="testing", description="Perform unit and integration tests",
                                           depends_on={"backend", "frontend"},
                                           required_specialty="Knowledge about testing tools"),
                                   SubTask(name="frontend", description="Develop the frontend UI",
                                           depends_on={"setup", "backend"},
                                           required_specialty="Knowledge about frontend tools"),
                                   SubTask(name="backend", description="Develop the backend API",
                                           depends_on={"setup", "database"},
                                           required_specialty="Knowledge about backend tools"),
                                   SubTask(name="deployment", description="Deploy the application",
                                           depends_on={"testing", "qa"},
                                           required_specialty="Knowledge about deployment tools and CI tools"),
                                   SubTask(name="delivery", description="Deploy the application",
                                           depends_on={"deployment"},
                                           required_specialty="Knowledge about delivery tools"),
                                   SubTask(name="qa", description="Perform quality assurance",
                                           depends_on={"testing"},
                                           required_specialty="Knowledge about testing tools")

                               ])
    web_app.task_deliverable = TaskDeliverable.default(web_app.description)
    tasks = [
        web_app
    ]

    llm = ChatOllama(model="llama3.1:latest", temperature=0)
    # Create specialized agents
    agents = [
        LLMTaskOperator(
            name="backend",
            role="Backend Developer",
            context="Knowledge about backend tools",
            skills=["Python", "Java", "Node.js"],  # Example skills
            llm=llm
        ),

        LLMTaskOperator(
            name="frontend",
            role="Frontend Developer",
            context="Knowledge about frontend tools",
            skills=["HTML", "CSS", "JavaScript", "React"],  # Example skills
            llm=llm
        ),

        LLMTaskOperator(
            name="database",
            role="Database Administrator",
            context="Knowledge about database management tools",
            skills=["SQL", "NoSQL", "Database Design"],  # Example skills
            llm=llm
        ),
        #
        LLMTaskOperator(
            name="deployment",
            role="Deployment Manager",
            context="Knowledge about deployment tools and CI tools",
            skills=["CI/CD", "Docker", "Kubernetes"],  # Example skills
            llm=llm
        ),
        #
        # LLMTaskOperator(
        #     name="qa",
        #     role="Quality Assurance Engineer",
        #     context="Knowledge about testing tools",
        #     skills=["Automated Testing", "Manual Testing", "Test Case Design"],  # Example skills
        #     llm=llm
        # ),
        #
        # LLMTaskOperator(
        #     name="delivery",
        #     role="Delivery Manager",
        #     context="Knowledge about delivery tools",
        #     skills=["Release Management", "Continuous Delivery"],  # Example skills
        #     llm=llm
        # )

    ]
    task_manager = LLMTaskCoordinator(tasks, agents, llm=llm)
    task_manager.do()
