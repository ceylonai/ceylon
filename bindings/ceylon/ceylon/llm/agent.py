import pickle

from langchain_core.tools import StructuredTool

from ceylon.ceylon import AgentCore, MessageHandler, AgentHandler, AgentDefinition, AgentConfig, Processor
from ceylon.llm.runner import RunnerInput


class LLMAgent(AgentCore, MessageHandler, AgentHandler, Processor):
    tools: list[StructuredTool]

    def __init__(self, name, position, llm, responsibilities=None, instructions=None, tools=None):
        if responsibilities is None:
            responsibilities = []
        if instructions is None:
            instructions = []
        if tools is None:
            tools = []
        self.tools = tools
        self.llm = llm
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


