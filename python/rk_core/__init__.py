import asyncio
import logging
import uuid
from multiprocessing import allow_connection_pickling
from threading import Thread
from time import sleep

from rk_core.rk_core import FunctionInfo, EventProcessor, MessageProcessor, Server, EventType, Event

from rk_core import rk_core

__doc__ = rk_core.__doc__
if hasattr(rk_core, "__all__"):
    __all__ = rk_core.__all__
# logging.basicConfig(level=logging.INFO)

rakun_version = rk_core.get_version()
logging.info(f"Rakun version: {rakun_version}")

import tracemalloc

tracemalloc.start()


class ProcessorWrapper:
    def __init__(self, func, event_type):
        self.name = func.__qualname__
        self.event_type = event_type
        self.is_decorated = True  # identifiable attribute
        self.args = func.__code__.co_varnames
        self.func = func

    def function(self, instance):
        def function(*args, **kwargs):
            return self.func(instance, *args, **kwargs)

        return function

    @classmethod
    def fill_agent(cls, agent):
        agent.decorated_methods = []
        for fn in dir(agent):
            attr = getattr(agent, fn)
            if isinstance(attr, ProcessorWrapper):
                name = attr.name
                args = attr.args
                event_type = attr.event_type
                function = attr.function(agent)  # Agent Instance need to call with function
                agent.decorated_methods.append((name, args, event_type, function))


class Processor:
    def __init__(self, event_type):
        self.event_type = event_type

    def __call__(self, func):
        return ProcessorWrapper(func, self.event_type)


class AgentWrapper:
    def __init__(self, agent):
        self.id = uuid.uuid4()
        self.agent = agent
        self.start_time = None

        # self.publisher = MessageProcessor()
        self.server = Server(agent.name)
        self.agent.decorated_methods = []
        # self.publisher = self.server.publisher

        ProcessorWrapper.fill_agent(self.agent)
        for dm in self.agent.decorated_methods:
            name, args, event_type, function = dm
            fnc_info = FunctionInfo(function, True, len(args))
            ep = EventProcessor(name, f"{self.id}", fnc_info, event_type)
            self.server.add_event_processor(ep)

        # self.publisher.start()
        self.agent.publisher = self.server.publisher()

    def __start__(self):
        self.server.start()

    def start(self):
        self.__start__()

    def stop(self):
        evt = asyncio.get_event_loop()

        async def stop():
            await self.agent.__state__("stop")
            exit(-1)

        evt.call_soon_threadsafe(stop)


class AgentManager:

    def __init__(self):
        self.agents = []

    def register(self, agent, order=0):
        """"
        Register an agent
        :param agent:
        :param order: Highest on start first
        """
        self.agents.append({
            "agent": AgentWrapper(agent),
            "order": order
        })

    def unregister(self, agent):
        self.agents = list(filter(lambda x: x["agent"].agent.name != agent.name, self.agents))

    def get_agents(self):
        return [x["agent"] for x in self.agents]

    def start(self):
        logging.info("Starting Rakun.")
        allow_connection_pickling()

        ordered_agents = reversed(sorted(self.agents, key=lambda x: x["order"]))
        ordered_agents = [x["agent"] for x in ordered_agents]

        agents_thread = []
        for agent in ordered_agents:
            logging.info(("Starting agent", agent.agent.name))
            t = Thread(target=agent.start)
            agents_thread.append(t)
            t.start()
            sleep(5)
        logging.info("Waiting for agents")
