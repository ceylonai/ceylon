# Time Scheduling Agent Framework

This project demonstrates a multi-agent system for scheduling meetings using the Ceylon framework. It simulates a group
of participants trying to find a common time slot for a meeting based on their individual availabilities.

## Overview

The system consists of two main types of agents:

1. **Participants**: Represent individuals with their own schedules and availabilities.
2. **Coordinator**: Manages the overall scheduling process and coordinates between participants.

The goal is to find a time slot that satisfies the meeting requirements (duration and minimum number of participants)
based on the availabilities of all participants.

## Key Components

### Data Classes

- `Meeting`: Represents the meeting to be scheduled, including:
   - name: Name of the meeting
   - date: Date for the meeting
   - duration: Length of the meeting in hours
   - minimum_participants: Minimum number of participants required
- `TimeSlot`: Represents a specific time slot with:
   - date: Date of the slot
   - start_time: Start hour (0-23)
   - end_time: End hour
   - duration: Property that calculates slot length
- `AvailabilityRequest`: Used by the Coordinator to request availability for a specific time slot
- `AvailabilityResponse`: Used by Participants to respond with their availability, including:
   - owner: Participant name
   - time_slot: The proposed time slot
   - accepted: Whether the participant is available
- `RunnerInput`: Wrapper class for the meeting request input

### Agents

1. **Participant (Worker)**
   - Manages individual schedules with predefined available time slots
   - Methods:
      - `on_message`: Handles availability requests and responds with acceptance/rejection
      - `is_overlap`: Checks if a proposed time slot overlaps with available times
   - Maintains a list of available TimeSlots for the participant

2. **Coordinator (Admin)**
   - Manages the overall scheduling process
   - State tracking:
      - meeting: Current meeting being scheduled
      - agreed_slots: Dictionary tracking participant agreements for each time slot
      - next_time_slot: Next time slot to be proposed
   - Methods:
      - `run`: Initializes the scheduling process with a meeting request
      - `on_agent_connected`: Triggers initial availability request when agents connect
      - `on_message`: Processes availability responses and proposes new time slots
      - `is_overlap`: Utility method to check time slot overlaps

## How It Works

1. The Coordinator is initialized with a Meeting request (name, duration, date, minimum participants)
2. Participants are created with their individual available time slots
3. When all participants connect, the Coordinator starts proposing time slots beginning at hour 0
4. For each proposed time slot:
   - Coordinator sends an AvailabilityRequest to all participants
   - Participants check their schedules and respond with AvailabilityResponse
   - Coordinator tracks agreements and proposes the next time slot if needed
5. The process continues until either:
   - A time slot with enough agreeing participants is found
   - All possible time slots for the day are exhausted

## Running the Code

1. Install required dependencies:
   ```
   pip install asyncio pydantic ceylon
   ```

2. Run the script:
   ```
   python time_scheduling.py
   ```

## Default Configuration

The example includes:
- Meeting "Meeting 1" with 2-hour duration and minimum 3 participants
- Five participants (Alice, Bob, Charlie, David, Kevin) with different availability windows
- Each participant has two available time slots during the day
- Date set to "2024-07-21"

## Customization

You can customize the simulation by modifying the `main` function:

- Adjust the Meeting parameters (duration, minimum participants)
- Add or remove Participants
- Modify Participant availability windows
- Change the date of the meeting

## Note

This implementation uses:
- Ceylon framework for agent communication
- Pydantic for data validation and serialization
- Pickle for message serialization
- Asyncio for asynchronous execution

## Limitations and Potential Improvements

- Currently only supports single-day scheduling
- Time slots are integer-based (hour granularity)
- No support for recurring meetings
- No consideration of time zones
- Limited to searching sequential time slots
- No preference weighting for participants
- No support for required vs optional participants
- No persistence of schedules between runs

These limitations provide opportunities for extending the system for more realistic scheduling scenarios.