import asyncio
import pickle
from typing import List

from pydantic.dataclasses import dataclass

from ceylon.workspace.admin import Admin
from ceylon.workspace.runner import RunnerInput
from ceylon.workspace.worker import Worker

admin_port = 8000
admin_peer = "Coordinator"
workspace_id = "time_scheduling"


@dataclass(repr=True)
class Meeting:
    name: str
    date: str
    duration: int
    minimum_participants: int

    def __str__(self):
        return f"{self.name} {self.date} {self.duration} {self.minimum_participants}"


@dataclass(repr=True)
class TimeSlot:
    date: str
    start_time: int
    end_time: int

    @property
    def duration(self):
        return self.end_time - self.start_time

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time}"

    def is_greater_than(self, other):
        return self.end_time > other.end_time


@dataclass(repr=True)
class AvailabilityRequest:
    time_slot: TimeSlot


@dataclass(repr=True)
class AvailabilityResponse:
    owner: str
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
        data = pickle.loads(data)
        if type(data) == AvailabilityRequest:
            data: AvailabilityRequest = data
            # Check if the time slot is available
            if not any(self.is_overlap(slot, data.time_slot, data.time_slot.duration) for slot in self.available_times):
                # print(f"Time slot {data.time_slot} is not available for {self.details().name}")
                await self.broadcast(pickle.dumps(
                    AvailabilityResponse(owner=self.details().name, time_slot=data.time_slot, accepted=False)))
            else:
                # print(f"Time slot {data.time_slot} is available")
                await self.broadcast(pickle.dumps(
                    AvailabilityResponse(owner=self.details().name, time_slot=data.time_slot, accepted=True)))

    @staticmethod
    def is_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration


class Coordinator(Admin):
    meeting: Meeting = None
    agreed_slots = {}
    next_time_slot = None

    def __init__(self):
        super().__init__(name=workspace_id, port=admin_port)

    @staticmethod
    def is_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration

    async def run(self, inputs: "bytes"):
        self.meeting = pickle.loads(inputs)
        print("Meeting Schedule request: ", self.meeting)

    async def on_agent_connected(self, topic: "str", agent_id: "str"):
        if self.next_time_slot is None and self.meeting is not None:
            self.next_time_slot = TimeSlot(self.meeting.date, 0, self.meeting.duration)
            await self.broadcast(pickle.dumps(AvailabilityRequest(time_slot=self.next_time_slot)))

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == AvailabilityResponse:
            data: AvailabilityResponse = data
            if data.accepted:
                time_slot_key = f"{data.time_slot}"
                print(f"{data.owner} accepts {data.time_slot}")
                if time_slot_key in self.agreed_slots:
                    slots = self.agreed_slots[time_slot_key]
                    if data.owner not in slots:
                        slots.append(data.owner)
                        self.agreed_slots[time_slot_key] = slots
                        if len(slots) >= self.meeting.minimum_participants:
                            print(f"Meeting {slots} participants agreed on {data.time_slot}")
                            await self.stop()
                else:
                    self.agreed_slots[time_slot_key] = [data.owner]

            current_time_slot = data.time_slot
            calculated_next_time_slot = TimeSlot(self.meeting.date, current_time_slot.start_time + 1,
                                                 current_time_slot.start_time + 1 + self.meeting.duration)

            if calculated_next_time_slot.is_greater_than(self.next_time_slot):
                self.next_time_slot = calculated_next_time_slot
                # print(f"Next time slot: {self.next_time_slot}")
                await self.broadcast(pickle.dumps(AvailabilityRequest(time_slot=self.next_time_slot)))


async def main():
    agent1 = Participant("Alice", [TimeSlot("2024-07-21", 9, 12), TimeSlot("2024-07-21", 14, 18)])
    agent2 = Participant("Bob", [TimeSlot("2024-07-21", 10, 13), TimeSlot("2024-07-21", 15, 17)])
    agent3 = Participant("Charlie", [TimeSlot("2024-07-21", 11, 14), TimeSlot("2024-07-21", 16, 18)])
    agent4 = Participant("David", [TimeSlot("2024-07-21", 11, 14), TimeSlot("2024-07-21", 16, 18)])
    agent5 = Participant("Kevin", [TimeSlot("2024-07-21", 10, 13), TimeSlot("2024-07-21", 15, 17)])

    coordinator = Coordinator()
    await coordinator.run_admin(
        inputs=pickle.dumps(Meeting(name="Meeting 1", duration=2, date="2024-07-21", minimum_participants=3)),
        workers=[agent1, agent2, agent3, agent4, agent5]
    )


if __name__ == '__main__':
    # enable_log("INFO")
    asyncio.run(main())
