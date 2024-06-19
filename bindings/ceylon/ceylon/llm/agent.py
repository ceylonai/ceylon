from ceylon.ceylon import AgentCore, MessageHandler, AgentHandler, AgentDefinition, AgentConfig, MessageType


class LLMAgent(AgentCore, MessageHandler, AgentHandler):
    def __init__(self, name, position, responsibilities=[], instructions=[]):
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
            on_message=self, processor=None, meta=None, event_handlers={})

    async def on_agent(self, agent: AgentDefinition):
        pass

    async def on_message(self, agent_id, message):
        print(f"on_message {agent_id} {message}")
