from langchain_community.chat_models import ChatOllama

from ceylon import RunnerAgent, JobSteps, Step, JobRequest
from ceylon.llm import LLMAgent
from ceylon.tools.search_tool import SearchTool

llm_lib = ChatOllama(model="llama3.1:latest")
researcher = LLMAgent(
    name="researcher",
    role="AI and Machine Learning Research Specialist",
    objective="Search from web for relevant information with source references",
    context="Searches for relevant information on web to gather data for content creation",
    tools=[
        SearchTool()
    ],
    llm=llm_lib
)

writer = LLMAgent(
    name="writer",
    role="Content Writer",
    objective="Increase engagement and improve public understanding of the topic.",
    context="Simplifies technical concepts with metaphors, and creates narrative-driven "
            "content while ensuring scientific accuracy.",
    llm=llm_lib
)

job = JobRequest(
    title="write_article",
    steps=JobSteps(steps=[
        Step(
            worker="researcher",
            dependencies=[],
        ),
        Step(
            worker="writer",
            dependencies=["researcher"],
        )
    ]),
    job_data="What happened to trump?",
)

coordinator = RunnerAgent(workers=[writer, researcher])
res: JobRequest = coordinator.execute(job)
print("Response:", res, res.id, res.result)
