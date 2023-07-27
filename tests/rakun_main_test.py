import asyncio
import logging
import random

# import names

import rk_core

logging.basicConfig(level=logging.INFO)


class AgentBasic:

    def __init__(self, name):
        self.name = name
        self.count = 0

    @rk_core.Processor(event_type=rk_core.EventType.Start)
    async def on_start(self, event: rk_core.Event):
        print(f"Agent Started:{self.name} Start {event.content}")
        while True:
            self.publisher.publish(f"hello {self.count}")
            rn = random.randint(5, 10)
            await asyncio.sleep(rn)
            self.count += 1

    @rk_core.Processor(event_type=rk_core.EventType.Data)
    async def on_data(self, event: rk_core.Event):
        print(f"Agent Got Message:{self.name} Data {event.content} from {event.creator}")


if __name__ == '__main__':
    agent_manager = rk_core.AgentManager()
    # name = names.get_full_name(gender='male')
    agent_manager.register_agent(AgentBasic("AGENT1"))
    # agent_manager.register_agent(AgentBasic("AGENT2"))
    # agent_manager.register_agent(AgentBasic("AGENT3"))
    # agent_manager.register_agent(AgentBasic("AGENT4"))
    agent_manager.start()
