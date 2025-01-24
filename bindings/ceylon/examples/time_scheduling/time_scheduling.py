import asyncio
from dataclasses import dataclass
from typing import List
from ceylon import BaseAgent, AgentDetail, on, on_run, on_connect, Worker, Admin


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
    participant: str
    time_slot: TimeSlot
    available: bool


class Participant(Worker):
    def __init__(self, name: str, available_slots: List[TimeSlot], admin_peer: str):
        super().__init__(name=name, admin_peer=admin_peer)
        self.available_slots = available_slots

    @staticmethod
    def has_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration

    @on(AvailabilityRequest)
    async def handle_request(self, data: AvailabilityRequest, time: int, agent: AgentDetail):
        is_available = any(
            self.has_overlap(slot, data.time_slot, data.time_slot.duration)
            for slot in self.available_slots
        )

        response = AvailabilityResponse(
            participant=self.name,
            time_slot=data.time_slot,
            available=is_available
        )
        await self.broadcast_message(response)

    @on_run()
    async def handle_run(self, inputs: bytes):
        while True:
            await asyncio.sleep(0.1)


class Scheduler(Admin):
    def __init__(self, meeting: Meeting, port: int = 8000):
        super().__init__(name="scheduler", port=port)
        self.meeting = meeting
        self.agreed_slots = {}
        self.current_slot = None

    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        if not self.current_slot:
            self.current_slot = TimeSlot(
                self.meeting.date,
                8,  # Start at 8 AM
                8 + self.meeting.duration
            )
            await self.broadcast_message(AvailabilityRequest(time_slot=self.current_slot))

    @on(AvailabilityResponse)
    async def handle_response(self, data: AvailabilityResponse, time: int, agent: AgentDetail):
        if not data.available:
            next_slot = TimeSlot(
                self.meeting.date,
                self.current_slot.start_time + 1,
                self.current_slot.start_time + 1 + self.meeting.duration
            )
            self.current_slot = next_slot
            await self.broadcast_message(AvailabilityRequest(time_slot=next_slot))
            return

        slot_key = f"{data.time_slot.date}_{data.time_slot.start_time}"
        if slot_key not in self.agreed_slots:
            self.agreed_slots[slot_key] = []

        if data.participant not in self.agreed_slots[slot_key]:
            self.agreed_slots[slot_key].append(data.participant)

        if len(self.agreed_slots[slot_key]) >= self.meeting.minimum_participants:
            print(f"Meeting scheduled at {data.time_slot.date} {data.time_slot.start_time}:00")
            print(f"Participants: {', '.join(self.agreed_slots[slot_key])}")
            await self.stop()

    @on_run()
    async def handle_run(self, inputs: bytes):
        while True:
            await asyncio.sleep(0.1)


async def main():
    meeting = Meeting(
        name="Team Sync",
        date="2024-07-21",
        duration=1,
        minimum_participants=3
    )

    scheduler = Scheduler(meeting)
    scheduler_details = scheduler.details()

    participants = [
        Participant("Alice", [
            TimeSlot("2024-07-21", 9, 12),
            TimeSlot("2024-07-21", 14, 18)
        ], admin_peer=scheduler_details.id),
        Participant("Bob", [
            TimeSlot("2024-07-21", 10, 13),
            TimeSlot("2024-07-21", 15, 17)
        ], admin_peer=scheduler_details.id),
        Participant("Charlie", [
            TimeSlot("2024-07-21", 11, 14),
            TimeSlot("2024-07-21", 16, 18)
        ], admin_peer=scheduler_details.id)
    ]

    await scheduler.start_agent(b"", participants)


if __name__ == "__main__":
    asyncio.run(main())
