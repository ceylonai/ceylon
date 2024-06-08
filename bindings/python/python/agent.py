import asyncio
import json
import random
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor

from ceylonai import ceylonai


class AgentCy:
    name: str
    __agent__: ceylonai.AbstractAgent

    def __init__(self, name: str):
        self.name = name

        def __proxy_msg_handler(sender: str, message: str):
            print("Proxy message handler", sender, message)
            self.receive_message(sender, message)

        self.__agent__ = ceylonai.AbstractAgent(name, __proxy_msg_handler)

    def receive_message(self, sender: str, message: str):
        print(self.name, sender, message)

    def publish(self, message: dict):
        self.__agent__.send(json.dumps(message))

    def start(self):
        self.__agent__.start()


def start():
    agent_1 = AgentCy("agent_1")
    agent_2 = AgentCy("agent_2")

    def test_func(agent, message):
        while True:
            agent.publish(message)
            time.sleep(random.randint(10, 100) / 100)

    def start_agents(agent):
        agent.start()

    with ThreadPoolExecutor(max_workers=4) as executor:
        s_t1 = executor.submit(start_agents, agent_1)
        s_t2 = executor.submit(start_agents, agent_2)

        t1 = threading.Thread(target=test_func, args=(agent_1, {"message": "hello11"}))
        t2 = threading.Thread(target=test_func, args=(agent_2, {"message": "hello22"}))

        t1.start()
        t2.start()

        # Wait for the start_agents tasks to complete
        s_t1.result()
        s_t2.result()

        # Optionally, you can join the threads if you want to wait for them to finish
        t1.join()
        t2.join()

    # async def test_func(agent, message):
    #     while True:
    #         await agent.publish(message)
    #         await asyncio.sleep(random.randint(10, 100) / 100)
    #
    # async def start_agents(agent: AgentCy):
    #     await agent.start()
    #
    # s_t1 = asyncio.create_task(start_agents(agent_1))
    # s_t2 = asyncio.create_task(start_agents(agent_2))
    #
    # t1 = asyncio.create_task(test_func(agent_1, {"message": "hello11"}))
    # t2 = asyncio.create_task(test_func(agent_2, {"message": "hello22"}))
    #
    # await asyncio.gather(s_t1, s_t2, t1, t2)


if __name__ == '__main__':
    asyncio.run(start())
