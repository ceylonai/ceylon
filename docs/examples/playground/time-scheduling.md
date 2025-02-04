# Building a Distributed Meeting Scheduling System with Ceylon

This tutorial demonstrates how to build a distributed meeting scheduling system using Ceylon's BasePlayGround functionality. The system allows multiple participants to coordinate and schedule meetings based on their availability.

## System Overview

The system implements a distributed scheduling algorithm where:
- Multiple participants share their availability
- Multiple meetings need to be scheduled
- Each meeting has minimum participant requirements
- Scheduling must respect time slots and participant constraints

### Architecture Diagram

````mermaid
flowchart TB
    subgraph Playground[Scheduling Playground]
        MT[Meeting Tracker]
        SR[Scheduling Router]
        PM[Progress Monitor]
    end

    subgraph Participants[Participant Agents]
        P1[Participant 1]
        P2[Participant 2]
        P3[Participant 3]
        P4[Participant 4]
    end

    subgraph Messages[Message Types]
        AR[Availability Request]
        AP[Availability Response]
        MS[Meeting Scheduled]
    end

    MT --> |Creates| AR
    AR --> |Sent to| Participants
    Participants --> |Responds with| AP
    AP --> |Processed by| SR
    SR --> |Creates| MS
    MS --> |Notifies| Participants
    PM --> |Monitors| SR
````

## Prerequisites

1. Python 3.8+
2. Ceylon framework
3. Basic understanding of:
    - Async Python
    - Distributed systems concepts
    - Event-driven programming

```bash
pip install ceylon loguru
```

## Core Components

### 1. Data Models

First, let's define our core data structures:

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
class MeetingOutput:
    meeting_id: str
    name: str
    scheduled: bool
    time_slot: Optional[TimeSlot] = None
    participants: List[str] = field(default_factory=list)
    error: Optional[str] = None
```

### 2. Message Types

Define the messages that agents will exchange:

```python
@dataclass
class AvailabilityRequest:
    meeting_id: str
    time_slot: TimeSlot

@dataclass
class AvailabilityResponse:
    meeting_id: str
    participant: str
    time_slot: TimeSlot
    available: bool

@dataclass
class MeetingScheduled:
    meeting_id: str
    time_slot: TimeSlot
    participants: List[str]
```

### 3. Participant Agent

The ParticipantAgent represents each person in the system:

```python
class ParticipantAgent(BaseAgent):
    def __init__(self, name: str, available_slots: List[TimeSlot]):
        super().__init__(
            name=name,
            mode=PeerMode.CLIENT,
            role="participant"
        )
        self.available_slots = available_slots
        self.scheduled_meetings: Dict[str, TimeSlot] = {}

    @staticmethod
    def has_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration

    @on(AvailabilityRequest) 
    async def handle_request(self, request: AvailabilityRequest, 
                           time: int, agent: AgentDetail):
        # Check availability and respond
        is_available = any(
            self.has_overlap(slot, request.time_slot, 
                           request.time_slot.duration)
            for slot in self.available_slots
        )
        response = AvailabilityResponse(
            meeting_id=request.meeting_id,
            participant=self.name,
            time_slot=request.time_slot,
            available=is_available
        )
        await self.broadcast_message(response)
```

### 4. Scheduling Playground

The SchedulingPlayground coordinates the entire system:

```python
class SchedulingPlayground(BasePlayGround):
    def __init__(self, name="meeting_scheduler", port=8888):
        super().__init__(name=name, port=port)
        self.meetings: Dict[str, Meeting] = {}
        self.current_slots: Dict[str, TimeSlot] = {}
        self.responses: Dict[str, Dict[str, List[str]]] = {}
        self.scheduled_meetings: Dict[str, MeetingScheduled] = {}
        self._meeting_completed_events: Dict[str, asyncio.Event] = {}
        self._completed_meetings: Dict[str, MeetingOutput] = {}

    async def schedule_meetings(self, meetings: List[Meeting], 
                              participants: List[ParticipantAgent]):
        # Store meetings and create completion events
        self.meetings = {str(i): meeting for i, meeting in enumerate(meetings)}
        
        # Start scheduling process
        async with self.play(workers=participants) as active_playground:
            # Initialize scheduling for each meeting
            for meeting_id, meeting in self.meetings.items():
                await self.start_scheduling(meeting_id, meeting)
                
            # Wait for completion
            await self.wait_for_completion()
            return self.get_completed_meetings()
```

## Implementation Steps

### 1. Initialize the System

```python
# Define meetings to schedule
meetings = [
    Meeting("Team Sync", "2024-07-21", 1, 3),
    Meeting("Project Review", "2024-07-21", 2, 2)
]

# Create participants
participants = [
    ParticipantAgent(
        "Alice",
        [TimeSlot("2024-07-21", 9, 12), 
         TimeSlot("2024-07-21", 14, 17)]
    ),
    ParticipantAgent(
        "Bob",
        [TimeSlot("2024-07-21", 10, 13), 
         TimeSlot("2024-07-21", 15, 18)]
    )
]

# Create playground
playground = SchedulingPlayground(port=8455)
```

### 2. Handle Meeting Responses

```python
@on(AvailabilityResponse)
async def handle_response(self, response: AvailabilityResponse, 
                        time: int, agent: AgentDetail):
    meeting_id = response.meeting_id
    
    # Handle unavailable time slots
    if not response.available:
        await self.try_next_slot(meeting_id)
        return
    
    # Track responses
    self.track_response(response)
    
    # Try scheduling
    if self.can_schedule(meeting_id):
        await self.schedule_meeting(meeting_id)
```

### 3. Schedule Meetings

```python
async def schedule_meeting(self, meeting_id: str):
    current_slot = self.current_slots[meeting_id]
    available_participants = self.get_available_participants(meeting_id)
    
    scheduled = MeetingScheduled(
        meeting_id=meeting_id,
        time_slot=current_slot,
        participants=available_participants
    )
    
    await self.broadcast_message(scheduled)
    self._complete_meeting(meeting_id, True, scheduled)
```

## System Flow

### 1. Initialization Flow

````mermaid
sequenceDiagram
    participant M as Main
    participant P as Playground
    participant PA as ParticipantAgents
    
    M->>P: Create Playground
    M->>PA: Create Participants
    M->>P: schedule_meetings(meetings, participants)
    P->>PA: Connect Participants
    
    loop For each meeting
        P->>PA: Send AvailabilityRequest
        PA->>P: Send AvailabilityResponse
    end
````

### 2. Scheduling Flow

````mermaid
sequenceDiagram
    participant P as Playground
    participant PA as Participants
    
    P->>PA: AvailabilityRequest
    
    loop Until scheduled
        PA->>P: AvailabilityResponse
        
        alt Enough Available
            P->>PA: MeetingScheduled
        else Try Next Slot
            P->>PA: New AvailabilityRequest
        end
    end
````

## Advanced Features

### 1. Custom Scheduling Rules

Extend the scheduling logic with custom rules:

```python
class CustomSchedulingPlayground(SchedulingPlayground):
    def __init__(self, rules: List[SchedulingRule], **kwargs):
        super().__init__(**kwargs)
        self.rules = rules
    
    async def can_schedule(self, meeting_id: str) -> bool:
        # Apply all rules
        for rule in self.rules:
            if not await rule.check(self, meeting_id):
                return False
        return True
```

### 2. Scheduling Priorities

Add priority handling:

```python
@dataclass
class PrioritizedMeeting(Meeting):
    priority: int = 1

class PrioritySchedulingPlayground(SchedulingPlayground):
    def get_next_meeting(self) -> Optional[str]:
        unscheduled = self.get_unscheduled_meetings()
        return max(unscheduled, 
                  key=lambda m: self.meetings[m].priority,
                  default=None)
```

### 3. Time Constraints

Add time constraint handling:

```python
@dataclass
class TimeConstraints:
    earliest_start: int = 9   # 9 AM
    latest_end: int = 17      # 5 PM
    min_gap: int = 1          # 1 hour between meetings

class ConstrainedSchedulingPlayground(SchedulingPlayground):
    def __init__(self, constraints: TimeConstraints, **kwargs):
        super().__init__(**kwargs)
        self.constraints = constraints
    
    def is_valid_slot(self, slot: TimeSlot) -> bool:
        return (slot.start_time >= self.constraints.earliest_start and
                slot.end_time <= self.constraints.latest_end)
```

## Best Practices

1. **Error Handling**
    - Implement comprehensive error handling
    - Use try-except blocks for message handling
    - Log errors with context

```python
@on(AvailabilityResponse)
async def handle_response(self, response: AvailabilityResponse, 
                        time: int, agent: AgentDetail):
    try:
        meeting_id = response.meeting_id
        if not self.is_valid_meeting(meeting_id):
            logger.warning(f"Invalid meeting ID: {meeting_id}")
            return
            
        # Process response
        await self.process_response(response)
        
    except Exception as e:
        logger.error(f"Error handling response: {e}")
        self._complete_meeting(meeting_id, False, 
                             error=f"Processing error: {str(e)}")
```

2. **Resource Management**
    - Use context managers
    - Clean up resources properly
    - Monitor system resources

```python
async with playground.play(workers=participants) as active_playground:
    try:
        results = await active_playground.schedule_meetings(meetings)
    finally:
        await active_playground.cleanup()
```

3. **Logging and Monitoring**
    - Log important events
    - Track system state
    - Monitor progress

```python
def _complete_meeting(self, meeting_id: str, success: bool, 
                     scheduled: Optional[MeetingScheduled] = None,
                     error: Optional[str] = None):
    """Record meeting completion status"""
    logger.info(f"Completing meeting {meeting_id}")
    logger.info(f"Success: {success}")
    if error:
        logger.error(f"Error: {error}")
    
    # Record completion
    output = MeetingOutput(
        meeting_id=meeting_id,
        name=self.meetings[meeting_id].name,
        scheduled=success,
        error=error
    )
    
    if success and scheduled:
        output.time_slot = scheduled.time_slot
        output.participants = scheduled.participants
        
    self._completed_meetings[meeting_id] = output
```

## Troubleshooting

### Common Issues

1. **Meetings Not Scheduling**
    - Check participant availability
    - Verify time slot constraints
    - Monitor response handling

2. **System Hanging**
    - Check event completion
    - Verify message handling
    - Monitor async operations

3. **Incorrect Schedules**
    - Validate time slot logic
    - Check overlap calculations
    - Verify participant responses

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger.enable("ceylon")
```

## Example Output

```
2025-02-04 10:15:30 | INFO | Starting scheduling system...
2025-02-04 10:15:30 | INFO | Participants connected: 4
2025-02-04 10:15:30 | INFO | Scheduling 2 meetings...

2025-02-04 10:15:31 | INFO | Meeting: Team Sync
2025-02-04 10:15:31 | INFO | - Checking slot: 9:00
2025-02-04 10:15:31 | INFO | - Available: Alice, Bob, Charlie
2025-02-04 10:15:31 | INFO | - Scheduled successfully

2025-02-04 10:15:32 | INFO | Meeting: Project Review
2025-02-04 10:15:32 | INFO | - Checking slot: 14:00
2025-02-04 10:15:32 | INFO | - Available: Bob, David
2025-02-04 10:15:32 | INFO | - Scheduled successfully

2025-02-04 10:15:33 | INFO | All meetings scheduled successfully!
```

## Conclusion

This tutorial demonstrated building a distributed meeting scheduling system using Ceylon's BasePlayGround. Key takeaways:

1. Modular system design using playground architecture
2. Effective message-based communication
3. Robust error handling and resource management
4. Flexible scheduling algorithms
5. Comprehensive monitoring and logging

For more information, visit:
- Ceylon Documentation: [https://docs.ceylon.ai](https://docs.ceylon.ai)
- Source Code: [https://github.com/ceylon-ai/ceylon](https://github.com/ceylon-ai/ceylon)