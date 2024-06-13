import pickle

from ceylon.ceylon import AgentCore, MessageHandler, Processor
from ceylon.runner import RunnerInput


class LLMManager(AgentCore, MessageHandler, Processor):
    def __init__(self, name="manager"):
        super().__init__(name=name, is_leader=True, on_message=self, processor=self, meta=None)

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        agents = runner_input.agents_meta
        print(agents)


class LLMAgent(AgentCore, MessageHandler):
    def __init__(self, name, responsibility="", instructions=""):
        meta = {"responsibility": responsibility, "instructions": instructions, "name": name}
        super().__init__(name=name, is_leader=False, on_message=self, processor=None, meta=meta)

    async def on_message(self, agent_id, message):
        pass
