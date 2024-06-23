import asyncio
import pickle
import random
import time

from ceylon.ceylon import AgentCore, MessageHandler, Processor, AgentDefinition, Message, EventType, \
    AgentConfig, AgentHandler, EventHandler
from ceylon.runner import AgentRunner


class Agent(AgentCore, MessageHandler, Processor, AgentHandler):
    class OnSubscribeEvent(EventHandler):

        def __init__(self, sender: AgentCore):
            super().__init__()
            self.sender = sender

        async def on_event(self, message: Message):
            print("ANY EVENT HANDLER", message)

    def __init__(self, name, position, is_leader, responsibilities, instructions):
        super().__init__(definition=AgentDefinition(
            id=None,
            name=name,
            position=position,
            is_leader=is_leader,
            responsibilities=responsibilities,
            instructions=instructions
        ),
            config=AgentConfig(
                memory_context_size=10
            ),
            on_message=self,
            processor=self,
            meta=None,
            agent_handler=self,
            event_handlers={
                EventType.ON_SUBSCRIBE: [self.OnSubscribeEvent(self)]
            })

    async def on_agent(self, agent: AgentDefinition):
        print(f"{self.definition().name} on_agent {agent.name}")

    async def on_message(self, agent_id, message):
        print("SELF=", self.definition().name, "AGENT ID=", agent_id, "MESSAGE=", message)

    async def run(self, inputs):
        print("run", self.definition().name)
        inputs = pickle.loads(inputs)
        while True:
            await self.broadcast(pickle.dumps({
                "title": f"Hi Im  {self.definition().name} at {time.time()}",
            }))
            await asyncio.sleep(random.randint(1, 2))

    async def on_start(self, input: "bytes"):
        self.log(f"on_start {input}")


#
async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(
        Agent(name="ceylon-ai-1", position="LEADER", is_leader=True, responsibilities=[], instructions=[]))
    runner.register_agent(
        Agent(name="ceylon-ai-2", position="AST WRITER", is_leader=False, responsibilities=[], instructions=[]))
    runner.register_agent(
        Agent(name="ceylon-ai-3", position="RESEARCHER", is_leader=False, responsibilities=[], instructions=[]))
    runner.register_agent(
        Agent(name="ceylon-ai-4", position="PROOF READER", is_leader=False, responsibilities=[], instructions=[]))

    await runner.run({
        "title": "How to use AI for Machine Learning",
    }, network={})


if __name__ == '__main__':
    asyncio.run(main())
