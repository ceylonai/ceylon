from langchain_community.chat_models import ChatOllama

from ceylon.llm.types.agent import AgentDefinition
from ceylon.llm.types.job import Job, Step, JobSteps
from ceylon.llm.unit import LLMAgent, ChiefAgent
from ceylon.tools.search_tool import SearchTool

llm_lib = ChatOllama(model="llama3.1:latest")
# llm_lib = ChatOpenAI(model="gpt-4o")
# llm_lib = OllamaFunctions(model="phi3:instruct", keep_alive=-1,
#                           format="json")
writer = LLMAgent(
    AgentDefinition(
        name="writer",
        role="Content Writer",
        objective="Increase engagement and improve public understanding of the topic.",
        context="Simplifies technical concepts with metaphors, and creates narrative-driven content while ensuring scientific accuracy."
    ),
    tool_llm=llm_lib
)
researcher = LLMAgent(
    AgentDefinition(
        name="researcher",
        role="AI and Machine Learning Research Specialist",
        objective="Search from web for relevant information with source references",
        context="Searches for relevant information on web to gather data for content creation"
    ),
    tools=[
        SearchTool(),
        # WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100))
    ],
    tool_llm=llm_lib
)

proof_writer = LLMAgent(
    AgentDefinition(
        name="proof_writer",
        role="Content Editor and Finalizer",
        objective="Refine AI-generated articles to be publication-ready",
        context="Edits for clarity, coherence, and flow; corrects grammar and spelling; enhances structure and "
                "formatting; ensures consistent tone and style; implements SEO best practices. Uses tools like grammar checkers and SEO analysis tools."
    ), tool_llm=llm_lib)

job = Job(
    title="write_article",
    explanation="Write an article about machine learning, Tone: Informal, Style: Creative, Length: Large",
    steps=JobSteps(steps=[
        Step(
            worker="writer",
            dependencies=["researcher"],
            explanation="Write an article about machine learning, Tone: Informal, Style: Creative, Length: Large"
        ),
        Step(
            worker="researcher",
            dependencies=[],
            explanation="Provide comprehensive and current coverage of AI applications in machine learning"
        ),
        Step(
            worker="proof_writer",
            dependencies=["writer"],
            explanation="Refine AI-generated articles to be publication-ready"
        )
    ]),
)

llm_lib = ChatOllama(model="phi3:latest")
chief = ChiefAgent(workers=[writer, researcher, proof_writer], tool_llm=llm_lib)
res = chief.execute(job)
print("Response:", res)
