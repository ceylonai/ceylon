# Advanced Meeting Scheduler Tutorial

## Introduction

This tutorial will show you how to create a distributed meeting scheduler using Python with Ceylon framework. The scheduler finds optimal meeting times by coordinating between multiple participants using an agent-based approach.

## Step 1: Set Up the Environment

First, install the required dependencies:

```bash
pip install ceylon pydantic
```

## Step 2: Define the Data Models

We'll use Pydantic for data validation and serialization. Here are our core data models:

```python
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from typing import List, Any

# Input model for the scheduler
class RunnerInput(BaseModel):
    request: Any
    
    class Config:
        arbitrary_types_allowed = True

@dataclass(repr=True)
class Meeting:
    name: str            # Meeting name
    date: str           # Meeting date
    duration: int       # Duration in hours
    minimum_participants: int  # Minimum required participants

@dataclass(repr=True)
class TimeSlot:
    date: str          # Date of the slot
    start_time: int    # Start hour (0-23)
    end_time: int      # End hour (0-23)
    
    @property
    def duration(self):
        return self.end_time - self.start_time
    
    def is_greater_than(self, other):
        return self.end_time > other.end_time

@dataclass(repr=True)
class AvailabilityRequest:
    time_slot: TimeSlot

@dataclass(repr=True)
class AvailabilityResponse:
    owner: str         # Participant name
    time_slot: TimeSlot
    accepted: bool     # Availability status
```

## Step 3: Implement the Participant Agent

The Participant class represents each meeting attendee:

```python
class Participant(Worker):
    name: str
    available_times: List[TimeSlot]

    def __init__(self, name, available_times):
        self.name = name
        self.available_times = available_times
        super().__init__(name=name, workspace_id=workspace_id, 
                        admin_peer=admin_peer, admin_port=admin_port)

    async def on_message(self, agent_id: str, data: bytes, time: int):
        data = pickle.loads(data)
        if type(data) == AvailabilityRequest:
            data: AvailabilityRequest = data
            # Check availability and respond
            is_available = any(self.is_overlap(slot, data.time_slot, 
                             data.time_slot.duration) 
                             for slot in self.available_times)
            
            response = AvailabilityResponse(
                owner=self.details().name,
                time_slot=data.time_slot,
                accepted=is_available
            )
            await self.broadcast(pickle.dumps(response))

    @staticmethod
    def is_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration
```

## Step 4: Implement the Coordinator

The Coordinator manages the scheduling process:

```python
class Coordinator(Admin):
    meeting: Meeting = None
    agreed_slots = {}
    next_time_slot = None

    def __init__(self):
        super().__init__(name=workspace_id, port=admin_port)

    async def run(self, inputs: bytes):
        input: RunnerInput = pickle.loads(inputs)
        self.meeting = input.request
        print("Meeting Schedule request: ", self.meeting)

    async def on_agent_connected(self, topic: str, agent_id: str):
        if self.next_time_slot is None and self.meeting is not None:
            self.next_time_slot = TimeSlot(
                self.meeting.date, 0, self.meeting.duration
            )
            await self.broadcast(pickle.dumps(
                AvailabilityRequest(time_slot=self.next_time_slot)
            ))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        data = pickle.loads(data)
        if type(data) == AvailabilityResponse:
            await self.handle_availability_response(data)

    async def handle_availability_response(self, data: AvailabilityResponse):
        if data.accepted:
            time_slot_key = f"{data.time_slot}"
            print(f"{data.owner} accepts {data.time_slot}")
            
            # Track acceptances and check if we have enough participants
            if time_slot_key in self.agreed_slots:
                slots = self.agreed_slots[time_slot_key]
                if data.owner not in slots:
                    slots.append(data.owner)
                    self.agreed_slots[time_slot_key] = slots
                    if len(slots) >= self.meeting.minimum_participants:
                        print(f"Meeting {slots} participants agreed on {data.time_slot}")
                        await self.stop()
                        return
            else:
                self.agreed_slots[time_slot_key] = [data.owner]

        # Try next time slot
        current_time_slot = data.time_slot
        next_time_slot = TimeSlot(
            self.meeting.date,
            current_time_slot.start_time + 1,
            current_time_slot.start_time + 1 + self.meeting.duration
        )

        if next_time_slot.is_greater_than(self.next_time_slot):
            self.next_time_slot = next_time_slot
            await self.broadcast(pickle.dumps(
                AvailabilityRequest(time_slot=self.next_time_slot)
            ))
```

## Step 5: Run the Scheduler

Here's how to set up and run the scheduler:

```python
async def main():
    # Create participants with their available times
    participants = [
        Participant("Alice", [
            TimeSlot("2024-07-21", 9, 12), 
            TimeSlot("2024-07-21", 14, 18)
        ]),
        Participant("Bob", [
            TimeSlot("2024-07-21", 10, 13), 
            TimeSlot("2024-07-21", 15, 17)
        ]),
        Participant("Charlie", [
            TimeSlot("2024-07-21", 11, 14), 
            TimeSlot("2024-07-21", 16, 18)
        ]),
        Participant("David", [
            TimeSlot("2024-07-21", 11, 14), 
            TimeSlot("2024-07-21", 16, 18)
        ]),
        Participant("Kevin", [
            TimeSlot("2024-07-21", 10, 13), 
            TimeSlot("2024-07-21", 15, 17)
        ])
    ]

    # Create and run coordinator
    coordinator = Coordinator()
    meeting = Meeting(
        name="Meeting 1",
        duration=2,
        date="2024-07-21",
        minimum_participants=3
    )
    
    await coordinator.arun_admin(
        inputs=pickle.dumps(RunnerInput(request=meeting)),
        workers=participants
    )

if __name__ == '__main__':
    asyncio.run(main())
```

## How It Works

1. The scheduler uses a distributed agent-based architecture where each participant is an independent agent.
2. The Coordinator initiates the scheduling process by sending availability requests for time slots.
3. Each Participant agent checks their availability and responds to requests.
4. The Coordinator tracks responses and finds a time slot that works for the minimum required participants.
5. The system uses efficient overlap detection to check time slot compatibility.

## Key Improvements from Basic Version

1. Uses Pydantic for robust data validation
2. Implements proper serialization/deserialization
3. Adds duration-aware time slot overlap detection
4. Supports multiple participants beyond the minimum required
5. Includes better error handling and type safety
6. Uses asynchronous communication for better performance

## Potential Enhancements

1. Add persistence layer for storing scheduling history
2. Implement priority-based scheduling
3. Add support for recurring meetings
4. Implement calendar integration (Google Calendar, Outlook)
5. Add conflict resolution for competing meeting requests
6. Implement notification system for scheduled meetings
7. Add support for different time zones
8. Create a REST API interface for web/mobile clients