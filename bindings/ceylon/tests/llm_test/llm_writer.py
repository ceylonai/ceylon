from langchain_community.chat_models import ChatOllama

from ceylon import JobSteps, Step, JobRequest
from ceylon.llm import LLMAgent
from ceylon.llm.agent import LLMExecutorAgent
from ceylon.tools.search_tool import SearchTool

llm_lib = ChatOllama(model="llama3.1:latest")
# llm_lib = ChatOpenAI(model="gpt-4o")
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

seo_optimizer = LLMAgent(
    name="seo_optimizer",
    role="SEO Optimizer",
    objective="Optimize content for search engines",
    context="Optimize content for search engines, with SEO optimization. You will optimize "
            "the content for search engines.",
    tools=[],
    llm=llm_lib
)
proof_writer = LLMAgent(
    name="proof_writer",
    role="Proof Writer",
    objective="Increase engagement and improve public understanding of the topic.",
    context="Simplifies technical concepts with paraphrasing, and creates narrative-driven content "
            "while ensuring scientific accuracy."
            " Proof writer will proofread and proofread the content. Do not use any explanation just use final article",
    llm=llm_lib
)
job = JobRequest(
    title="write_article",
    steps=JobSteps(steps=[
        Step(
            worker="seo_optimizer",
            dependencies=["writer"],
        ),
        Step(
            worker="researcher",
            dependencies=[],
        ),
        Step(
            worker="writer",
            dependencies=["researcher"],
        ),
        Step(
            worker="proof_writer",
            dependencies=["seo_optimizer"],
        )
    ]),
    job_data="Write Article Title: What is the importance of Machine Learning, Tone: Informal, "
             "Style: Creative, Length: Large. Focus on keyword AI,Future",
)

coordinator = LLMExecutorAgent(workers=[researcher, writer, seo_optimizer, proof_writer])


# res: JobRequest = coordinator.execute(job)
# print("Response:", res)
async def main():
    res: JobRequest = await coordinator.aexecute(job)
    print("Response:", res)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
