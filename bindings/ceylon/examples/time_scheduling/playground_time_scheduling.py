import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from loguru import logger

from ceylon import BaseAgent, AgentDetail, on, on_run, on_connect, PeerMode
from ceylon.base.playground import BasePlayGround


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


class ParticipantAgent(BaseAgent):
    def __init__(
            self,
            name: str,
            available_slots: List[TimeSlot]
    ):
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
    async def handle_request(self, request: AvailabilityRequest, time: int, agent: AgentDetail):
        if request.meeting_id in self.scheduled_meetings:
            return

        is_available = any(
            self.has_overlap(slot, request.time_slot, request.time_slot.duration)
            for slot in self.available_slots
        )

        response = AvailabilityResponse(
            meeting_id=request.meeting_id,
            participant=self.name,
            time_slot=request.time_slot,
            available=is_available
        )
        await self.broadcast_message(response)

    @on(MeetingScheduled)
    async def handle_scheduled(self, meeting: MeetingScheduled, time: int, agent: AgentDetail):
        if self.name in meeting.participants:
            self.scheduled_meetings[meeting.meeting_id] = meeting.time_slot
            logger.info(f"{self.name}: Confirmed for meeting {meeting.meeting_id} at {meeting.time_slot.start_time}:00")

    @on_run()
    async def handle_run(self, inputs: bytes):
        logger.info(f"Participant {self.name} started")
        while True:
            await asyncio.sleep(0.1)


@dataclass
class MeetingOutput:
    meeting_id: str
    name: str
    scheduled: bool
    time_slot: Optional[TimeSlot] = None
    participants: List[str] = field(default_factory=list)
    error: Optional[str] = None


class SchedulingPlayground(BasePlayGround):
    def __init__(self, name="meeting_scheduler", port=8888):
        super().__init__(name=name, port=port)
        self.meetings: Dict[str, Meeting] = {}
        self.current_slots: Dict[str, TimeSlot] = {}
        self.responses: Dict[str, Dict[str, List[str]]] = {}
        self.scheduled_meetings: Dict[str, MeetingScheduled] = {}
        self._meeting_completed_events: Dict[str, asyncio.Event] = {}
        self._completed_meetings: Dict[str, MeetingOutput] = {}
        self._connected_event = asyncio.Event()

    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        if agent.role == "participant":
            connected_agents = await self.get_connected_agents()
            if len(connected_agents) >= len(self._all_tasks_completed_events):
                self._connected_event.set()

    @on(AvailabilityResponse)
    async def handle_response(self, response: AvailabilityResponse, time: int, agent: AgentDetail):
        meeting_id = response.meeting_id
        if meeting_id in self.scheduled_meetings:
            return

        # Handle unavailable time slot
        if not response.available:
            current = self.current_slots[meeting_id]
            next_slot = TimeSlot(
                current.date,
                current.start_time + 1,
                current.start_time + 1 + self.meetings[meeting_id].duration
            )

            if next_slot.end_time > 18:  # Don't schedule past 6 PM
                self._complete_meeting(meeting_id, False, error="No suitable time found")
                return

            self.current_slots[meeting_id] = next_slot
            await self.broadcast_message(AvailabilityRequest(
                meeting_id=meeting_id,
                time_slot=next_slot
            ))
            return

        # Track the response
        slot_key = f"{response.time_slot.date}_{response.time_slot.start_time}"
        if meeting_id not in self.responses:
            self.responses[meeting_id] = {}
        if slot_key not in self.responses[meeting_id]:
            self.responses[meeting_id][slot_key] = []

        if response.participant not in self.responses[meeting_id][slot_key]:
            self.responses[meeting_id][slot_key].append(response.participant)

        # Try to schedule the meeting
        available_participants = self.responses[meeting_id][slot_key]
        meeting = self.meetings[meeting_id]

        if len(available_participants) >= meeting.minimum_participants:
            # Schedule the meeting
            scheduled = MeetingScheduled(
                meeting_id=meeting_id,
                time_slot=self.current_slots[meeting_id],
                participants=available_participants[:meeting.minimum_participants]
            )
            self.scheduled_meetings[meeting_id] = scheduled
            await self.broadcast_message(scheduled)

            self._complete_meeting(meeting_id, True, scheduled)

            # Check if all meetings are scheduled
            if len(self.scheduled_meetings) == len(self.meetings):
                logger.info("\nAll meetings scheduled successfully!")
                await self.finish()

    def _complete_meeting(
            self,
            meeting_id: str,
            success: bool,
            scheduled: Optional[MeetingScheduled] = None,
            error: Optional[str] = None
    ):
        """Record meeting completion status"""
        meeting = self.meetings[meeting_id]
        output = MeetingOutput(
            meeting_id=meeting_id,
            name=meeting.name,
            scheduled=success
        )

        if success and scheduled:
            output.time_slot = scheduled.time_slot
            output.participants = scheduled.participants
        elif error:
            output.error = error

        self._completed_meetings[meeting_id] = output
        if meeting_id in self._meeting_completed_events:
            self._meeting_completed_events[meeting_id].set()

    def get_completed_meetings(self) -> Dict[str, MeetingOutput]:
        """Get all completed meeting results"""
        return self._completed_meetings.copy()

    async def schedule_meetings(self, meetings: List[Meeting], participants: List[ParticipantAgent]):
        """Initialize and start meeting scheduling"""
        # Store meetings and create completion events
        self.meetings = {str(i): meeting for i, meeting in enumerate(meetings)}
        for meeting_id in self.meetings:
            self._meeting_completed_events[meeting_id] = asyncio.Event()

        # Start the playground
        async with self.play(workers=participants) as active_playground:
            # Wait for all participants to connect
            await self._connected_event.wait()

            # Start scheduling each meeting
            for meeting_id, meeting in self.meetings.items():
                initial_slot = TimeSlot(
                    meeting.date,
                    9,  # Start at 9 AM
                    9 + meeting.duration
                )
                self.current_slots[meeting_id] = initial_slot
                await self.broadcast_message(AvailabilityRequest(
                    meeting_id=meeting_id,
                    time_slot=initial_slot
                ))

            # Wait for all meetings to complete
            await asyncio.gather(*(
                event.wait() for event in self._meeting_completed_events.values()
            ))

            return self.get_completed_meetings()


async def main():
    # Define meetings to schedule
    meetings = [
        Meeting("Team Sync", "2024-07-21", 1, 3),
        Meeting("Project Review", "2024-07-21", 2, 2)
    ]

    # Create participants
    participants = [
        ParticipantAgent(
            "Alice",
            [TimeSlot("2024-07-21", 9, 12), TimeSlot("2024-07-21", 14, 17)]
        ),
        ParticipantAgent(
            "Bob",
            [TimeSlot("2024-07-21", 10, 13), TimeSlot("2024-07-21", 15, 18)]
        ),
        ParticipantAgent(
            "Charlie",
            [TimeSlot("2024-07-21", 11, 14), TimeSlot("2024-07-21", 16, 18)]
        ),
        ParticipantAgent(
            "David",
            [TimeSlot("2024-07-21", 9, 11), TimeSlot("2024-07-21", 13, 16)]
        )
    ]

    # Create and run playground
    playground = SchedulingPlayground(port=8455)

    try:
        logger.info("Starting scheduling system...")
        completed_meetings = await playground.schedule_meetings(meetings, participants)

        # Print results
        logger.info("\nScheduling Results:")
        for meeting in completed_meetings.values():
            logger.info(f"\nMeeting: {meeting.name}")
            if meeting.scheduled:
                logger.info(f"Time: {meeting.time_slot.start_time}:00")
                logger.info(f"Participants: {', '.join(meeting.participants)}")
            else:
                logger.warning(f"Failed to schedule: {meeting.error}")

    except KeyboardInterrupt:
        logger.info("Shutting down scheduling system...")

if __name__ == "__main__":
    asyncio.run(main())