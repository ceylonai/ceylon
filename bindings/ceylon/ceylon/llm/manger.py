import pickle

from ceylon.ceylon import AgentCore, MessageHandler, Processor, AgentDefinition, MessageType, EventType, AgentConfig, \
    AgentHandler, EventHandler
from ceylon.runner import RunnerInput


class LLMManager(AgentCore, MessageHandler, Processor, AgentHandler):
    class OnAnyEvent(EventHandler):
        async def on_event(self, message):
            print(f"on_any_event {message}")

    def __init__(self, name="manager"):
        super().__init__(
            definition=AgentDefinition(id=None, name=name,
                                       is_leader=True,
                                       position="LEADER",
                                       responsibilities=[],
                                       instructions=[]),
            config=AgentConfig(memory_context_size=10),
            on_message=self,
            processor=self, meta={},
            agent_handler=self,
            event_handlers={
                EventType.ON_ANY: [self.OnAnyEvent()]
            })

    async def on_agent(self, agent: "AgentDefinition"):
        pass

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        agents = runner_input.agents_meta
        print(agents)
