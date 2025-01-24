# Building a Multi-Agent Meeting Scheduler System

## Core Components

### Data Models

```python
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
```

### Participant Agent

```python
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
    async def handle_availability_request(self, data: AvailabilityRequest,
                                          time: int, agent: AgentDetail):
        is_available = any(self.is_overlap(slot, data.time_slot,
                                           data.time_slot.duration)
                           for slot in self.available_times)
        await self.broadcast_message(AvailabilityResponse(
            owner=self.details().name,
            time_slot=data.time_slot,
            accepted=is_available
        ))
```

### Coordinator Agent

```python
class Coordinator(Admin):
    def __init__(self, name: str, port: int):
        super().__init__(name=name, port=port)
        self.meeting_request = None
        self.agreed_slots = {}
        self.next_time_slot = None

    @on_run()
    async def handle_run(self, inputs: Meeting):
        self.meeting_request = inputs

    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        start_time = 8
        self.next_time_slot = TimeSlot(
            self.meeting_request.date,
            start_time,
            start_time + self.meeting_request.duration
        )
        await self.broadcast_message(
            AvailabilityRequest(time_slot=self.next_time_slot)
        )

    @on(AvailabilityResponse)
    async def handle_availability_response(self, data: AvailabilityResponse,
                                           time: int, agent: AgentDetail):
        if not data.accepted:
            current_slot = data.time_slot
            next_slot = TimeSlot(
                self.meeting_request.date,
                current_slot.start_time + 1,
                current_slot.start_time + 1 + self.meeting_request.duration
            )
            if next_slot.end_time > self.next_time_slot.end_time:
                self.next_time_slot = next_slot
                await self.broadcast_message(
                    AvailabilityRequest(time_slot=self.next_time_slot)
                )
            return

        time_slot_key = str(data.time_slot)
        slots = self.agreed_slots.get(time_slot_key, [])
        if data.owner not in slots:
            slots.append(data.owner)
            self.agreed_slots[time_slot_key] = slots
            if len(slots) >= self.meeting_request.minimum_participants:
                await self.stop()
```

## System Usage

```python
async def main():
    participants = [
        Participant("Alice", [
            TimeSlot("2024-07-21", 9, 12),
            TimeSlot("2024-07-21", 14, 18)
        ]),
        Participant("Bob", [
            TimeSlot("2024-07-21", 10, 13),
            TimeSlot("2024-07-21", 15, 17)
        ]),
    ]

    admin = Coordinator(name="admin", port=8888)
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
```

## Key Features

1. Time slot management with overlap detection
2. Asynchronous availability requests/responses
3. Automatic meeting slot negotiation
4. Minimum participant requirement tracking
5. Decentralized participant coordination

## Customization Options

1. Add priority-based scheduling:

```python
@dataclass
class Meeting:
    priority: int  # Add priority field
```

2. Implement preferred time slots:

```python
@dataclass
class AvailabilityResponse:
    preference_score: int  # Add preference rating
```

3. Add recurring meeting support:

```python
@dataclass
class Meeting:
    recurrence: str  # weekly, monthly, etc.
```