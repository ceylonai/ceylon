import abc

import orjson
from pydantic import BaseModel

from rk_core import Processor, EventType, Event


class AgentDetail(BaseModel):
    name: str
    id: str


class AbsAgent(abc.ABC):
    name = ""
    other_agents = {}
    broadcast_messages = []

    def __init__(self, name):
        self.name = name

    # @Processor(event_type=EventType.Any)
    # async def any(self, data: Event):
    #     print(f"{self.name}{data.event_type} received: {data.content}")

    @Processor(event_type=EventType.AgentConnected)
    async def agent_connected(self, data: Event):
        peer_id = bytes(data.content).decode('utf-8')
        self.other_agents[peer_id] = None
        print(f"{self.name}{data.event_type} received: {peer_id} \n")
        await self.publish({
            "message": f"{peer_id} connected need your name",
        })

    @Processor(event_type=EventType.AgentConnected)
    async def response_name(self, data: Event):
        pass

    async def publish(self, message):
        msg = orjson.dumps(message)
        await self.publisher.publish(msg)
