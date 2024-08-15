from langchain_openai import ChatOpenAI

from ceylon.ceylon import enable_log
from ceylon.llm import LLMTaskOperator, LLMTaskCoordinator
from ceylon.task import Task
from ceylon.utils.agent_monitor import AgentMonitor

# Define the main task
task_management_app = Task(
    name="Create Task Management App",
    description="Develop a advanced task management application with features for adding, "
                "listing, and completing tasks. and with priority from list.also need to download list of tasks by date.and need to check finished tasks"
                " no need to use DB. only UI base output is enough"
)

tasks = [task_management_app]

# Initialize language models

llm = ChatOpenAI(model="gpt-4o-mini")
tool_llm = ChatOpenAI(model="gpt-4o-mini")
code_llm = ChatOpenAI(model="gpt-4o-mini")

# Create specialized agents
agents = [
    LLMTaskOperator(
        name="backend_developer",
        role="Python Backend Developer",
        context="Experienced in developing backend systems, API design, and database integration.",
        skills=[
            "Python Programming",
            "API Development",
            "Database Design",
            "Backend Architecture",
            "Data Modeling"
        ],
        tools=[],
        llm=code_llm
    ),
    LLMTaskOperator(
        name="frontend_developer",
        role="Python Frontend Developer",
        context="Proficient in creating user interfaces and handling user interactions in Python applications.",
        skills=[
            "UI Design",
            "User Experience",
            "Frontend Development",
            "Python GUI Frameworks"
        ],
        tools=[],
        llm=code_llm
    ),
    AgentMonitor()
]
# enable_log("DEBUG")
# Initialize TaskManager
task_manager = LLMTaskCoordinator(tasks, agents, tool_llm=tool_llm, llm=llm)

# Execute tasks
completed_tasks = task_manager.do(inputs=b"")

# Print results
for task in completed_tasks:
    print(f"Task: {task.name}")
    print(f"Result: {task.final_answer}")
    print("-" * 50)
