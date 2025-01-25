# Meeting Scheduler Code Explanation

## 1. Data Models

### TimeSlot
```python
@dataclass
class TimeSlot:
    date: str
    start_time: int
    end_time: int

    @property
    def duration(self):
        return self.end_time - self.start_time
```
- Uses Python's dataclass for automatic initialization
- Stores date as string and times as integers
- Calculates duration dynamically as property

### Meeting
```python
@dataclass
class Meeting:
    name: str
    date: str
    duration: int
    minimum_participants: int
```
- Defines meeting requirements
- Specifies minimum number of required participants
- Sets meeting duration in hours

### Message Classes
```python
@d[.ceylon_network](../../bindings/ceylon/examples/network_agent/.ceylon_network)ataclass
class AvailabilityRequest:
    time_slot: TimeSlot

@dataclass
class AvailabilityResponse:
    owner: str
    time_slot: TimeSlot
    accepted: bool
```
- `AvailabilityRequest`: Sent to check participant availability
- `AvailabilityResponse`: Participant's response indicating acceptance

## 2. Participant Agent

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

Key aspects:
1. Inherits from Ceylon's Worker class
2. Maintains list of available time slots
3. `is_overlap()` checks if two time slots overlap with sufficient duration
4. Uses `@on` decorator to handle availability requests
5. Broadcasts response to all agents

## 3. Coordinator Agent

```python
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
    start_time = 8
    admin.next_time_slot = TimeSlot(
        admin.meeting_request.date,
        start_time,
        start_time + admin.meeting_request.duration
    )
    await admin.broadcast_message(AvailabilityRequest(
        time_slot=admin.next_time_slot))
```

Key functionality:
1. Inherits from Ceylon's Admin class
2. Maintains state of scheduling process
3. Initializes with starting time slot when agents connect
4. Tracks agreed time slots and next time slot to try

### Response Handler
```python
@admin.on(AvailabilityResponse)
async def handle_availability_response(data: AvailabilityResponse, 
                                    time: int, agent: AgentDetail):
    if not data.accepted:
        current_slot = data.time_slot
        next_slot = TimeSlot(
            admin.meeting_request.date,
            current_slot.start_time + 1,
            current_slot.start_time + 1 + admin.meeting_request.duration
        )
        if next_slot.end_time > admin.next_time_slot.end_time:
            admin.next_time_slot = next_slot
            await admin.broadcast_message(
                AvailabilityRequest(time_slot=admin.next_time_slot))
        return

    time_slot_key = str(data.time_slot)
    slots = admin.agreed_slots.get(time_slot_key, [])
    if data.owner not in slots:
        slots.append(data.owner)
        admin.agreed_slots[time_slot_key] = slots
        if len(slots) >= admin.meeting_request.minimum_participants:
            print(f"Meeting scheduled with {slots} participants at {data.time_slot}")
            await admin.stop()
```

Response handling logic:
1. For rejections:
    - Creates next time slot
    - Broadcasts new availability request if needed
2. For acceptances:
    - Tracks accepting participant
    - Checks if minimum participants reached
    - Stops process when meeting can be scheduled

## 4. Main Function

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
        Participant("Charlie", [
            TimeSlot("2024-07-21", 11, 14), 
            TimeSlot("2024-07-21", 16, 18)
        ]),
    ]

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
```

Main function flow:
1. Creates participant agents with availability windows
2. Defines meeting requirements
3. Starts scheduling process by launching admin agent
4. Uses pickle for serializing meeting data

## Key Design Patterns

1. **Observer Pattern**
    - Uses Ceylon's `@on` decorators for event handling
    - Agents respond to specific message types

2. **Asynchronous Programming**
    - Built on Python's asyncio
    - Non-blocking message handling

3. **State Management**
    - Coordinator maintains scheduling state
    - Participants track own availability

4. **Message-Passing Architecture**
    - Communication via serialized messages
    - Broadcast and direct messaging support

## Error Handling

1. Time slot validation through overlap checking
2. Graceful handling of rejection responses
3. State tracking prevents duplicate acceptances

## Performance Considerations

1. Uses efficient time slot comparison algorithm
2. Minimizes message passing through broadcast patterns
3. Asynchronous operations prevent blocking