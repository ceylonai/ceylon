from ceylon.llm import LLMTaskCoordinator, LLMTaskOperator

from langchain_openai import ChatOpenAI

code_llm = ChatOpenAI(model="gpt-4o")

python_developer = LLMTaskOperator(
    name="python_developer",
    role="Junior Python Developer",
    context="Develop Python application with standalone application development knowlage",
    skills=[
        "Python programming"
    ],
    llm=code_llm
)

python_gui_developer = LLMTaskOperator(
    name="python_gui_developer",
    role="Junior Python GUI Developer",
    context="Develop Python application with GUI development knowlage",
    skills=[
        "Python programming",
        "GUI development"
    ],
    llm=code_llm
)

from ceylon.task import Task

task = Task(
    name="Create Task Management App",
    description="Develop a advance task manager app. Required features. mark completed, filter with date, download by selected date. Need a UI for users"
)

tool_llm = ChatOpenAI(model="gpt-4o-mini")
llm = ChatOpenAI(model="gpt-4o-mini")

from textwrap import dedent

agents = [python_developer, python_gui_developer]

software_agency = LLMTaskCoordinator(
    tasks=[task],
    agents=agents,
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
    llm=llm,
    tool_llm=tool_llm
)

completed_tasks = software_agency.do()
# Print results
for task in completed_tasks:
    print(f"Task: {task.name}")
    print(f"Result: {task.final_answer}")
    print("-" * 50)
