import pickle

from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import format_tool_to_openai_function

from ceylon.ceylon import AgentCore, MessageHandler, AgentHandler, AgentDefinition, AgentConfig, Processor
from ceylon.llm.runner import RunnerInput


class LLMAgent(AgentCore, MessageHandler, AgentHandler, Processor):
    tools: list[StructuredTool]

    def __init__(self, name, position, responsibilities=None, instructions=None, tools=None):
        if responsibilities is None:
            responsibilities = []
        if instructions is None:
            instructions = []
        if tools is None:
            tools = []
        self.tools = tools

        super().__init__(definition=AgentDefinition(
            id=None,
            name=name,
            responsibilities=responsibilities,
            position=position,
            is_leader=False,
            instructions=instructions
        ),
            config=AgentConfig(memory_context_size=10),
            agent_handler=self,
            on_message=self, processor=self, meta=None, event_handlers={})

    async def on_agent(self, agent: AgentDefinition):
        pass

    async def on_message(self, agent_id, message):
        print(f"on_message {agent_id} {message}")

    async def run(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        input = runner_input.request
        ollama_llama3 = ChatOllama(model="llama3")
        ollama_llama3.bind(
            functions=[format_tool_to_openai_function(t) for t in self.tools],
        )
        template = """
        **Role:** {role}
        **Responsibilities:** {responsibilities}
        **Instructions:** {instructions}
        **Task:**
        {task_info}
        """

        # Create a PromptTemplate instance
        prompt = PromptTemplate(template=template,
                                input_variables=["role", "responsibilities", "instructions", "task_info"])

        # Define a ToolChain to use the Retriever and Processor tools
        agent = (
                prompt
                | ollama_llama3
                | OpenAIFunctionsAgentOutputParser()
        )

        # Initialize the agent executor
        agent_executor = AgentExecutor(agent=agent,
                                       tools=self.tools,
                                       verbose=True)

        response = agent_executor.invoke({
            "role": self.definition().position,
            "responsibilities": " ".join(self.definition().responsibilities),
            "instructions": " ".join(self.definition().instructions),
            "task_info": "\n".join([f"**{key.capitalize()}:** {value}" for key, value in runner_input.request.items()])
        })
        response = response.get("output")
        print(f"Response: {response}")
        return pickle.dumps(response)
