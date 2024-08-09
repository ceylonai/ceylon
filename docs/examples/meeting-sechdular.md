# Simplified Meeting Scheduler Tutorial

## Introduction

This tutorial will show you how to create a simple meeting scheduler using Python. The scheduler will help find a time
when everyone can attend a meeting.

## Step 1: Install the Required Tools

First, we need to install some special tools (called libraries) that will help us build our scheduler. You can install
these using a program called pip. Type this into your computer's command line:

```
pip install ceylon
```

## Step 2: Define the Building Blocks

Now, we'll create some "blueprints" for the different parts of our scheduler. These blueprints are called classes, and
they help us organize our code.

```python
from pydantic.dataclasses import dataclass


@dataclass
class Meeting:
    name: str  # The name of the meeting
    date: str  # The date of the meeting
    duration: int  # How long the meeting will last
    minimum_participants: int  # The smallest number of people needed for the meeting


@dataclass
class TimeSlot:
    date: str  # The date of the time slot
    start_time: int  # When the time slot starts
    end_time: int  # When the time slot ends


@dataclass
class AvailabilityRequest:
    time_slot: TimeSlot  # The time slot we're asking about


@dataclass
class AvailabilityResponse:
    owner: str  # The name of the person responding
    time_slot: TimeSlot  # The time slot they're responding about
    accepted: bool  # Whether they can attend (True) or not (False)
```

## Step 3: Create the Participant

Next, we'll create a "Participant" who can tell us if they're available for a meeting.

```python
from ceylon import Agent, on_message
from typing import List


class Participant(Agent):
    name: str  # The participant's name
    available_times: List[TimeSlot]  # A list of times when they're free

    def __init__(self, name, available_times):
        self.name = name
        self.available_times = available_times
        super().__init__(name=name, workspace_id="time_scheduling", admin_peer="Coordinator", admin_port=8000)

    @on_message(type=AvailabilityRequest)
    async def on_availability_request(self, data: AvailabilityRequest):
        # Check if the participant is available at the requested time
        if self.is_available(data.time_slot):
            # If available, send a positive response
            await self.broadcast_data(AvailabilityResponse(owner=self.name, time_slot=data.time_slot, accepted=True))
        else:
            # If not available, send a negative response
            await self.broadcast_data(AvailabilityResponse(owner=self.name, time_slot=data.time_slot, accepted=False))

    def is_available(self, requested_slot: TimeSlot) -> bool:
        # Check if the requested time slot overlaps with any of the participant's available times
        for available_slot in self.available_times:
            if self.slots_overlap(available_slot, requested_slot):
                return True
        return False

    @staticmethod
    def slots_overlap(slot1: TimeSlot, slot2: TimeSlot) -> bool:
        # Check if two time slots overlap
        return slot1.start_time < slot2.end_time and slot2.start_time < slot1.end_time
```

## Step 4: Create the Coordinator

The Coordinator is in charge of finding a time that works for everyone.

```python
from ceylon import CoreAdmin, on_message
import pickle


class Coordinator(CoreAdmin):
    meeting: Meeting = None
    agreed_slots = {}
    next_time_slot = None

    def __init__(self):
        super().__init__(name="time_scheduling", port=8000)

    async def run(self, inputs: "bytes"):
        # Unpack the meeting details
        self.meeting = pickle.loads(inputs)
        print("Meeting Schedule request: ", self.meeting)

    async def on_agent_connected(self, topic: "str", agent_id: "str"):
        # When a new participant connects, start asking about availability
        if self.next_time_slot is None and self.meeting is not None:
            self.next_time_slot = TimeSlot(self.meeting.date, 0, self.meeting.duration)
            await self.broadcast_data(AvailabilityRequest(time_slot=self.next_time_slot))

    @on_message(type=AvailabilityResponse)
    async def on_availability_request(self, data: AvailabilityResponse):
        # Process responses from participants
        if data.accepted:
            # If the participant is available, add them to the list for this time slot
            time_slot_key = f"{data.time_slot}"
            if time_slot_key in self.agreed_slots:
                self.agreed_slots[time_slot_key].append(data.owner)
            else:
                self.agreed_slots[time_slot_key] = [data.owner]

            # Check if we have enough participants for this time slot
            if len(self.agreed_slots[time_slot_key]) >= self.meeting.minimum_participants:
                print(f"Meeting scheduled! Participants: {self.agreed_slots[time_slot_key]}, Time: {data.time_slot}")
                await self.stop()
                return

        # If we haven't found a suitable time yet, try the next time slot
        self.next_time_slot = TimeSlot(self.meeting.date, self.next_time_slot.start_time + 1,
                                       self.next_time_slot.start_time + 1 + self.meeting.duration)
        await self.broadcast_data(AvailabilityRequest(time_slot=self.next_time_slot))
```

## Step 5: Run the Scheduler

Finally, we'll set up our participants and start the scheduler.

```python
import asyncio


async def main():
    # Create our participants with their available times
    alice = Participant("Alice", [TimeSlot("2024-07-21", 9, 12), TimeSlot("2024-07-21", 14, 18)])
    bob = Participant("Bob", [TimeSlot("2024-07-21", 10, 13), TimeSlot("2024-07-21", 15, 17)])
    charlie = Participant("Charlie", [TimeSlot("2024-07-21", 11, 14), TimeSlot("2024-07-21", 16, 18)])

    # Create our coordinator
    coordinator = Coordinator()

    # Start the scheduling process
    meeting = Meeting(name="Team Meeting", duration=2, date="2024-07-21", minimum_participants=3)
    await coordinator.arun_admin(
        inputs=pickle.dumps(meeting),
        workers=[alice, bob, charlie]
    )


if __name__ == '__main__':
    asyncio.run(main())
```

## How It Works

1. We set up our "Participants" (Alice, Bob, and Charlie) and tell the computer when they're free.
2. We create a "Coordinator" who's in charge of finding a time that works for everyone.
3. The Coordinator asks each Participant if they're free at a certain time.
4. Each Participant checks their schedule and tells the Coordinator if they can make it.
5. If enough people can make it, the Coordinator schedules the meeting.
6. If not enough people can make it, the Coordinator tries a different time.
7. This keeps going until a good time is found or we run out of options.

## Real-World Improvements

To make this work better in the real world, we could:

1. Connect it to people's actual calendars (like Google Calendar).
2. Send out email reminders about the meeting.
3. Allow for scheduling multiple meetings at once.
4. Let people join or leave the meeting after it's been scheduled.
5. Give some meetings or people higher priority.
6. Suggest different days if no time works for everyone.
7. Create a user-friendly website for people to use the scheduler.

These improvements would make our simple scheduler much more useful for real-life situations!