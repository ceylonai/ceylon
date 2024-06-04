import asyncio
import json
import random

from ceylonai import ceylonai


class AgentCy:
    name: str
    __agent__: ceylonai.AbstractAgent

    def __init__(self, name: str):
        self.name = name

        async def __proxy_msg_handler(sender: str, message: str):
            await self.receive_message(sender, message)

        self.__agent__ = ceylonai.AbstractAgent(name, __proxy_msg_handler)

    async def receive_message(self, sender: str, message: str):
        print(self.name, sender, message)

    async def publish(self, message: dict):
        await self.__agent__.send(json.dumps(message))

    async def start(self):
        await self.__agent__.start()


async def start():
    agent_1 = AgentCy("agent_1")
    agent_2 = AgentCy("agent_2")

    async def test_func(agent, message):
        while True:
            await agent.publish(message)
            await asyncio.sleep(random.randint(10, 100) / 100)

    async def start_agents(agent: AgentCy):
        await agent.start()

    s_t1 = asyncio.create_task(start_agents(agent_1))
    s_t2 = asyncio.create_task(start_agents(agent_2))

    t1 = asyncio.create_task(test_func(agent_1, {"message": "hello11"}))
    t2 = asyncio.create_task(test_func(agent_2, {"message": "hello22"}))

    await asyncio.gather(s_t1, s_t2, t1, t2)


if __name__ == '__main__':
    asyncio.run(start())
