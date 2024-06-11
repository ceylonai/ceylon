from ceylon.ceylon import AgentCore, MessageHandler, Processor


class LLMManager(AgentCore, MessageHandler, Processor):
    def __init__(self, name, is_leader):
        super().__init__(name=name, is_leader=is_leader, on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        print(inputs)


class LLMAgent(AgentCore, MessageHandler, Processor):
    def __init__(self, name, is_leader):
        super().__init__(name=name, is_leader=is_leader, on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        print(inputs)
