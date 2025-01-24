# Time Scheduler System

A distributed system for scheduling meetings using multi-agent coordination.

## Features

### Automatic Time Slot Negotiation
- Intelligently proposes time slots based on participant availability
- Handles scheduling conflicts by advancing to next available slot
- Optimizes for maximum participant attendance

### Smart Availability Management
- Tracks individual participant time preferences and constraints
- Supports multiple available time slots per participant
- Detects overlapping availability windows efficiently
- Validates duration requirements against available slots

### Flexible Meeting Requirements
- Configurable minimum participant thresholds
- Dynamic participant joining and leaving
- Meeting duration enforcement
- Date-specific scheduling support

### Asynchronous Communication
- Non-blocking availability checks
- Real-time participant responses
- Event-driven architecture using decorators
- Scalable multi-agent message passing

## Quick Start

```python
async def main():
    # Create meeting request
    meeting = Meeting(
        name="Team Sync",
        date="2024-07-21",
        duration=1,
        minimum_participants=3
    )

    # Initialize scheduler
    scheduler = Scheduler(meeting)
    scheduler_details = scheduler.details()

    # Create participants
    participants = [
        Participant("Alice", [
            TimeSlot("2024-07-21", 9, 12),
            TimeSlot("2024-07-21", 14, 18)
        ], admin_peer=scheduler_details.id),
        # Add more participants...
    ]

    # Start scheduling
    await scheduler.start_agent(b"", participants)

asyncio.run(main())
```

## Components

### TimeSlot
```python
@dataclass
class TimeSlot:
    date: str
    start_time: int
    end_time: int
```

### Meeting
```python
@dataclass
class Meeting:
    name: str
    date: str
    duration: int
    minimum_participants: int
```

### Participant Agent
Handles availability requests and responses:
```python
@on(AvailabilityRequest)
async def handle_request(self, data: AvailabilityRequest, time: int, agent: AgentDetail):
    is_available = any(
        self.has_overlap(slot, data.time_slot, data.time_slot.duration)
        for slot in self.available_slots
    )
    # Send response...
```

### Scheduler Agent
Coordinates meeting scheduling:
```python
@on(AvailabilityResponse)
async def handle_response(self, data: AvailabilityResponse, time: int, agent: AgentDetail):
    if not data.available:
        # Try next time slot
        next_slot = TimeSlot(...)
        await self.broadcast_message(...)
    else:
        # Track agreements
        if len(agreed_participants) >= minimum_required:
    # Finalize meeting
```

## Customization

Add priority scheduling:
```python
@dataclass
class Meeting:
    priority: int = 1  # Add priority field
```

Add participant preferences:
```python
@dataclass
class AvailabilityResponse:
    preference_score: int = 0  # Add preference rating
```

## License
Copyright 2024, All rights reserved.