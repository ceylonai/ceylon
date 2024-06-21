import pickle

from pydantic import BaseModel

from ceylon.ceylon import AgentCore, MessageHandler, Processor, AgentDefinition, AgentConfig, \
    AgentHandler, EventHandler
from ceylon.llm.llm_caller import process_agent_request
from ceylon.llm.runner import RunnerInput


class OtherAgent(BaseModel):
    definition: AgentDefinition
    is_connected: bool

    class Config:
        arbitrary_types_allowed = True


class LLMManager(AgentCore, MessageHandler, Processor, AgentHandler):
    connected_agents = []

    class OnAnyEvent(EventHandler):
        async def on_event(self, message):
            print(f"on_any_event {message}")

    def __init__(self, llm, name="manager"):
        self.llm = llm
        super().__init__(
            definition=AgentDefinition(id=None, name=name,
                                       is_leader=True,
                                       position="LEADER",
                                       responsibilities=[
                                           "With inputs you need to select next agent or agents to send the message",
                                       ],
                                       instructions=[
                                           "Select next agent or agents to send the message"
                                       ]),
            config=AgentConfig(memory_context_size=10),
            on_message=self,
            processor=self, meta={},
            agent_handler=self,
            event_handlers={
                # EventType.ON_ANY: [self.OnAnyEvent()]
            })
        self.connected_agents = []

    async def on_agent(self, agent: "AgentDefinition"):
        pass

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        agents = runner_input.agents

        agent_details = []
        for agent in agents:
            agent_details.append((agent.position, agent.responsibilities, agent.instructions))

        inputs = {
            "agents": agent_details
        }

        res = await process_agent_request(self.llm, inputs, agent_definition=self.definition(), tools=[])
        print(res)
