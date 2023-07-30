import abc
import enum

import orjson
from pydantic import BaseModel

from rk_core import Processor, EventType, Event


class MessageType(enum.StrEnum):
    AGENT_IDENTIFICATION_DETAIL_REQUEST = "AGENT_IDENTIFICATION_DETAIL_REQUEST"
    AGENT_IDENTIFICATION_DETAIL_RESPONSE = "AGENT_IDENTIFICATION_DETAIL_RESPONSE"


class AgentDetail(BaseModel):
    name: str
    peer_id: str


class Message(BaseModel):
    sender_id: str
    thread_id: str
    title: str
    data: object


class DetailRequest(BaseModel):
    peer_id: str


class AbsAgent(abc.ABC):
    name = ""
    other_agents = {}
    broadcast_messages = []

    def __init__(self, name):
        self.name = name
        self.id = None

    # @Processor(event_type=EventType.Any)
    # async def any(self, data: Event):
    #     print(f"{self.name}{data.event_type} received: {data.content}")
    @Processor(event_type=EventType.Start)
    async def any(self, data: Event):
        peer_id = bytes(data.content).decode('utf-8')
        self.id = peer_id

    @Processor(event_type=EventType.AgentConnected)
    async def agent_connected(self, data: Event):
        peer_id = bytes(data.content).decode('utf-8')
        self.other_agents[peer_id] = None
        await self.publish(Message(
            sender_id=self.id,
            thread_id="",
            title=MessageType.AGENT_IDENTIFICATION_DETAIL_REQUEST,
            data=DetailRequest(peer_id=peer_id)
        ).model_dump_json())

    @Processor(event_type=EventType.Data)
    async def register_agent(self, event: Event):
        data = orjson.loads(bytes(event.content).decode('utf-8'))
        message = Message.model_validate_json(data)
        if message.title == MessageType.AGENT_IDENTIFICATION_DETAIL_RESPONSE.value:
            request = AgentDetail.model_validate(message.data)
            self.other_agents[request.peer_id] = request
            print(f"{request.name}----{request.peer_id} connected with {self.name}----{self.id}")

    @Processor(event_type=EventType.Data)
    async def response_detail(self, event: Event):
        data = orjson.loads(bytes(event.content).decode('utf-8'))
        message = Message.model_validate_json(data)
        if message.title == MessageType.AGENT_IDENTIFICATION_DETAIL_REQUEST.value:
            request = DetailRequest.model_validate(message.data)
            if request.peer_id == self.id:
                await self.publish(Message(
                    sender_id=self.id,
                    thread_id=message.thread_id,
                    title=MessageType.AGENT_IDENTIFICATION_DETAIL_RESPONSE,
                    data=AgentDetail(
                        name=self.name,
                        peer_id=self.id
                    )
                ).model_dump_json())

    async def publish(self, message):
        msg = orjson.dumps(message)
        await self.publisher.publish(msg)
