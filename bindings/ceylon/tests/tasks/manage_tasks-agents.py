from langchain_community.chat_models import ChatOllama

from ceylon.llm import Task, SubTask, SpecializedAgent, TaskManager

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

    tasks = [
        web_app
    ]

    llm = ChatOllama(model="llama3.1:latest", temperature=0)
    # Create specialized agents
    agents = [
        SpecializedAgent(
            name="backend",
            specialty="Knowledge about backend tools",
            skills=["Python", "Java", "Node.js"],  # Example skills
            experience_level="Advanced",  # Example experience level
            tools=["Django", "Spring Boot", "Express.js"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="frontend",
            specialty="Knowledge about frontend tools",
            skills=["HTML", "CSS", "JavaScript", "React"],  # Example skills
            experience_level="Intermediate",  # Example experience level
            tools=["React", "Angular", "Vue.js"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="database",
            specialty="Knowledge about database management tools",
            skills=["SQL", "NoSQL", "Database Design"],  # Example skills
            experience_level="Advanced",  # Example experience level
            tools=["MySQL", "MongoDB", "PostgreSQL"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="deployment",
            specialty="Knowledge about deployment tools and CI tools",
            skills=["CI/CD", "Docker", "Kubernetes"],  # Example skills
            experience_level="Advanced",  # Example experience level
            tools=["Jenkins", "Docker", "Kubernetes"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="qa",
            specialty="Knowledge about testing tools",
            skills=["Automated Testing", "Manual Testing", "Test Case Design"],  # Example skills
            experience_level="Intermediate",  # Example experience level
            tools=["Selenium", "JUnit", "TestNG"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="delivery",
            specialty="Knowledge about delivery tools",
            skills=["Release Management", "Continuous Delivery"],  # Example skills
            experience_level="Intermediate",  # Example experience level
            tools=["Jira", "Confluence", "GitLab CI"],  # Example tools
            llm=llm
        )

    ]
    task_manager = TaskManager(tasks, agents, tool_llm=llm)
    task_manager.run_admin(inputs=b"", workers=agents)
