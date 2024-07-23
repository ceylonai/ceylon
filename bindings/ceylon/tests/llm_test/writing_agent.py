from langchain_community.chat_models import ChatOllama
from langchain_experimental.llms.ollama_functions import OllamaFunctions

from ceylon.llm.types.job import Job, Step
from ceylon.llm.types.agent import AgentDefinition
from ceylon.llm.unit import LLMAgent, ChiefAgent
from ceylon.tools.search_tool import SearchTool

llm_lib = ChatOllama(model="llama3:instruct")
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
        objective="Provide comprehensive and current coverage of AI applications in machine learning",
        context="Conducts thorough research on AI applications in machine learning, gathering detailed information "
                "from reputable academic and industry sources. Uses tools like academic databases and industry report aggregators."
    ),
    tools=[SearchTool()],
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
    explanation="Write an article about machine learning",
    work_order=[
        Step(worker="researcher", dependencies=[]),
        Step(worker="writer", dependencies=["researcher"]),
        Step(worker="proof_writer", dependencies=["writer"]),
    ],
    input={
        "title": "How to use AI for Machine Learning",
        "tone": "informal",
        "style": "creative"
    }
)

llm_lib = ChatOllama(model="phi3:latest")
# llm_lib = OllamaFunctions(model="phi3:14b", output_format="json")
chief = ChiefAgent(workers=[writer, researcher, proof_writer], tool_llm=llm_lib)

res = chief.execute(job)
print("Response:", res)
