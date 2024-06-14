import asyncio
import pickle
import random
import time

from ceylon.ceylon import AgentCore, MessageHandler, Processor, MessageType, AgentDefinition, Message, EventType, \
    AgentConfig
from ceylon.runner import AgentRunner


class Agent(AgentCore, MessageHandler, Processor):
    class OnSubscribeEvent(MessageHandler):

        def __init__(self, sender: AgentCore):
            super().__init__()
            self.sender = sender

        async def on_message(self, agent_id: str, message: Message):
            print("ANY EVENT HANDLER", agent_id, message)

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
            on_message=self, processor=self, meta=None, event_handlers={
                EventType.ON_SUBSCRIBE: [self.OnSubscribeEvent(self)]
            })

    async def on_message(self, agent_id, message):
        id = self.definition().id
        name = self.definition().name
        if message.type == MessageType.MESSAGE:
            print(
                "SENDER NAME=", message.sender,
                "RECEIVER ID=", message.receiver,
                id == message.receiver,
                "MY ID=", name,
                "DATA=", pickle.loads(message.data),
                "MESSAGE=", message.message,
                "MESSAGE TYPE=", message.type.name)
        else:
            print(
                "SENDER NAME=", message.sender,
                "RECEIVER ID=", message.receiver,
                id == message.receiver,
                "MY ID=", name,
                "MESSAGE=", message.message,
                "MESSAGE TYPE=", message.type.name)

    async def run(self, inputs):
        print("run", self.definition().name)
        inputs = pickle.loads(inputs)
        while True:
            await asyncio.sleep(random.randint(1, 5))
            await self.broadcast(pickle.dumps({
                "title": f"Hi Im  {self.definition().name} at {time.time()}",
            }), to=None)


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
    })


if __name__ == '__main__':
    asyncio.run(main())
