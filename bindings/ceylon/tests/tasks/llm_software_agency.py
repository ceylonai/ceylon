from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

from ceylon.llm import Task, SpecializedAgent, TaskManager

# Define the main task
task_management_app = Task(
    name="Create a Very Simple Ping Pong Game",
    description="""Develop a minimalist single-player Ping Pong game:
1. Create a game window with one paddle and a ball.
2. Move the paddle up and down using arrow keys.
3. Make the ball bounce off the walls and paddle.
4. Count and display how many times the player hits the ball.
5. End the game if the ball passes the paddle.
6. Allow restarting the game after it ends."""
)

tasks = [task_management_app]

# Initialize language models

llm = ChatOpenAI(model="gpt-4o-mini")
tool_llm = ChatOpenAI(model="gpt-4o-mini")
code_llm = ChatOllama(model="codestral:latest")
# code_llm = ChatOpenAI(model="codestral:latest")

# Create specialized agents
agents = [
    SpecializedAgent(
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
    SpecializedAgent(
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
    SpecializedAgent(
        name="testing_specialist",
        role="Quality Assurance Engineer",
        context="Expertise in software testing methodologies and test automation for Python applications.",
        skills=[
            "Unit Testing",
            "Integration Testing",
            "Test Automation",
            "Python Testing Frameworks"
        ],
        tools=[],
        llm=code_llm
    ),
    SpecializedAgent(
        name="game_developer",
        role="Python Game Developer",
        context="Experienced in creating interactive games and simulations using Python, with a focus on 2D game development.",
        skills=[
            "Game Design",
            "Game Mechanics",
            "2D Graphics",
            "Collision Detection",
            "Game Loop Implementation",
            "Player Input Handling",
            "Basic Game AI"
        ],
        tools=[
            "Pygame",
            "Arcade",
            "Pyglet"
        ],
        llm=code_llm
    )
]

# Initialize TaskManager
task_manager = TaskManager(tasks, agents, tool_llm=tool_llm, llm=llm)

# Execute tasks
completed_tasks = task_manager.do(inputs=b"")

# Print results
for task in completed_tasks:
    print(f"Task: {task.name}")
    print(f"Result: {task.final_answer}")
    print("-" * 50)
