import asyncio
import threading
import uuid
from time import sleep

from rakun import rakun
import logging

__doc__ = rakun.__doc__
if hasattr(rakun, "__all__"):
    __all__ = rakun.__all__

logging.basicConfig(level=logging.DEBUG)


class AgentWrapper:
    def __init__(self, agent):
        self.id = uuid.uuid4()
        self.agent = agent
        self.start_time = None
        self.subscribe = rakun.MessageProcessor(self.__process_message__)

    async def __process_message__(self, message):
        print(f"Agent:{self.id} Message: {message}")

    async def __start__(self):
        self.start_time = rakun.get_time()
        await self.__state__("start")

        async def message_handler():
            res = self.subscribe.start()
            print(f"Agent:{self.id} Message: {res}")
            await res

        async def background():
            for i in range(10):
                await self.__state__(f"running {i}")

        async with asyncio.TaskGroup() as tg:
            background_task = tg.create_task(background())
            message_task = tg.create_task(message_handler())

        await self.__state__("stop")

    async def __state__(self, state):
        logging.info(f"{self.start_time} Agent:{self.id} State: {state}")
        await self.agent.__state__(state)

    def start(self):
        asyncio.run(self.__start__())

    def stop(self):
        evt = asyncio.get_event_loop()

        async def stop():
            await self.agent.__state__("stop")
            exit(-1)

        evt.call_soon_threadsafe(stop)


class AgentManager:

    def __init__(self):
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(AgentWrapper(agent))

    def unregister_agent(self, agent):
        # using id remove the agent
        self.agents = [agent for agent in self.agents if agent.id != agent.id]

    def get_agents(self):
        return [agent.agent for agent in self.agents]

    def start(self):
        logging.info("Starting Rakun.")

        agents_thread = []
        for agent in self.agents:
            t = threading.Thread(target=agent.start)
            agents_thread.append(t)
            t.start()
            sleep(0.001)

        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Stopping Rakun...")
            for agent in self.agents:
                agent.stop()
