import asyncio
from textwrap import dedent

from langchain_openai import ChatOpenAI

from ceylon.llm import LLMTaskOperator, LLMTaskCoordinator
from ceylon.task import Task
from ceylon.utils.agent_monitor import AgentMonitor

# Define the main task
task_management_app = Task(
    name="Create Task Management App",
    description=dedent("""
    Develop a advanced task management application with features for adding,  listing, and completing tasks. 
    and with priority from list.also need to download list of tasks by date.and need to check finished tasks 
     no need to use DB. only UI base output is enough. final output must be python script.
    """)
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
            "Python GUI Frameworks like Tkinter",
        ],
        tools=[],
        llm=code_llm
    ),
    AgentMonitor()
]
# enable_log("INFO")
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
