import asyncio
import pickle
from typing import List

from pydantic import dataclasses

from ceylon.ceylon import enable_log
from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker

admin_port = 8000
admin_peer = "Coordinator"
workspace_id = "time_scheduling"


@dataclasses.dataclass
class Meeting:
    name: str
    duration: int
    minimum_participants: int


@dataclasses.dataclass
class TimeSlot:
    date: str
    start_time: int
    end_time: int

    @property
    def duration(self):
        return self.end_time - self.start_time


@dataclasses.dataclass
class AvailabilityRequest:
    time_slot: TimeSlot


@dataclasses.dataclass
class AvailabilityResponse:
    time_slot: TimeSlot
    accepted: bool


class Participant(Worker):
    name: str
    available_times: List[TimeSlot]

    def __init__(self, name, available_times):
        self.name = name
        self.available_times = available_times
        super().__init__(name=name, workspace_id=workspace_id, admin_peer=admin_peer, admin_port=admin_port)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"Agent on_message  {self.details().name}", agent_id, data, time)


class Coordinator(Admin):
    meeting_agents = []

    def __init__(self):
        super().__init__(name=workspace_id, port=admin_port)

    @staticmethod
    def is_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration

    async def on_agent_connected(self, topic: "str", agent_id: "str"):
        print(f"Agent {agent_id} connected to {topic}")
        await self.broadcast(pickle.dumps(AvailabilityRequest(time_slot=TimeSlot("2024-07-21", 9, 12))))


async def main():
    agent1 = Participant("Alice", [TimeSlot("2024-07-21", 9, 12), TimeSlot("2024-07-21", 14, 18)])
    agent2 = Participant("Bob", [TimeSlot("2024-07-21", 10, 13), TimeSlot("2024-07-21", 15, 17)])
    agent3 = Participant("Charlie", [TimeSlot("2024-07-21", 11, 14), TimeSlot("2024-07-21", 16, 18)])

    coordinator = Coordinator()
    await coordinator.run_admin(
        inputs=Meeting(name="Meeting 1", duration=2, minimum_participants=2),
        workers=[agent1, agent2, agent3]
    )


if __name__ == '__main__':
    # enable_log("INFO")
    asyncio.run(main())
