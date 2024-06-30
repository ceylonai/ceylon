from ceylon.ceylon import AgentCore, MessageHandler, Processor


class LLMManager(AgentCore, MessageHandler, Processor):
    def __init__(self, name="manager"):
        super().__init__(name=name, is_leader=True, on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        print(inputs)


class LLMAgent(AgentCore, MessageHandler, Processor):
    def __init__(self, name):
        super().__init__(name=name, is_leader=False, on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        print(inputs)
