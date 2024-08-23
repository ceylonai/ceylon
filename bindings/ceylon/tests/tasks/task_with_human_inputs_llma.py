from langchain_openai import ChatOpenAI

from ceylon.llm import LLMTaskOperator, LLMTaskCoordinator
from ceylon.task import Task, SubTask
from ceylon.task.task_human_intractive_operator import TaskOperatorWithHumanInteractive

llm = ChatOpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama',  # required, but unused
    model_name='llama3.1:latest'
)

admin = LLMTaskCoordinator(
    llm=llm
)
admin.add_agents([
    LLMTaskOperator(
        name="research",
        role="Researcher",
        context="Knowledge about research methodologies and tools",
        skills=["Market Research", "Data Analysis", "Literature Review"],  # Example skills
        llm=llm
    ),

    LLMTaskOperator(
        name="writing",
        role="Content Writer",
        context="Knowledge about content writing",
        skills=["Creative Writing", "Technical Writing", "Copywriting"],  # Example skills
        llm=llm
    ),
    TaskOperatorWithHumanInteractive(name="get_user_inputs", role="Get Human Inputs from User")
])

# Create subtasks
subtasks = [
    SubTask(name="research", description="Conduct research on SaaS concepts and examples", executor="research"),
    SubTask(name="outline", description="Create an outline for the article", depends_on={"research"},
            executor="writing"),
    SubTask(name="draft", description="Write the first draft of the article", depends_on={"outline"},
            executor="writing"),
    SubTask(name="review", description="Internal review and editing of the draft", depends_on={"draft"},
            executor="writing"),
    SubTask(name="feedback", description="Gather user feedback on the article", depends_on={"review"},
            executor="get_user_inputs"),
    SubTask(name="revise", description="Revise the article based on user feedback", depends_on={"feedback"},
            executor="writing"),
    SubTask(name="finalize", description="Finalize and proofread the article", depends_on={"revise"},
            executor="writing")
]

task = Task.create_task(name="Create SaaS Article",
                        description="Create a simple article about SaaS, get user feedback before final",
                        subtasks=subtasks)

admin.add_tasks([task])
results = admin.do()

for task in results:
    print(task.final_answer)
