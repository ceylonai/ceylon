import asyncio
import logging

import rk_core

logging.basicConfig(level=logging.INFO)


class AgentBasic:

    def __init__(self, name):
        self.name = name

    @rk_core.Processor(event_type=rk_core.EventType.Start)
    async def on_start(self, event: rk_core.Event):
        print(f"Agendddddddt:{self.name} Start {event.content}")
        while True:
            self.publisher.publish("hello")
            await asyncio.sleep(1)

    @rk_core.Processor(event_type=rk_core.EventType.Data)
    async def on_data(self, event: rk_core.Event):
        print(f"Agentssssssss:{self.name} Data {event.content} from {event.creator}")


if __name__ == '__main__':
    agent_manager = rk_core.AgentManager()
    agent_manager.register_agent(AgentBasic("AGENT1"))
    agent_manager.register_agent(AgentBasic("AGENT2"))
    agent_manager.start()
