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

- `Meeting`: Represents the meeting to be scheduled, including name, date, duration, and minimum required participants.
- `TimeSlot`: Represents a specific time slot with a date, start time, and end time.
- `AvailabilityRequest`: Used by the Coordinator to request availability from Participants.
- `AvailabilityResponse`: Used by Participants to respond to availability requests.

### Agents

1. **Participant (Worker)**
    - Manages individual schedules and responds to availability requests.
    - Methods:
        - `on_message`: Handles incoming availability requests.
        - `is_overlap`: Checks if a given time slot overlaps with available times.

2. **Coordinator (Admin)**
    - Manages the overall scheduling process.
    - Methods:
        - `run`: Initializes the scheduling process with a meeting request.
        - `on_agent_connected`: Triggers the initial availability request.
        - `on_message`: Processes responses from Participants and determines if a suitable time slot is found.

## How It Works

1. The Coordinator sends out an initial availability request to all Participants.
2. Participants check their schedules and respond with their availability.
3. The Coordinator collects responses and keeps track of agreed time slots.
4. If a time slot with enough participants is found, the process ends successfully.
5. If not, the Coordinator continues to propose new time slots until a suitable one is found or all possibilities are
   exhausted.

## Running the Code

To run the time scheduling simulation:

1. Ensure you have the required dependencies installed:
   ```
   pip install asyncio pydantic ceylon
   ```

2. Run the script:
   ```
   python time_scheduling.py
   ```

3. The script will simulate the scheduling process and output the results, including which participants agreed on which
   time slots.

## Customization

You can customize the simulation by modifying the `main` function:

- Adjust the number of Participants and their availabilities.
- Modify the Meeting parameters (duration, date, minimum participants).

## Note

This example uses the Ceylon framework for agent communication. Make sure you have the Ceylon library properly installed
and configured in your environment.