from langchain_community.chat_models import ChatOllama
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain_openai import ChatOpenAI

from ceylon.llm import LLMTaskOperator, LLMTaskCoordinator
from ceylon.task import Task

# Define the main task
task_management_app = Task(
    name="Create Task Management App",
    description="Develop a simple task management application with features for adding, listing, and completing tasks."
                " no need to use DB. only UI base output is enough"
)

tasks = [task_management_app]

# Initialize language models

llm = ChatOpenAI(model="gpt-4o-mini")
tool_llm = ChatOpenAI(model="gpt-4o-mini")
code_llm = ChatOpenAI(model="gpt-4o-mini")
# llm = ChatOllama(model="llama3.1:latest")
# tool_llm = OllamaFunctions(model="llama3.1:latest", format="json")
# code_llm = ChatOllama(model="codestral:latest")

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
    # SpecializedAgent(
    #     name="testing_specialist",
    #     role="Quality Assurance Engineer",
    #     context="Expertise in software testing methodologies and test automation for Python applications.",
    #     skills=[
    #         "Unit Testing",
    #         "Integration Testing",
    #         "Test Automation",
    #         "Python Testing Frameworks"
    #     ],
    #     tools=[],
    #     llm=code_llm
    # ),
    # SpecializedAgent(
    #     name="game_developer",
    #     role="Python Game Developer",
    #     context="Experienced in creating interactive games and simulations using Python, with a focus on 2D game development.",
    #     skills=[
    #         "Game Design",
    #         "Game Mechanics",
    #         "2D Graphics",
    #         "Collision Detection",
    #         "Game Loop Implementation",
    #         "Player Input Handling",
    #         "Basic Game AI"
    #     ],
    #     tools=[
    #         "Pygame",
    #         "Arcade",
    #         "Pyglet"
    #     ],
    #     llm=code_llm
    # )
]

# Initialize TaskManager
task_manager = LLMTaskCoordinator(tasks, agents, tool_llm=tool_llm, llm=llm)

# Execute tasks
completed_tasks = task_manager.do(inputs=b"")

# Print results
for task in completed_tasks:
    print(f"Task: {task.name}")
    print(f"Result: {task.final_answer}")
    print("-" * 50)
