import asyncio
from pathlib import Path
from textwrap import dedent

from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from langchain_community.utilities.github import GitHubAPIWrapper
from langchain_openai import ChatOpenAI
from loguru import logger

from ceylon.ceylon import enable_log
from ceylon.llm import LLMTaskOperator, LLMTaskCoordinator
from ceylon.task import Task
from ceylon.utils.agent_monitor import AgentMonitor
from tasks.fw_tool import FixedWriteFileTool

enable_log("INFO")
# Define the main task
task_management_app = Task(
    name="Create Task Management App",
    description=dedent("""
    Need a software to print "Hello Ceylon" in console. 
    """)
)

import getpass
import os

for env_var in [
    "GITHUB_APP_ID",
    "GITHUB_APP_PRIVATE_KEY",
    "GITHUB_REPOSITORY",
]:
    if not os.getenv(env_var):
        os.environ[env_var] = getpass.getpass()

tasks = [task_management_app]

# Initialize language models

llm = ChatOpenAI(model="gpt-4o-mini")
tool_llm = ChatOpenAI(model="gpt-4o-mini")
code_llm = ChatOpenAI(model="gpt-4o-mini")

# github = GitHubAPIWrapper()
# toolkit = GitHubToolkit.from_github_api_wrapper(github)


working_directory = Path("software")
logger.info(working_directory.absolute())
root_dir = f"{working_directory.absolute()}"
toolkit = FileManagementToolkit(
    root_dir=root_dir,
    selected_tools=["read_file"],
)  # If you don't provide a root_dir, operations will default to the current working directory
logger.info(toolkit.get_tools())

# Create specialized agents
agents = [
    LLMTaskOperator(
        name="backend_developer",
        role="Python Backend Developer",
        context="Specializes in server-side logic, API development, database design, and system architecture. Focuses on efficiency, scalability, and security.",
        skills=[
            "Python Programming",
            "RESTful API Design",
            "Database Management (SQL and NoSQL)",
            "Server Architecture",
            "Authentication and Authorization",
            "Asynchronous Programming",
            "Microservices Architecture",
        ],
        tools=[],
        llm=code_llm
    ),
    LLMTaskOperator(
        name="frontend_developer",
        role="Python Frontend Developer",
        context="Expertise in creating intuitive and responsive user interfaces for Python applications. Focuses on user experience, accessibility, and cross-platform compatibility.",
        skills=[
            "UI/UX Design Principles",
            "Python GUI Frameworks (Tkinter, PyQt, wxPython)",
            "Event-driven Programming",
            "Responsive Design",
            "User Input Validation",
            "Data Visualization",
            "Accessibility Standards",
        ],
        tools=[],
        llm=code_llm
    ),
    LLMTaskOperator(
        name="qa_engineer",
        role="QA Engineer",
        context="Ensures software quality through comprehensive testing strategies. Focuses on identifying bugs, improving user experience, and maintaining code integrity.",
        skills=[
            "Test Planning and Strategy",
            "Unit Testing (pytest, unittest)",
            "Integration Testing",
            "End-to-End Testing (Selenium, Behave)",
            "Performance Testing (Locust)",
            "Security Testing",
            "API Testing (Postman, requests)",
            "Continuous Integration/Continuous Deployment (CI/CD)",
            "Bug Tracking and Reporting",
        ],
        tools=[],
        llm=code_llm,
        verbose=True
    ),
    LLMTaskOperator(
        name="source_code_writer",
        role="Source Code Manager",
        context="Responsible for creating, organizing, and managing source code files within the project structure. Ensures code consistency and proper file management.",
        skills=[
            "File System Operations",
            "Source Code Organization",
            "Version Control Integration",
            "Code Template Generation",
            "Project Structure Management",
            "File Naming Conventions",
            "Code Documentation",
        ],
        tools=[
            *toolkit.get_tools(),
            FixedWriteFileTool(
                root_dir=root_dir, )
        ],
        llm=code_llm,
        verbose=True
    ),
    AgentMonitor()
]
# Initialize TaskManager
task_manager = LLMTaskCoordinator(tasks, agents, tool_llm=tool_llm, llm=llm,
                                  team_goal=dedent("""
                                  Develop and deliver straightforward, secure, and efficient Python-based 
                                  software solutions that provide clear business value, 
                                  achieve 95% client satisfaction, and are completed on time and within budget
                                  """),
                                  context=dedent("""
                                  Employ agile methodologies to gather and analyze client requirements, design simple yet 
                                  robust solutions, implement clean and readable Python code, conduct thorough testing,
                                   and deploy using streamlined CI/CD practices. Prioritize code simplicity, 
                                  maintainability, and adherence to Python best practices 
                                  throughout the development lifecycle, following the principle that
                                   'simple is better than complex'.
                                  """),
                                  )
# task_manager.visualize_team_network(output_file=None)
# Execute tasks
completed_tasks = asyncio.run(task_manager.async_do(inputs=b""))

# Print results
for task in completed_tasks:
    print(f"Task: {task.name}")
    print(f"Result: {task.final_answer}")
    print("-" * 50)
