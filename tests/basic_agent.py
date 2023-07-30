import logging
# logging.basicConfig(level=logging.DEBUG)
import rk_core.agent.abstract_agent
from rk_core import Processor, EventType, AgentManager, Event


class BasicAgent(rk_core.agent.abstract_agent.AbsAgent):

    def __init__(self, name):
        super().__init__(name)
        print("BasicAgent created.")

    @Processor(event_type=EventType.OnBoot)
    async def on_start(self):
        print(f"{self.name} started")
        await self.publish({"hello": f"Greeting From {self.name} - world"})

    @Processor(event_type=EventType.Data)
    async def on_data(self, event: Event):
        print(f"{self.name} received: {event.content}")


if __name__ == '__main__':
    abc = BasicAgent("test1")
    bdc = BasicAgent("test2")

    agm = AgentManager()
    agm.register(abc, 1)
    agm.register(bdc, 2)
    agm.start()
