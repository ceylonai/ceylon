import asyncio
import uuid

from rk_core.rk_core import Server, FunctionInfo, EventProcessor, EventType
from rk_core.__agent_func import EventProcessorWrapper


class AgentWrapper:
    def __init__(self, agent):
        self.id = uuid.uuid4()
        self.agent = agent
        self.start_time = None

        # self.publisher = MessageProcessor()
        self.server = Server(agent.name)
        self.agent.decorated_methods = []
        # self.publisher = self.server.publisher

        EventProcessorWrapper.fill_agent(self.agent)
        for dm in self.agent.decorated_methods:
            name, args, event_type, function = dm
            fnc_info = FunctionInfo(function, True, len(args))
            ep = EventProcessor(name, f"{self.id}", fnc_info, event_type)

            if event_type == EventType.OnBoot:
                self.server.add_startup_handler(ep)
            elif event_type == EventType.OnShutdown:
                self.server.add_shutdown_handler(ep)
            else:
                self.server.add_event_processor(ep)

        # self.publisher.start()
        self.agent.publisher = self.server.publisher()

    def __start__(self):
        self.server.start()
        pass

    def start(self):
        self.__start__()

    def stop(self):
        evt = asyncio.get_event_loop()

        async def stop():
            await self.agent.__state__("stop")
            exit(-1)

        evt.call_soon_threadsafe(stop)
