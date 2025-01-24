#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import pickle

from pydantic.dataclasses import dataclass

from ceylon import Admin, Worker
from ceylon import AgentDetail
from ceylon import on


@dataclass
class TimeSlot:
    date: str
    start_time: int
    end_time: int

    @property
    def duration(self):
        return self.end_time - self.start_time


@dataclass
class Meeting:
    name: str
    date: str
    duration: int
    minimum_participants: int


@dataclass
class AvailabilityRequest:
    time_slot: TimeSlot


@dataclass
class AvailabilityResponse:
    owner: str
    time_slot: TimeSlot
    accepted: bool


class Participant(Worker):
    def __init__(self, name: str, available_times: list[TimeSlot]):
        super().__init__(name=name, role="participant")
        self.available_times = available_times

    @staticmethod
    def is_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration

    @on(AvailabilityRequest)
    async def handle_availability_request(self, data: AvailabilityRequest, time: int, agent: AgentDetail):
        print(f"Participant {self.details().name} received availability request {data.time_slot}")
        is_available = any(self.is_overlap(slot, data.time_slot, data.time_slot.duration)
                           for slot in self.available_times)
        await self.broadcast_message(AvailabilityResponse(
            owner=self.details().name,
            time_slot=data.time_slot,
            accepted=is_available
        ))


class Coordinator(Admin):
    def __init__(self, name: str, port: int):
        super().__init__(name=name, port=port)
        self.meeting_request = None
        self.agreed_slots = {}
        self.next_time_slot = None


admin = Coordinator(name="admin", port=8888)


@admin.on_run()
async def handle_run(inputs: Meeting):
    admin.meeting_request = inputs
    print("Meeting Schedule request:", admin.meeting_request)


@admin.on_connect("*")
async def handle_connection(topic: str, agent: AgentDetail):
    print(f"Agent connected to {admin.details().name}: {agent}")
    start_time = 8
    admin.next_time_slot = TimeSlot(
        admin.meeting_request.date,
        start_time,
        start_time + admin.meeting_request.duration
    )
    await admin.broadcast_message(AvailabilityRequest(time_slot=admin.next_time_slot))


@admin.on(AvailabilityResponse)
async def handle_availability_response(data: AvailabilityResponse, time: int, agent: AgentDetail):
    if not data.accepted:
        current_slot = data.time_slot
        next_slot = TimeSlot(
            admin.meeting_request.date,
            current_slot.start_time + 1,
            current_slot.start_time + 1 + admin.meeting_request.duration
        )
        if next_slot.end_time > admin.next_time_slot.end_time:
            admin.next_time_slot = next_slot
            await admin.broadcast_message(AvailabilityRequest(time_slot=admin.next_time_slot))
        return

    time_slot_key = str(data.time_slot)
    print(f"{data.owner} accepts {data.time_slot}")

    slots = admin.agreed_slots.get(time_slot_key, [])
    if data.owner not in slots:
        slots.append(data.owner)
        admin.agreed_slots[time_slot_key] = slots
        if len(slots) >= admin.meeting_request.minimum_participants:
            print(f"Meeting scheduled with {slots} participants at {data.time_slot}")
            await admin.stop()


async def main():
    participants = [
        Participant("Alice", [TimeSlot("2024-07-21", 9, 12), TimeSlot("2024-07-21", 14, 18)]),
        Participant("Bob", [TimeSlot("2024-07-21", 10, 13), TimeSlot("2024-07-21", 15, 17)]),
        Participant("Charlie", [TimeSlot("2024-07-21", 11, 14), TimeSlot("2024-07-21", 16, 18)]),
    ]
    #
    # coordinator = Coordinator(name="Coordinator", port=4587)

    meeting = Meeting(
        name="Meeting 1",
        duration=1,
        date="2024-07-21",
        minimum_participants=3
    )

    await admin.start_agent(
        inputs=pickle.dumps(meeting),
        workers=participants
    )


if __name__ == '__main__':
    asyncio.run(main())
